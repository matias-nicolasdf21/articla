"""Carga el texto oficial de LeyChile (XML en data/leychile/) a las tablas `fuentes` y `fragmentos`.

Uso (desde la carpeta del proyecto):
    python -m scripts.cargar_leychile --dry-run     # solo lee los XML y muestra los conteos (sin base de datos)
    python -m scripts.cargar_leychile               # carga a PostgreSQL (usa DATABASE_URL del .env)

Se puede ejecutar varias veces: la fuente se actualiza y sus fragmentos se reemplazan.
Los embeddings quedan en NULL: se calculan en el paso siguiente (búsqueda semántica).
"""
import argparse
import json
from pathlib import Path

from app.ingesta.leychile import leer_norma

RAIZ = Path(__file__).resolve().parent.parent

def _cargar_config() -> list:
    """Normas de data/normas.json (el Código Civil viene dentro del DFL N.º 1 de 2000: parte_raiz="2")."""
    lista = json.loads((RAIZ / "data" / "normas.json").read_text(encoding="utf-8"))
    return [{**n, "archivo": f"data/leychile/{n['archivo']}"} for n in lista]


NORMAS = _cargar_config()


def url_oficial(id_norma: str) -> str:
    return f"https://www.bcn.cl/leychile/navegar?idNorma={id_norma}"


def cargar(conn, cfg: dict, norma) -> int:
    fuente_id = conn.execute(
        """INSERT INTO fuentes (tipo, identificador, titulo, url_oficial, licencia)
           VALUES (%(tipo)s, %(identificador)s, %(titulo)s, %(url)s, 'dominio publico')
           ON CONFLICT (identificador) DO UPDATE
             SET tipo = EXCLUDED.tipo, titulo = EXCLUDED.titulo, url_oficial = EXCLUDED.url_oficial
           RETURNING id""",
        {**cfg, "url": url_oficial(norma.id_norma)},
    ).fetchone()["id"]
    conn.execute("DELETE FROM fragmentos WHERE fuente_id = %s", (fuente_id,))
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO fragmentos (fuente_id, articulo, texto, ubicacion, fecha_version)
               VALUES (%s, %s, %s, %s, %s)""",
            [(fuente_id, a.articulo, a.texto, a.ubicacion, a.fecha_version) for a in norma.articulos],
        )
    return fuente_id


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="no escribe en la base de datos")
    args = ap.parse_args()

    normas = []
    for cfg in NORMAS:
        ruta = RAIZ / cfg["archivo"]
        if not ruta.exists():
            print(f"- {cfg['identificador']}: falta el archivo (ejecuta: python -m scripts.descargar_leychile)")
            continue
        n = leer_norma(ruta, cfg["parte_raiz"])
        normas.append((cfg, n))
        print(f"{cfg['identificador']}: {len(n.articulos)} artículos vigentes "
              f"({n.derogados_omitidos} derogados omitidos) · idNorma {n.id_norma} · {n.titulo[:70]}")
        for a in n.articulos[:2] + n.articulos[-1:]:
            print(f"     {a.articulo}: {a.texto[:90].replace(chr(10), ' ')}")
    if args.dry_run:
        return

    import psycopg
    from psycopg.rows import dict_row
    from app.config import get_database_url

    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:   # una sola transacción
        for cfg, n in normas:
            cargar(conn, cfg, n)
    print("Carga terminada.")


if __name__ == "__main__":
    main()
