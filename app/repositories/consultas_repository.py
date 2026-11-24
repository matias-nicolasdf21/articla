"""Capa de datos: consultas SQL de `consultas` y `consulta_citas`. Sin reglas de negocio.

`sesion` es un identificador anónimo que genera el navegador (no es un dato personal): si viene,
cada operación se limita a las consultas de esa sesión."""

COLUMNAS = "id, pregunta, respuesta, util, modo, duracion_ms, creada_en"


def _filtro(sesion: str | None, alias: str = "") -> tuple[str, tuple]:
    return (f" AND {alias}sesion = %s", (sesion,)) if sesion else ("", ())


def _con_citas(conn, filas: list[dict]) -> list[dict]:
    if not filas:
        return []
    ids = [f["id"] for f in filas]
    citas = conn.execute(
        """SELECT c.consulta_id, g.id AS fragmento_id, f.identificador AS fuente, g.articulo
           FROM consulta_citas c
           JOIN fragmentos g ON g.id = c.fragmento_id
           JOIN fuentes f ON f.id = g.fuente_id
           WHERE c.consulta_id = ANY(%s)
           ORDER BY c.consulta_id, c.orden, g.id""",
        (ids,),
    ).fetchall()
    por_consulta: dict[int, list] = {i: [] for i in ids}
    for c in citas:
        por_consulta[c["consulta_id"]].append(
            {"fragmento_id": c["fragmento_id"], "fuente": c["fuente"], "articulo": c["articulo"]}
        )
    return [{**f, "citas": por_consulta[f["id"]]} for f in filas]


def crear(conn, pregunta: str, respuesta: str, fragmento_ids: list[int],
          sesion: str | None = None, modo: str = "extractiva", duracion_ms: int | None = None,
          reutilizable: bool = False) -> dict:
    """Guarda la consulta y sus citas en una sola transacción (o se guarda todo o nada)."""
    with conn.transaction():
        fila = conn.execute(
            f"""INSERT INTO consultas (pregunta, respuesta, sesion, modo, duracion_ms, reutilizable)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING {COLUMNAS}""",
            (pregunta, respuesta, sesion, modo, duracion_ms, reutilizable),
        ).fetchone()
        for orden, fid in enumerate(fragmento_ids):
            conn.execute(
                "INSERT INTO consulta_citas (consulta_id, fragmento_id, orden) VALUES (%s, %s, %s)",
                (fila["id"], fid, orden),
            )
    return _con_citas(conn, [fila])[0]


# Normaliza una pregunta para reconocer repeticiones: minúsculas, sin signos ni espacios dobles.
NORMALIZAR = "btrim(regexp_replace(lower({}), '[¿?¡!.,;:\\s]+', ' ', 'g'))"


def buscar_reciente(conn, pregunta: str, dias: int) -> dict | None:
    """Última respuesta redactada con IA (con citas validadas y sin un "No me sirvió") a la misma pregunta en los últimos `dias` días (de cualquier sesión:
    solo se reutiliza el texto de la respuesta y sus citas, nunca quién preguntó)."""
    fila = conn.execute(
        f"""SELECT {COLUMNAS} FROM consultas
            WHERE reutilizable IS TRUE AND util IS NOT FALSE AND {NORMALIZAR.format('pregunta')} = {NORMALIZAR.format('%s')}
              AND creada_en > now() - make_interval(days => %s::int)
            ORDER BY creada_en DESC LIMIT 1""",
        (pregunta, dias),
    ).fetchone()
    return _con_citas(conn, [fila])[0] if fila else None


def listar(conn, limit: int, offset: int, sesion: str | None = None) -> tuple[list[dict], int]:
    filtro, p = _filtro(sesion)
    total = conn.execute(f"SELECT count(*) AS n FROM consultas WHERE TRUE{filtro}", p).fetchone()["n"]
    filas = conn.execute(
        f"""SELECT {COLUMNAS} FROM consultas WHERE TRUE{filtro}
            ORDER BY creada_en DESC, id DESC LIMIT %s OFFSET %s""",
        (*p, limit, offset),
    ).fetchall()
    return _con_citas(conn, filas), total


def obtener(conn, consulta_id: int, sesion: str | None = None) -> dict | None:
    filtro, p = _filtro(sesion)
    fila = conn.execute(
        f"SELECT {COLUMNAS} FROM consultas WHERE id = %s{filtro}", (consulta_id, *p)
    ).fetchone()
    return _con_citas(conn, [fila])[0] if fila else None


def actualizar_util(conn, consulta_id: int, util: bool | None, sesion: str | None = None) -> dict | None:
    filtro, p = _filtro(sesion)
    fila = conn.execute(
        f"UPDATE consultas SET util = %s WHERE id = %s{filtro} RETURNING {COLUMNAS}",
        (util, consulta_id, *p),
    ).fetchone()
    if fila and util is False:
        # "No me sirvió" sobre una respuesta (original o copia del caché): ninguna respuesta guardada
        # a esa misma pregunta se vuelve a reutilizar; la próxima vez se redacta de nuevo.
        conn.execute(
            f"""UPDATE consultas SET reutilizable = FALSE
                WHERE reutilizable AND {NORMALIZAR.format('pregunta')} = {NORMALIZAR.format('%s')}""",
            (fila["pregunta"],),
        )
    return _con_citas(conn, [fila])[0] if fila else None


def eliminar(conn, consulta_id: int, sesion: str | None = None) -> bool:
    filtro, p = _filtro(sesion)
    return conn.execute(f"DELETE FROM consultas WHERE id = %s{filtro}", (consulta_id, *p)).rowcount > 0


def eliminar_de_sesion(conn, sesion: str) -> int:
    return conn.execute("DELETE FROM consultas WHERE sesion = %s", (sesion,)).rowcount


def purgar_antiguas(conn, dias: int) -> int:
    """Borra las consultas con más de `dias` días (promesa de conservación del Hito 1)."""
    return conn.execute(
        "DELETE FROM consultas WHERE creada_en < now() - make_interval(days => %s::int)", (dias,)
    ).rowcount
