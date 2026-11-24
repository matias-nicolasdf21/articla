"""Calcula el embedding de cada artículo que todavía no lo tiene (búsqueda por significado).

Uso:  python -m scripts.calcular_embeddings
Se puede interrumpir y repetir: solo procesa los artículos con embedding vacío.
"""
import time

from app.ia import embeddings
from app.repositories import fragmentos_repository as repo

LOTE = 256
LARGO_MAX = 1000   # el modelo solo lee el comienzo del texto (unas 128 palabras)


def texto_para_vector(f: dict) -> str:
    return f"{f['fuente_titulo']}, {f['articulo']}. {f['texto']}"[:LARGO_MAX]


def calcular(conn, avisar=print) -> int:
    if not embeddings.disponible():
        avisar("[embeddings] modelo no disponible: se omite (la búsqueda usará solo palabras).")
        return 0
    total, hechos, inicio = repo.contar_sin_embedding(conn), 0, time.monotonic()
    while True:
        filas = repo.pendientes_de_embedding(conn, LOTE)
        if not filas:
            break
        vectores = embeddings.vectorizar([texto_para_vector(f) for f in filas])
        repo.guardar_embeddings(conn, [(f["id"], embeddings.como_literal(v)) for f, v in zip(filas, vectores)])
        hechos += len(filas)
        avisar(f"[embeddings] {hechos}/{total} artículos ({time.monotonic() - inicio:.0f} s)")
    return hechos


def main() -> None:
    import psycopg
    from psycopg.rows import dict_row
    from app.config import get_database_url
    with psycopg.connect(get_database_url(), autocommit=True, row_factory=dict_row) as conn:
        calcular(conn)


if __name__ == "__main__":
    main()
