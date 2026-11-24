"""Capa de negocio de `consultas`: recupera los artículos relacionados y arma la respuesta citada.

Flujo de `crear` (RAG: primero recuperar, después generar):
  1. Valida la pregunta (5 a 1000 caracteres).
  2. Si hay modelo de lenguaje, traduce la duda a términos jurídicos ("me echaron" -> "despido, indemnización,
     aviso previo") para buscar mejor. Luego recupera artículos por dos vías y las combina (ranking recíproco):
       - por significado: embedding de la pregunta comparado con pgvector;
       - por palabras: búsqueda de texto completo en español.
  3. Si hay modelo de lenguaje, le pide redactar en lenguaje simple SOLO con esos artículos, cada uno con
     un código [F1]...; después valida que cada código citado exista en lo entregado (nunca se inventa una cita).
  4. Si no hay modelo o falla, responde de forma extractiva (muestra los artículos encontrados).
  5. Guarda la consulta y sus citas en una sola transacción, con el modo y el tiempo de respuesta.
"""
import re
import time

from app.errors import NoEncontrado, ReglaDeNegocio
from app.repositories import consultas_repository, fragmentos_repository

MIN_PREGUNTA = 5
MAX_PREGUNTA = 1000
MAX_CITAS = 5
MAX_CITAS_EXTRACTIVA = 3   # sin IA se muestran menos artículos, porque van con su texto
CANDIDATOS = 10         # artículos que se entregan al modelo de lenguaje
POR_VIA = 12            # artículos que trae cada vía de búsqueda antes de fusionar
MAX_TERMINOS = 20
MAX_LEYES = 4
MAX_ARTICULOS = 6
LARGO_EXTRACTO = 350
LARGO_CONTEXTO = 2500   # caracteres de cada artículo que se envían al modelo
RRF_K = 60
CACHE_DIAS = 7          # una pregunta repetida en este plazo reutiliza la respuesta ya redactada
PATRON_SESION = re.compile(r"^[A-Za-z0-9-]{8,64}$")
AVISO = "Esto es orientación general y no reemplaza la asesoría de un abogado."


# ---------- validaciones ----------
def validar_sesion(sesion: str | None) -> str | None:
    if sesion is None or sesion == "":
        return None
    if not PATRON_SESION.match(sesion):
        raise ReglaDeNegocio("El identificador de sesión no es válido.")
    return sesion


def _validar_pregunta(pregunta: str) -> str:
    pregunta = (pregunta or "").strip()
    if len(pregunta) < MIN_PREGUNTA:
        raise ReglaDeNegocio(f"La pregunta debe tener al menos {MIN_PREGUNTA} caracteres.")
    if len(pregunta) > MAX_PREGUNTA:
        raise ReglaDeNegocio(f"La pregunta no puede superar {MAX_PREGUNTA} caracteres.")
    return pregunta


# ---------- recuperación ----------
def terminos_de_busqueda(pregunta: str) -> str:
    """Convierte la pregunta en una consulta tsquery 'palabra | palabra | …' (solo letras: es seguro)."""
    palabras = re.findall(r"[a-záéíóúñü]{4,}", pregunta.lower())
    unicas = list(dict.fromkeys(palabras))[:MAX_TERMINOS]
    return " | ".join(unicas)


def fusionar(*listas: list[dict], limite: int) -> list[dict]:
    """Fusión por ranking recíproco: premia los artículos que aparecen arriba en cualquiera de las listas."""
    puntaje: dict[int, float] = {}
    por_id: dict[int, dict] = {}
    for lista in listas:
        for pos, f in enumerate(lista):
            puntaje[f["id"]] = puntaje.get(f["id"], 0.0) + 1.0 / (RRF_K + pos + 1)
            por_id.setdefault(f["id"], f)
    orden = sorted(puntaje, key=lambda i: (-puntaje[i], i))
    return [por_id[i] for i in orden[:limite]]


def normalizar_ley(nombre: str) -> str:
    """'Ley 14.908' -> 'ley 14908'; 'Código Civil' -> 'codigo civil' (igual que el identificador en la base)."""
    import unicodedata
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", sin_tildes.replace(".", "").lower()).strip()
    t = re.sub(r"^(decreto con fuerza de ley|d f l|dfl)\b", "dfl", t)
    t = re.sub(r"^(decreto ley|d l|dl)\b", "dl", t)
    return re.sub(r"^ley n[°ºo]? ", "ley ", t)


PATRON_ARTICULO = re.compile(
    r"^(?P<ley>.+?)[\s,]*\bart(?:[íi]culo|\.)?\s*(?:n[°º]\s*)?(?P<num>\d+(?:\s*-\s*[a-z]\b|\s*(?:bis|ter|qu[aá]ter))?(?:\s*transitorio)?)",
    re.IGNORECASE)


def normalizar_articulo(texto: str) -> tuple[str, str] | None:
    """'Código Civil art. 1545' -> ('codigo civil', 'art. 1545'), con el mismo formato que la base."""
    m = PATRON_ARTICULO.match(texto.strip())
    if not m:
        return None
    num = re.sub(r"\s+", " ", m.group("num").lower().replace("á", "a")).strip()
    return normalizar_ley(m.group("ley")), f"art. {num}"


def reformular(pregunta: str, llm) -> tuple[str, list[str], list[tuple[str, str]]]:
    """Agrega a la pregunta los términos jurídicos que sugiere el modelo y devuelve las leyes y los artículos
    concretos que nombra (estos se buscan tal cual en la base: si no existen, simplemente no aparecen)."""
    if llm is None or not llm.disponible() or not hasattr(llm, "reformular"):
        return pregunta, [], []
    r = llm.reformular(pregunta)
    if not isinstance(r, dict):
        return pregunta, [], []
    extra = " ".join(str(r.get(k, "")) for k in ("consulta", "terminos") if isinstance(r.get(k), str))
    leyes = [normalizar_ley(x) for x in r.get("leyes", []) if isinstance(x, str) and x.strip()] \
        if isinstance(r.get("leyes"), list) else []
    articulos = [a for a in (normalizar_articulo(x) for x in r.get("articulos", []) if isinstance(x, str))
                 if a] if isinstance(r.get("articulos"), list) else []
    return f"{pregunta} {extra}".strip(), leyes[:MAX_LEYES], articulos[:MAX_ARTICULOS]


def _permanentes_primero(fragmentos: list[dict]) -> list[dict]:
    """Los artículos transitorios suelen regular situaciones antiguas (p. ej. rentas máximas de 1982):
    se dejan después de los permanentes, sin eliminarlos."""
    return sorted(fragmentos, key=lambda f: "transitorio" in str(f.get("articulo", "")).lower())


def recuperar(conn, pregunta: str, repo_frag, vectorizador, llm=None) -> list[dict]:
    """Recupera por varias vías y fusiona. Los artículos que el modelo nombra con su número pesan el triple
    y las vías limitadas a las leyes que nombra pesan el doble: con 147 mil artículos, buscar en todo el corpus
    trae leyes antiguas parecidas pero no aplicables."""
    from app.ia.embeddings import como_literal
    busqueda, leyes, articulos = reformular(pregunta, llm)
    vector = vectorizador.pregunta(busqueda) if vectorizador else None
    literal = como_literal(vector) if vector else None
    terminos = terminos_de_busqueda(busqueda)
    listas = []
    if articulos and hasattr(repo_frag, "buscar_articulos"):
        directos = repo_frag.buscar_articulos(conn, articulos)
        listas += [directos] * 3        # peso triple
    if literal:
        listas.append(repo_frag.buscar_semantico(conn, literal, POR_VIA))
    if terminos:
        listas.append(repo_frag.buscar(conn, terminos, POR_VIA))
    if leyes and hasattr(repo_frag, "buscar_en_fuentes"):
        en_leyes = []
        if literal:
            en_leyes.append(repo_frag.buscar_semantico_en_fuentes(conn, leyes, literal, POR_VIA))
        if terminos:
            en_leyes.append(repo_frag.buscar_en_fuentes(conn, leyes, terminos, POR_VIA))
        listas += en_leyes * 2          # peso doble
    return _permanentes_primero(fusionar(*listas, limite=CANDIDATOS + 4))[:CANDIDATOS]


# ---------- redacción ----------
def _extracto(texto: str, largo: int = LARGO_EXTRACTO) -> str:
    t = re.sub(r"\s+", " ", texto).strip()
    return t if len(t) <= largo else t[:largo].rsplit(" ", 1)[0] + "…"


def _etiqueta(f: dict) -> str:
    """Nombre legible del artículo, igual al de la cita: 'Ley 14.908, art. 14' o 'Código Civil de Chile, art. 1545'.
    Si el identificador tiene número (leyes, DFL, DL) se usa ese; los códigos usan su título."""
    ident = re.sub(r"\s*\(idNorma \d+\)$", "", f["fuente"])
    titulo = f.get("fuente_titulo")
    nombre = ident if re.search(r"\d", ident) or not titulo or titulo.isupper() or len(titulo) > 80 else titulo
    return f"{nombre}, {f['articulo']}"


def armar_prompt(pregunta: str, fragmentos: list[dict]) -> str:
    bloques = [f"[F{i}] {_etiqueta(f)}\n{_extracto(f['texto'], LARGO_CONTEXTO)}"
               for i, f in enumerate(fragmentos, start=1)]
    return f"Pregunta de la persona:\n{pregunta}\n\nArtículos disponibles:\n\n" + "\n\n".join(bloques)


def redactar_extractiva(fragmentos: list[dict]) -> str:
    if not fragmentos:
        return ("No encontré artículos relacionados con tu pregunta en las leyes cargadas. "
                "Prueba con otras palabras o consulta a un abogado o a una Corporación de Asistencia Judicial.")
    lineas = [f"- {_etiqueta(f)}: {_extracto(f['texto'])}" for f in fragmentos]
    return ("No pude redactar una explicación en este momento, pero estos son los artículos de la ley más "
            "relacionados con tu pregunta.\n\nArtículos relacionados:\n" + "\n".join(lineas) + f"\n\n{AVISO}")


TITULO_LEY = "Qué dice la ley:"
TITULO_PASOS = "Qué puedes hacer:"
TITULO_TENER = "Ten en cuenta:"


def _lista_de_textos(valor) -> list[str]:
    if not isinstance(valor, list):
        return []
    return [re.sub(r"^\s*(?:[0-9]+[.)]|[-•*])\s*", "", x).strip() for x in valor if isinstance(x, str) and x.strip()]


def _sin_citas_repetidas(linea: str) -> str:
    """En una misma línea, deja solo la primera vez que aparece cada cita "(Fuente, art. N)":
    'A (CT, art. 211 C), B (CT, art. 211 B). (CT, art. 211 C)' -> 'A (CT, art. 211 C), B (CT, art. 211 B).'"""
    vistas = set()

    def quitar(m):
        cita = m.group(1)
        if cita in vistas:
            return ""
        vistas.add(cita)
        return m.group(0)
    linea = re.sub(r"\s*\(([^()]+, art\.[^()]+)\)", quitar, linea)
    return re.sub(r"\s+([.,;])", r"\1", linea).rstrip()


def validar_redaccion(salida: dict | None, fragmentos: list[dict]) -> tuple[str, list[dict]] | None:
    """Acepta la respuesta del modelo solo si sus afirmaciones legales citan artículos que se le entregaron.

    Formato esperado: {"resumen", "ley": [{"texto", "cita"}], "pasos", "ten_en_cuenta", "sin_respuesta"}.
    Cada punto de "ley" sin un código válido se descarta; cada [Fn] se reemplaza por el nombre del artículo
    y cualquier código inexistente se elimina. Se arma un texto por secciones que la interfaz muestra con títulos.
    También acepta el formato anterior {"respuesta", "pasos", "citas"}."""
    if not isinstance(salida, dict):
        return None
    disponibles = {f"F{i}": f for i, f in enumerate(fragmentos, start=1)}
    resumen = salida.get("resumen", salida.get("respuesta"))
    if not isinstance(resumen, str) or not resumen.strip():
        return None
    puntos_ley = []
    for item in salida.get("ley", []) if isinstance(salida.get("ley"), list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("texto"), str) or not item["texto"].strip():
            continue
        codigo = str(item.get("cita", "")).strip().strip("[]")
        if codigo in disponibles:
            puntos_ley.append(f"{item['texto'].strip()} [{codigo}]")
    pasos = _lista_de_textos(salida.get("pasos"))[:5]
    tener = _lista_de_textos(salida.get("ten_en_cuenta"))[:3]

    partes = [resumen.strip()]
    if puntos_ley:
        partes.append(TITULO_LEY + "\n" + "\n".join(f"- {p}" for p in puntos_ley[:4]))
    if pasos:
        partes.append(TITULO_PASOS + "\n" + "\n".join(f"{i}. {p}" for i, p in enumerate(pasos, start=1)))
    if tener:
        partes.append(TITULO_TENER + "\n" + "\n".join(f"- {p}" for p in tener))
    texto = "\n\n".join(partes)

    pedidas = [str(x) for x in salida.get("citas", [])] if isinstance(salida.get("citas"), list) else []
    codigos = [c for c in dict.fromkeys([*re.findall(r"\[(F\d+)\]", texto), *pedidas]) if c in disponibles]
    citas = [disponibles[c] for c in codigos][:MAX_CITAS]
    ids_citados = {f["id"] for f in citas}

    def reemplazo(m):
        f = disponibles.get(m.group(1))
        return f" ({_etiqueta(f)})" if f is not None and f["id"] in ids_citados else ""

    texto = re.sub(r"\s*\[(F\d+)\]", reemplazo, texto).strip()
    # Si el modelo ya escribió la cita y además puso el código, queda repetida: "(Ley X, art. 1). (Ley X, art. 1)"
    texto = re.sub(r"\(([^()]+)\)\.?\s*\(\1\)", r"(\1)", texto)
    texto = "\n".join(_sin_citas_repetidas(linea) for linea in texto.split("\n"))
    if fragmentos and not citas:
        # Sin ninguna cita válida solo se acepta si el modelo declara que los artículos no responden.
        declara = salida.get("sin_respuesta") is True or re.search(
            r"no (encontr|aparec|se menciona|hay|regul)", texto.lower())
        if not declara:
            return None
    if "no reemplaza" not in texto.lower():
        texto += f"\n\n{AVISO}"
    return texto, citas


# ---------- alertas de seguridad ----------
PALABRAS_VIOLENCIA = re.compile(
    r"violen|golpe|me pega|pegó|agred|amenaz|abus|acos|maltrat|femicid|me quiere matar|denunciar a mi pareja")
PALABRAS_RIESGO_VITAL = re.compile(r"suicid|quitarme la vida|matarme|no quiero vivir|hacerme daño")


def alerta_para(pregunta: str) -> str | None:
    """Si la pregunta sugiere un riesgo para la persona, se muestran teléfonos de ayuda (fuentes oficiales)."""
    p = (pregunta or "").lower()
    if PALABRAS_RIESGO_VITAL.search(p):
        return ("Si estás pensando en hacerte daño, no estás solo/a: llama a la línea de prevención del suicidio "
                "*4141 (MINSAL, gratuita). Si hay peligro inmediato, llama al 133.")
    if PALABRAS_VIOLENCIA.search(p):
        return ("Si estás en peligro ahora, llama al 133 (Carabineros). También puedes llamar al 149 (Fono Familia "
                "de Carabineros) o al 1455 (orientación en violencias de género, gratuito, todos los días de 8:00 a 24:00).")
    return None


def _con_alerta(c: dict) -> dict:
    return {**c, "alerta": alerta_para(c.get("pregunta", ""))}


# ---------- casos de uso ----------
def crear(conn, pregunta: str, repo=consultas_repository, repo_frag=fragmentos_repository,
          vectorizador=None, llm=None, sesion: str | None = None, reloj=time.monotonic) -> dict:
    inicio = reloj()
    pregunta = _validar_pregunta(pregunta)
    sesion = validar_sesion(sesion)

    # Pregunta repetida: se reutiliza la respuesta ya redactada y validada (responde en milisegundos).
    previa = repo.buscar_reciente(conn, pregunta, CACHE_DIAS) if hasattr(repo, "buscar_reciente") else None
    if previa and previa.get("respuesta") and previa.get("citas"):
        duracion_ms = int((reloj() - inicio) * 1000)
        return _con_alerta(repo.crear(conn, pregunta, previa["respuesta"],
                                      [c["fragmento_id"] for c in previa["citas"]],
                                      sesion=sesion, modo="ia", duracion_ms=duracion_ms))

    fragmentos = recuperar(conn, pregunta, repo_frag, vectorizador, llm)

    modo, respuesta, citas, reutilizable = "extractiva", None, fragmentos[:MAX_CITAS_EXTRACTIVA], False
    if llm is not None and llm.disponible() and fragmentos:
        validada = validar_redaccion(llm.redactar(armar_prompt(pregunta, fragmentos)), fragmentos)
        if validada is not None:
            respuesta, citas = validada
            modo = "ia"
            reutilizable = bool(citas)
    if respuesta is None:
        respuesta = redactar_extractiva(citas)

    duracion_ms = int((reloj() - inicio) * 1000)
    return _con_alerta(repo.crear(conn, pregunta, respuesta, [f["id"] for f in citas],
                                  sesion=sesion, modo=modo, duracion_ms=duracion_ms,
                                  reutilizable=reutilizable))


def listar(conn, page: int, limit: int, repo=consultas_repository, sesion: str | None = None) -> dict:
    items, total = repo.listar(conn, limit, (page - 1) * limit, sesion=validar_sesion(sesion))
    return {"items": [_con_alerta(c) for c in items], "total": total, "page": page, "limit": limit}


def obtener(conn, consulta_id: int, repo=consultas_repository, sesion: str | None = None) -> dict:
    c = repo.obtener(conn, consulta_id, sesion=validar_sesion(sesion))
    if c is None:
        raise NoEncontrado(f"La consulta {consulta_id} no existe.")
    return _con_alerta(c)


def actualizar_util(conn, consulta_id: int, util: bool | None, repo=consultas_repository,
                    sesion: str | None = None) -> dict:
    c = repo.actualizar_util(conn, consulta_id, util, sesion=validar_sesion(sesion))
    if c is None:
        raise NoEncontrado(f"La consulta {consulta_id} no existe.")
    return _con_alerta(c)


def eliminar(conn, consulta_id: int, repo=consultas_repository, sesion: str | None = None) -> None:
    if not repo.eliminar(conn, consulta_id, sesion=validar_sesion(sesion)):
        raise NoEncontrado(f"La consulta {consulta_id} no existe.")


def eliminar_historial(conn, sesion: str | None, repo=consultas_repository) -> int:
    """Derecho a supresión: borra todas las consultas de una sesión."""
    sesion = validar_sesion(sesion)
    if sesion is None:
        raise ReglaDeNegocio("Para borrar el historial hay que indicar la sesión (cabecera X-Sesion).")
    return repo.eliminar_de_sesion(conn, sesion)
