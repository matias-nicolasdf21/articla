"""Capa de datos: consultas SQL de `fragmentos` (los artículos cargados desde LeyChile)."""

# Artículos "modificatorios" ("Modifícase…", "Reemplázase…", "Derógase…"): cambian otra ley y no explican
# derechos por sí mismos. Se marcan una vez y no se usan para responder (sí se ven en la Biblioteca).
REGEX_MODIFICATORIO = (r"^[\s\"“”'«]*((art[íi]culo|art\.)\s+[^\s]+\s*[.:º°\-–]*\s*)?"
                       r"(modif[íi]ca|reempl[áa]za|introd[úu]ce|agr[ée]ga|der[óo]ga|sustit[úu]ye|interc[áa]la|"
                       r"supr[íi]me|incorp[óo]ra)n?se\M")
UTIL = "g.modificatorio IS NOT TRUE"

SELECT = """SELECT g.id, g.fuente_id, f.identificador AS fuente, f.titulo AS fuente_titulo,
                   f.url_oficial, g.articulo, g.texto, g.ubicacion, g.fecha_version
            FROM fragmentos g JOIN fuentes f ON f.id = g.fuente_id"""


def obtener(conn, fragmento_id: int) -> dict | None:
    return conn.execute(f"{SELECT} WHERE g.id = %s", (fragmento_id,)).fetchone()


def listar_por_fuente(conn, fuente_id: int, limit: int, offset: int) -> tuple[list[dict], int]:
    total = conn.execute(
        "SELECT count(*) AS n FROM fragmentos WHERE fuente_id = %s", (fuente_id,)
    ).fetchone()["n"]
    items = conn.execute(
        f"{SELECT} WHERE g.fuente_id = %s ORDER BY g.id LIMIT %s OFFSET %s",
        (fuente_id, limit, offset),
    ).fetchall()
    return items, total


def buscar(conn, consulta_tsquery: str, limite: int) -> list[dict]:
    """Búsqueda por palabras (texto completo en español de PostgreSQL), ordenada por relevancia."""
    return conn.execute(
        f"""{SELECT}
            CROSS JOIN to_tsquery('spanish', %(q)s) AS q
            WHERE to_tsvector('spanish', g.texto) @@ q AND {UTIL}
            ORDER BY ts_rank(to_tsvector('spanish', g.texto), q) DESC, g.id
            LIMIT %(limite)s""",
        {"q": consulta_tsquery, "limite": limite},
    ).fetchall()


def buscar_semantico(conn, vector_literal: str, limite: int) -> list[dict]:
    """Búsqueda por significado: los artículos cuyo embedding está más cerca (distancia coseno, índice HNSW)."""
    conn.execute("SET hnsw.ef_search = 100")   # más candidatos, porque luego se filtran los modificatorios
    return conn.execute(
        f"""{SELECT}
            WHERE g.embedding IS NOT NULL AND {UTIL}
            ORDER BY g.embedding <=> %(v)s::vector, g.id
            LIMIT %(limite)s""",
        {"v": vector_literal, "limite": limite},
    ).fetchall()


# Compara sin puntos y sin el sufijo " (idNorma …)" que llevan las normas con número repetido.
FILTRO_FUENTES = "lower(replace(split_part(f.identificador, ' (', 1), '.', '')) = ANY(%(ids)s)"


def buscar_articulos(conn, pares: list[tuple[str, str]]) -> list[dict]:
    """Trae artículos concretos, p. ej. [('codigo civil', 'art. 1545')], en el orden pedido.
    Los que no existen en la base simplemente no aparecen (nada se inventa)."""
    if not pares:
        return []
    return conn.execute(
        f"""{SELECT}
            JOIN unnest(%(ids)s::text[], %(arts)s::text[]) WITH ORDINALITY AS p(ident, art, n)
              ON lower(replace(split_part(f.identificador, ' (', 1), '.', '')) = p.ident
             AND regexp_replace(lower(g.articulo), '[[:space:]-]', '', 'g') = regexp_replace(p.art, '[[:space:]-]', '', 'g')
            WHERE {UTIL}
            ORDER BY p.n, g.id""",
        {"ids": [i for i, _ in pares], "arts": [a for _, a in pares]},
    ).fetchall()


def buscar_en_fuentes(conn, identificadores: list[str], consulta_tsquery: str, limite: int) -> list[dict]:
    """Búsqueda por palabras solo dentro de las leyes indicadas (identificadores normalizados, sin puntos)."""
    if not identificadores or not consulta_tsquery:
        return []
    return conn.execute(
        f"""{SELECT}
            CROSS JOIN to_tsquery('spanish', %(q)s) AS q
            WHERE {FILTRO_FUENTES} AND to_tsvector('spanish', g.texto) @@ q AND {UTIL}
            ORDER BY ts_rank(to_tsvector('spanish', g.texto), q) DESC, g.id
            LIMIT %(limite)s""",
        {"ids": identificadores, "q": consulta_tsquery, "limite": limite},
    ).fetchall()


def buscar_semantico_en_fuentes(conn, identificadores: list[str], vector_literal: str, limite: int) -> list[dict]:
    """Búsqueda por significado solo dentro de las leyes indicadas."""
    if not identificadores:
        return []
    return conn.execute(
        f"""{SELECT}
            WHERE {FILTRO_FUENTES} AND g.embedding IS NOT NULL AND {UTIL}
            ORDER BY (g.embedding <=> %(v)s::vector) + 0, g.id   -- "+ 0": recorre solo esas leyes, sin el índice HNSW
            LIMIT %(limite)s""",
        {"ids": identificadores, "v": vector_literal, "limite": limite},
    ).fetchall()


# --- usados por scripts/calcular_embeddings.py ---
def pendientes_de_embedding(conn, limite: int) -> list[dict]:
    return conn.execute(
        """SELECT g.id, f.titulo AS fuente_titulo, g.articulo, g.texto
           FROM fragmentos g JOIN fuentes f ON f.id = g.fuente_id
           WHERE g.embedding IS NULL ORDER BY g.id LIMIT %s""", (limite,)
    ).fetchall()


def guardar_embeddings(conn, pares: list[tuple[int, str]]) -> None:
    with conn.cursor() as cur:
        cur.executemany("UPDATE fragmentos SET embedding = %s::vector WHERE id = %s",
                        [(v, i) for i, v in pares])


def contar_sin_embedding(conn) -> int:
    return conn.execute("SELECT count(*) AS n FROM fragmentos WHERE embedding IS NULL").fetchone()["n"]


def estadisticas(conn) -> dict:
    return conn.execute(
        """SELECT (SELECT count(*) FROM fuentes) AS fuentes,
                  (SELECT count(*) FROM fragmentos) AS articulos,
                  (SELECT count(*) FROM fragmentos WHERE embedding IS NOT NULL) AS con_embedding,
                  (SELECT max(fecha_version) FROM fragmentos) AS version_mas_reciente"""
    ).fetchone()


def marcar_modificatorios(conn) -> int:
    """Marca los artículos que solo modifican otra ley. Los nuevos se evalúan una vez; además se revisan
    los ya marcados como útiles, por si la regla mejoró (p. ej. textos que empiezan con comillas, como
    el art. 1 de la Ley 21.643). La expresión está anclada al inicio, así que la revisión es rápida."""
    nuevos = conn.execute(
        "UPDATE fragmentos g SET modificatorio = (g.texto ~* %s) WHERE g.modificatorio IS NULL",
        (REGEX_MODIFICATORIO,),
    ).rowcount
    corregidos = conn.execute(
        "UPDATE fragmentos g SET modificatorio = TRUE WHERE g.modificatorio IS FALSE AND g.texto ~* %s",
        (REGEX_MODIFICATORIO,),
    ).rowcount
    return nuevos + corregidos
