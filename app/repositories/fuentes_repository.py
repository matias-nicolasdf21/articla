"""Capa de datos: aquí viven TODAS las consultas SQL de `fuentes`. Sin reglas de negocio."""
from psycopg import errors as pgerr

from app.errors import Conflicto

COLUMNAS = "id, tipo, identificador, titulo, url_oficial, licencia, creada_en"


def crear(conn, d: dict) -> dict:
    try:
        return conn.execute(
            f"""INSERT INTO fuentes (tipo, identificador, titulo, url_oficial, licencia)
                VALUES (%(tipo)s, %(identificador)s, %(titulo)s, %(url_oficial)s, %(licencia)s)
                RETURNING {COLUMNAS}""",
            d,
        ).fetchone()
    except pgerr.UniqueViolation:
        raise Conflicto(f"Ya existe una fuente con identificador '{d['identificador']}'.")


def listar(conn, tipo: str | None, limit: int, offset: int, q: str | None = None) -> tuple[list[dict], int]:
    condiciones = []
    if tipo:
        condiciones.append("tipo = %(tipo)s")
    if q:
        condiciones.append("(titulo ILIKE %(q)s OR replace(identificador, '.', '') ILIKE %(qn)s)")
    filtro = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    params = {"tipo": tipo, "q": f"%{q}%" if q else None,
              "qn": f"%{q.replace('.', '')}%" if q else None, "limit": limit, "offset": offset}
    total = conn.execute(f"SELECT count(*) AS n FROM fuentes {filtro}", params).fetchone()["n"]
    items = conn.execute(
        f"""SELECT {COLUMNAS},
                   (SELECT count(*) FROM fragmentos g WHERE g.fuente_id = fuentes.id) AS articulos
            FROM fuentes {filtro} ORDER BY id LIMIT %(limit)s OFFSET %(offset)s""",
        params,
    ).fetchall()
    return items, total


def obtener(conn, fuente_id: int) -> dict | None:
    return conn.execute(
        f"""SELECT {COLUMNAS},
                   (SELECT count(*) FROM fragmentos g WHERE g.fuente_id = fuentes.id) AS articulos
            FROM fuentes WHERE id = %s""", (fuente_id,)
    ).fetchone()


def reemplazar(conn, fuente_id: int, d: dict) -> dict | None:
    try:
        return conn.execute(
            f"""UPDATE fuentes SET tipo=%(tipo)s, identificador=%(identificador)s, titulo=%(titulo)s,
                    url_oficial=%(url_oficial)s, licencia=%(licencia)s
                WHERE id=%(id)s RETURNING {COLUMNAS}""",
            {**d, "id": fuente_id},
        ).fetchone()
    except pgerr.UniqueViolation:
        raise Conflicto(f"Ya existe una fuente con identificador '{d['identificador']}'.")


def eliminar(conn, fuente_id: int) -> bool:
    cur = conn.execute("DELETE FROM fuentes WHERE id = %s", (fuente_id,))
    return cur.rowcount > 0
