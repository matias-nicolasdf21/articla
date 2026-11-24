"""Corpus completo: lista, descarga y carga normas publicadas en LeyChile, por tipo.

Se ejecuta por etapas y cada etapa se puede interrumpir (Ctrl + C) y repetir: retoma donde quedó.
Sin tipos trabaja con las leyes ("ley"); con tipos, por ejemplo "dfl dl", con decretos con fuerza de ley y
decretos ley (cada conjunto tiene su propia lista en data/).

  python -m scripts.corpus_completo tipos              # 0. cuenta cuántas normas hay de cada tipo
  python -m scripts.corpus_completo listar [tipos]     # 1. arma la lista (datos abiertos de la BCN)
  python -m scripts.corpus_completo descargar [tipos]  # 2. baja cada XML a data/leychile_todas/ (horas)
  python -m scripts.corpus_completo cargar [tipos]     # 3. carga a la base los artículos vigentes
  python -m scripts.calcular_embeddings                # 4. calcula los embeddings que falten

En Docker, anteponer:  docker compose exec api
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LISTA = RAIZ / "data" / "normas_todas.json"     # se cambia según los tipos pedidos (ver _elegir_tipos)
TIPOS = ["ley"]
CARPETA = RAIZ / "data" / "leychile_todas"
SPARQL = "https://datos.bcn.cl/sparql"
XML_URL = "https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma={id}"
AGENTE = {"User-Agent": "Articla-proyecto-universitario"}
PAGINA = 5000
PAUSA_INICIAL_S = 2.0    # pausa entre descargas; sube sola si LeyChile responde 429 (demasiadas peticiones)
PAUSA_MAX_S = 20.0

CONSULTA = """PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT DISTINCT ?norma ?code ?title WHERE {{
  ?norma a bcnnorms:Norm ; bcnnorms:leychileCode ?code .
  FILTER({filtro_tipos} && ?code > {desde})
  OPTIONAL {{ ?norma dc:title ?title }}
}} ORDER BY ?code LIMIT {limite}"""


def _sparql(consulta: str) -> list[dict]:
    url = SPARQL + "?" + urllib.parse.urlencode({"query": consulta, "format": "application/sparql-results+json"})
    req = urllib.request.Request(url, headers={**AGENTE, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))["results"]["bindings"]


def _tipo_y_numero(uri: str) -> tuple[str, str]:
    """URI: .../recurso/cl/<tipo>/<organismo>/<fecha>/<número>[/...]"""
    resto = uri.split("/recurso/cl/", 1)[-1].strip("/").split("/")
    tipo = resto[0] if resto else "?"
    numero = resto[3] if len(resto) > 3 else (resto[-1] if resto else "?")
    return tipo, numero


TIPOS_CONSULTA = """PREFIX bcnnorms: <http://datos.bcn.cl/ontologies/bcn-norms#>
SELECT ?tipo (COUNT(DISTINCT ?code) AS ?n) WHERE {
  ?norma a bcnnorms:Norm ; bcnnorms:leychileCode ?code .
  BIND(STRBEFORE(STRAFTER(STR(?norma), "/recurso/cl/"), "/") AS ?tipo)
} GROUP BY ?tipo ORDER BY DESC(?n)"""


def tipos() -> None:
    """Cuenta las normas de cada tipo según la parte de la URI (ley, dfl, dl, dto, …)."""
    try:
        for f in _sparql(TIPOS_CONSULTA):
            print(f"[tipos] {f['tipo']['value'] or '(sin tipo)':<12} {int(float(f['n']['value'])):>8,}".replace(",", "."))
    except Exception as e:
        print(f"[tipos] el servidor no pudo contar todo de una vez ({e}).")
        print("        Prueba directo:  python -m scripts.corpus_completo listar dfl dl")


def _numero_de_ley(uri: str) -> str:
    resto = uri.split("/recurso/cl/ley/", 1)[-1].strip("/")
    return resto.split("/")[0]


def listar() -> None:
    base = {int(n["id"]) for n in json.loads((RAIZ / "data" / "normas.json").read_text(encoding="utf-8"))}
    vistas: dict[int, dict] = {}
    # Se pagina "por llave" (idNorma mayor al último visto): el servidor de la BCN no acepta OFFSET grandes.
    ultimo, pagina, leidas = 0, PAGINA, 0
    while True:
        try:
            filtro = " || ".join(f'CONTAINS(STR(?norma), "/recurso/cl/{t}/")' for t in TIPOS)
            filas = _sparql(CONSULTA.format(limite=pagina, desde=ultimo, filtro_tipos=f"({filtro})"))
        except Exception as e:
            if pagina > 500:
                pagina //= 2
                print(f"[listar] el servidor rechazó la página ({e}); reintento con {pagina} filas")
                time.sleep(3)
                continue
            raise
        leidas += len(filas)
        codigos = []
        for f in filas:
            try:
                code = int(float(f["code"]["value"]))
            except (KeyError, ValueError):
                continue
            codigos.append(code)
            if code in base or code in vistas:
                continue
            tipo, numero = _tipo_y_numero(f["norma"]["value"])
            titulo = (f.get("title", {}).get("value") or f"{tipo.upper()} {numero}").strip()
            vistas[code] = {"id": code, "tipo": tipo, "numero": numero, "titulo": titulo[:300]}
        print(f"[listar] {leidas} filas leídas · {len(vistas)} leyes distintas · último idNorma {max(codigos, default=ultimo)}")
        if len(filas) < pagina or not codigos:
            break
        ultimo = max(codigos)
        time.sleep(1)
    LISTA.write_text(json.dumps(sorted(vistas.values(), key=lambda x: x["id"]), ensure_ascii=False, indent=0),
                     encoding="utf-8")
    print(f"[listar] {len(vistas)} normas de tipo {', '.join(TIPOS)} (sin contar las base) guardadas en "
          f"{LISTA.relative_to(RAIZ)}")
    if not vistas:
        print("[listar] no se encontró ninguna: revisa los tipos con  python -m scripts.corpus_completo tipos")
    for ejemplo in list(vistas.values())[:5]:
        print("   ej.:", ejemplo)


class Ritmo:
    """Controla la velocidad: si LeyChile pide bajar el ritmo (HTTP 429), espera y aumenta la pausa."""
    def __init__(self):
        self.pausa = PAUSA_INICIAL_S

    def frenar(self, espera: float | None = None) -> float:
        self.pausa = min(PAUSA_MAX_S, self.pausa * 1.5)
        return espera if espera else max(30.0, self.pausa * 5)

    def acelerar(self):
        self.pausa = max(PAUSA_INICIAL_S, self.pausa * 0.98)


def _bajar(n: dict, ritmo: Ritmo) -> str:
    import urllib.error
    destino = CARPETA / f"{n['id']}.xml"
    if destino.exists() and destino.stat().st_size > 0:
        return "ya"
    req = urllib.request.Request(XML_URL.format(id=n["id"]), headers=AGENTE)
    ultimo = None
    for intento in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                datos = r.read()
            time.sleep(ritmo.pausa)
            ritmo.acelerar()
            if not datos.lstrip().startswith(b"<"):
                return "no-xml"
            destino.write_bytes(datos)
            return "ok"
        except urllib.error.HTTPError as e:
            ultimo = e
            if e.code == 429:
                try:
                    retry = float(e.headers.get("Retry-After") or 0)
                except ValueError:
                    retry = 0
                espera = ritmo.frenar(retry)
                print(f"[descargar] LeyChile pide ir más lento: espero {espera:.0f} s (pausa ahora {ritmo.pausa:.1f} s)")
                time.sleep(espera)
                continue
            if e.code in (401, 403, 404):
                return f"error: {e}"
            time.sleep(5 * (intento + 1))
        except Exception as e:
            ultimo = e
            time.sleep(5 * (intento + 1))
    return f"error: {ultimo}"


def descargar() -> None:
    # De la más nueva a la más antigua: si no alcanza el tiempo, ya están las leyes vigentes más usadas.
    normas = sorted(json.loads(LISTA.read_text(encoding="utf-8")), key=lambda x: -x["id"])
    CARPETA.mkdir(parents=True, exist_ok=True)
    cuenta = {"ok": 0, "ya": 0, "fallo": 0}
    ritmo = Ritmo()
    inicio = time.monotonic()
    for i, n in enumerate(normas, start=1):
        r = _bajar(n, ritmo)
        clave = r if r in ("ok", "ya") else "fallo"
        cuenta[clave] += 1
        if clave == "fallo" and cuenta["fallo"] <= 30:
            print(f"[descargar] idNorma {n['id']}: {r}")
        if i % 100 == 0 or i == len(normas):
            transcurrido = time.monotonic() - inicio
            restante = (len(normas) - i) * transcurrido / max(i - cuenta["ya"], 1) / 3600 if cuenta["ok"] else 0
            print(f"[descargar] {i}/{len(normas)} · nuevas {cuenta['ok']} · ya estaban {cuenta['ya']} · "
                  f"fallidas {cuenta['fallo']} · {transcurrido / 60:.0f} min · quedan ~{restante:.1f} h")


SIGLAS = {"ley": "Ley", "decreto con fuerza de ley": "DFL", "decreto ley": "DL", "decreto": "Decreto"}


def _identificacion(ruta: Path) -> tuple[str | None, str | None]:
    """Lee del XML el número de la ley y su nombre de uso común (si tiene)."""
    import xml.etree.ElementTree as ET
    ns = "{http://www.leychile.cl/esquemas}"
    try:
        raiz = ET.parse(ruta).getroot()
    except ET.ParseError:
        return None, None
    numero = None
    for tn in raiz.iter(f"{ns}TipoNumero"):
        tipo, num = (tn.findtext(f"{ns}Tipo") or "").strip(), (tn.findtext(f"{ns}Numero") or "").strip()
        if num:
            numero = f"{SIGLAS.get(tipo.lower(), tipo)} {_formato_numero(num)}"
            break
    comun = raiz.findtext(f".//{ns}NombreUsoComun")
    return numero, (comun.strip() if comun else None)


def _formato_numero(num: str) -> str:
    return f"{int(num):,}".replace(",", ".") if num.isdigit() else num


def cargar() -> None:
    import psycopg
    from psycopg.rows import dict_row
    from app.config import get_database_url
    from app.ingesta.leychile import leer_norma
    from scripts.cargar_leychile import cargar as cargar_norma

    normas = json.loads(LISTA.read_text(encoding="utf-8"))
    hechas = arts = sin_vigentes = errores = 0
    with psycopg.connect(get_database_url(), autocommit=True, row_factory=dict_row) as conn:
        for i, n in enumerate(normas, start=1):
            ruta = CARPETA / f"{n['id']}.xml"
            if not ruta.exists():
                continue
            try:
                norma = leer_norma(ruta, None)
            except Exception as e:
                errores += 1
                if errores <= 20:
                    print(f"[cargar] idNorma {n['id']}: no se pudo leer ({e})")
                continue
            if not norma.articulos:
                sin_vigentes += 1        # ley derogada completa o sin artículos: no se carga
                continue
            numero, comun = _identificacion(ruta)
            ident = numero if numero else f"Norma sin número (idNorma {n['id']})"
            otra = conn.execute("SELECT url_oficial FROM fuentes WHERE identificador = %s", (ident,)).fetchone()
            if otra and not (otra["url_oficial"] or "").endswith(f"idNorma={n['id']}"):
                ident = f"{ident} (idNorma {n['id']})"     # mismo número, otra norma: no pisar la anterior
            titulo = comun.title() if comun else (norma.titulo or n["titulo"])
            cfg = {"tipo": "ley", "identificador": ident[:100], "titulo": titulo[:300]}
            with conn.transaction():
                cargar_norma(conn, cfg, norma)
            hechas += 1
            arts += len(norma.articulos)
            if i % 500 == 0:
                print(f"[cargar] {i}/{len(normas)} revisadas · {hechas} cargadas · {arts} artículos")
    print(f"[cargar] listo: {hechas} leyes, {arts} artículos · {sin_vigentes} sin artículos vigentes · "
          f"{errores} con error de lectura")
    print("Ahora calcula los embeddings:  python -m scripts.calcular_embeddings")


def _elegir_tipos(args: list[str]) -> None:
    global TIPOS, LISTA
    TIPOS = [a.lower() for a in args] or ["ley"]
    LISTA = RAIZ / "data" / ("normas_todas.json" if TIPOS == ["ley"] else f"normas_{'_'.join(TIPOS)}.json")


if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else ""
    _elegir_tipos(sys.argv[2:])
    {"tipos": tipos, "listar": listar, "descargar": descargar, "cargar": cargar}.get(etapa, lambda: print(__doc__))()
