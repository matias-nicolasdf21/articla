"""Capa de negocio: reglas de `fuentes`. No contiene SQL ni conoce HTTP."""
from app.errors import NoEncontrado, ReglaDeNegocio
from app.repositories import fuentes_repository

TIPOS = {"ley", "codigo", "libro"}
LICENCIA_POR_DEFECTO = "dominio publico"


def _preparar(datos: dict) -> dict:
    d = dict(datos)
    d["identificador"] = d["identificador"].strip()
    d["titulo"] = d["titulo"].strip()
    d.setdefault("url_oficial", None)
    if d["tipo"] not in TIPOS:
        raise ReglaDeNegocio(f"Tipo inválido: debe ser uno de {sorted(TIPOS)}.")
    # Regla de negocio: un libro puede tener derechos de autor, así que debe declarar su licencia.
    if d["tipo"] == "libro" and not d.get("licencia"):
        raise ReglaDeNegocio("Un libro debe declarar su licencia (p. ej. 'autorizacion escrita del autor'). Hoy el corpus usa solo el texto oficial de LeyChile.")
    d["licencia"] = d.get("licencia") or LICENCIA_POR_DEFECTO
    return d


def crear(conn, datos: dict, repo=fuentes_repository) -> dict:
    return repo.crear(conn, _preparar(datos))


def listar(conn, tipo: str | None, page: int, limit: int, repo=fuentes_repository, q: str | None = None) -> dict:
    if tipo is not None and tipo not in TIPOS:
        raise ReglaDeNegocio(f"Tipo inválido: debe ser uno de {sorted(TIPOS)}.")
    q = (q or "").strip()[:100] or None
    items, total = repo.listar(conn, tipo, limit, (page - 1) * limit, q=q)
    return {"items": items, "total": total, "page": page, "limit": limit}


def obtener(conn, fuente_id: int, repo=fuentes_repository) -> dict:
    fuente = repo.obtener(conn, fuente_id)
    if fuente is None:
        raise NoEncontrado(f"La fuente {fuente_id} no existe.")
    return fuente


def reemplazar(conn, fuente_id: int, datos: dict, repo=fuentes_repository) -> dict:
    fuente = repo.reemplazar(conn, fuente_id, _preparar(datos))
    if fuente is None:
        raise NoEncontrado(f"La fuente {fuente_id} no existe.")
    return fuente


def eliminar(conn, fuente_id: int, repo=fuentes_repository) -> None:
    if not repo.eliminar(conn, fuente_id):
        raise NoEncontrado(f"La fuente {fuente_id} no existe.")
