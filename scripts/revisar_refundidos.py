"""Busca leyes cuyo texto vigente vive en un texto refundido (DFL o decreto) y no en su ficha original.

Uso:  docker compose exec api python scripts/revisar_refundidos.py

En LeyChile, cuando el gobierno dicta un "texto refundido, coordinado y sistematizado" de una ley,
las reformas posteriores se aplican al refundido y la ficha original de la ley deja de actualizarse.
Así ocurrió con la Ley 19.496 (refundida en el DFL 3 de 2019): Articla decía que la garantía legal
dura tres meses porque leía la ficha original. Este script lista los pares "ley original / refundido"
que hay en la base, para revisar si alguna respuesta podría estar leyendo una versión congelada.
Solo lee: no cambia nada.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app.config import get_database_url  # noqa: E402

PATRON = re.compile(r"REFUNDIDO.*?LEY\s+N[°º.]*\s*([\d.]+)", re.IGNORECASE)


def main() -> None:
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        refundidos = conn.execute(
            """SELECT f.identificador, f.titulo, count(g.id) AS articulos
               FROM fuentes f LEFT JOIN fragmentos g ON g.fuente_id = f.id
               WHERE f.titulo ILIKE '%%refundido%%' GROUP BY f.id ORDER BY f.identificador"""
        ).fetchall()
        originales = {r["clave"]: r for r in conn.execute(
            """SELECT lower(replace(split_part(identificador, ' (', 1), '.', '')) AS clave, identificador
               FROM fuentes WHERE identificador ILIKE 'ley %%'"""
        ).fetchall()}

    pares = []
    for r in refundidos:
        m = PATRON.search(r["titulo"] or "")
        if not m:
            continue
        clave = "ley " + m.group(1).replace(".", "").strip()
        if clave in originales:
            pares.append((originales[clave]["identificador"], r["identificador"], r["articulos"]))

    print(f"Textos refundidos en la base: {len(refundidos)}")
    print(f"Leyes que además tienen su ficha original cargada: {len(pares)}\n")
    for ley, refundido, n in pares:
        print(f"  {ley:<28} -> vigente en {refundido} ({n} artículos)")
    print("\nSi una de estas leyes está entre las normas base (data/normas.json), su 'id' debe ser el del"
          " refundido, como se hizo con la Ley 19.496 (idNorma 1160403).")


if __name__ == "__main__":
    main()
