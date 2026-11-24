"""Lectura del XML oficial de LeyChile (Biblioteca del Congreso Nacional).

Descarga de cada norma:  https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma=<ID>
Esta capa solo convierte el XML en artículos (no toca la base de datos), así se puede probar sola.
"""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

NS = "{http://www.leychile.cl/esquemas}"


@dataclass
class Articulo:
    articulo: str            # etiqueta que se cita, p. ej. 'art. 1545' o 'art. 1 transitorio'
    texto: str               # texto oficial del artículo
    ubicacion: str           # p. ej. 'LIBRO CUARTO … > Título XII …'
    fecha_version: date | None
    id_parte: str            # identificador de la parte en LeyChile (trazabilidad)


@dataclass
class Norma:
    id_norma: str
    titulo: str
    nombre_comun: str
    articulos: list
    derogados_omitidos: int


def _limpiar(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def _texto_limpio(s: str) -> str:
    """El XML corta las líneas a ~60 caracteres: se unen y se conservan los párrafos."""
    s = re.sub(r"\n\s{3,}", "\n\n", s.strip())      # sangría = párrafo nuevo
    s = re.sub(r"(?<!\n)\n(?!\n)", " ", s)           # salto simple = misma línea
    return "\n\n".join(re.sub(r"[ \t]+", " ", p).strip() for p in s.split("\n\n") if p.strip())


def _etiqueta(nombre: str, transitorio: bool) -> str:
    n = re.sub(r"\s*\(DEL ART\.?[^)]*\)", "", nombre)   # el Código Civil viene dentro de un DFL
    n = _limpiar(n).replace("º", "").replace("°", "").rstrip(".")
    n = n.lower() if n.isalpha() else n
    if transitorio and n != "transitorio":
        n += " transitorio"
    return f"art. {n}"


def _es_derogado(texto: str) -> bool:
    """True si el artículo es solo la marca 'Derogado' (p. ej. 'Art. 29. Derogado. L. 19.585')."""
    t = _limpiar(texto)
    return bool(re.match(r"Art(?:ículo|\.)\s+\S+\s*[-–]?\s*(Derogado|Suprimido)\b", t, flags=re.I))


def _seccion(tp: str, nombre: str, titulo: str) -> str:
    return _limpiar(titulo) or _limpiar(nombre) or tp


def leer_norma(ruta_xml: str, parte_raiz: str | None = None) -> Norma:
    """Lee una norma. Con `parte_raiz` solo toma el articulado de ese artículo raíz.

    El Código Civil se publica como el artículo 2 de un decreto con fuerza de ley (DFL N.º 1 de 2000),
    junto a otras leyes refundidas; para quedarnos solo con el Código se usa parte_raiz="2".
    """
    raiz = ET.parse(ruta_xml).getroot()
    meta = raiz.find(NS + "Metadatos")
    titulo = _limpiar(meta.findtext(NS + "TituloNorma")) if meta is not None else ""
    nombre = _limpiar(meta.findtext(f"{NS}NombresUsoComun/{NS}NombreUsoComun")) if meta is not None else ""
    salida, omitidos, usados = [], 0, {}

    def recorrer(nodo, secciones, transitorio):
        nonlocal omitidos
        for ef in nodo.findall(f"{NS}EstructurasFuncionales/{NS}EstructuraFuncional"):
            tp = ef.attrib.get("tipoParte", "")
            nom = ef.findtext(f"{NS}Metadatos/{NS}NombreParte") or ""
            tit = ef.findtext(f"{NS}Metadatos/{NS}TituloParte") or ""
            trans = transitorio or ef.attrib.get("transitorio") == "transitorio"
            if tp == "Artículo":
                texto = (ef.findtext(NS + "Texto") or "").strip()
                if not _limpiar(nom) and not re.match(r"\s*Art", texto, flags=re.I):
                    omitidos += 1          # texto sin número que no es un artículo (p. ej. la ley que aprueba el Código)
                elif texto and ef.attrib.get("derogado") == "no derogado" and not _es_derogado(texto):
                    etiqueta = _etiqueta(nom, trans)
                    usados[etiqueta] = usados.get(etiqueta, 0) + 1
                    if usados[etiqueta] > 1:           # mismo número repetido en el XML
                        etiqueta += f" ({usados[etiqueta]})"
                    try:
                        fv = date.fromisoformat(ef.attrib.get("fechaVersion", ""))
                    except ValueError:
                        fv = None
                    salida.append(Articulo(etiqueta, _texto_limpio(texto), " > ".join(secciones), fv,
                                           ef.attrib.get("idParte", "")))
                elif texto:
                    omitidos += 1
                recorrer(ef, secciones, trans)
            elif tp == "Doble Articulado":          # envoltorio del DFL: no es una sección del Código
                recorrer(ef, secciones, trans)
            else:
                recorrer(ef, secciones + [_seccion(tp, nom, tit)], trans)

    if parte_raiz is None:
        recorrer(raiz, [], False)
    else:
        for ef in raiz.findall(f"{NS}EstructurasFuncionales/{NS}EstructuraFuncional"):
            nombre_parte = _limpiar(ef.findtext(f"{NS}Metadatos/{NS}NombreParte"))
            if nombre_parte.split(" ")[0] == parte_raiz:     # p. ej. '7 (LEY SOBRE ABANDONO DE FAMILIA…)'
                recorrer(ef, [], False)
    return Norma(raiz.attrib.get("normaId", ""), titulo, nombre, salida, omitidos)
