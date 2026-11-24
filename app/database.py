import psycopg
from psycopg.rows import dict_row

from app.config import get_database_url


def get_conn():
    """Una conexión por petición. autocommit: cada escritura queda confirmada al ejecutarse."""
    with psycopg.connect(get_database_url(), autocommit=True, row_factory=dict_row) as conn:
        yield conn
