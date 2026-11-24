"""Capa de negocio de `fragmentos`: lectura de los artículos del corpus."""
from app.errors import NoEncontrado
from app.repositories import fragmentos_repository, fuentes_repository


def obtener(conn, fragmento_id: int, repo=fragmentos_repository) -> dict:
    f = repo.obtener(conn, fragmento_id)
    if f is None:
        raise NoEncontrado(f"El fragmento {fragmento_id} no existe.")
    return f


def listar_por_fuente(conn, fuente_id: int, page: int, limit: int,
                      repo=fragmentos_repository, repo_fuentes=fuentes_repository) -> dict:
    if repo_fuentes.obtener(conn, fuente_id) is None:
        raise NoEncontrado(f"La fuente {fuente_id} no existe.")
    items, total = repo.listar_por_fuente(conn, fuente_id, limit, (page - 1) * limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


def estadisticas(conn, repo=fragmentos_repository) -> dict:
    """Tamaño del corpus cargado (lo muestra la página de inicio)."""
    return repo.estadisticas(conn)
