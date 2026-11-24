"""Deja la base lista para usar, sin pasos manuales. Lo ejecuta el contenedor de la API al iniciar.

1. Espera a que PostgreSQL responda.
2. Aplica las migraciones (columnas nuevas del Hito 3) sin borrar datos: se puede repetir.
3. Si no hay artículos cargados, descarga los XML que falten y carga las normas de data/normas.json desde data/leychile/*.xml.
4. Calcula los embeddings que falten (si el modelo está disponible).

Uso:  python -m scripts.preparar
"""
import time

import psycopg
from psycopg.rows import dict_row

from app.config import get_database_url
from app.ingesta.leychile import leer_norma
from scripts import calcular_embeddings, cargar_leychile, descargar_leychile

MIGRACIONES = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    "ALTER TABLE fragmentos ALTER COLUMN ubicacion TYPE TEXT",
    "ALTER TABLE fragmentos ALTER COLUMN articulo TYPE VARCHAR(100)",
    "ALTER TABLE fragmentos ADD COLUMN IF NOT EXISTS fecha_version DATE",
    "ALTER TABLE consultas ADD COLUMN IF NOT EXISTS sesion VARCHAR(64)",
    "ALTER TABLE consultas ADD COLUMN IF NOT EXISTS modo VARCHAR(20)",
    "ALTER TABLE consultas ADD COLUMN IF NOT EXISTS duracion_ms INTEGER",
    "ALTER TABLE consulta_citas ADD COLUMN IF NOT EXISTS orden SMALLINT NOT NULL DEFAULT 0",
    "CREATE INDEX IF NOT EXISTS idx_consultas_sesion ON consultas(sesion)",
    "ALTER TABLE consultas ADD COLUMN IF NOT EXISTS reutilizable BOOLEAN",
    "DROP INDEX IF EXISTS idx_consultas_modo_fecha",
    "CREATE INDEX IF NOT EXISTS idx_consultas_reutilizables ON consultas(creada_en) WHERE reutilizable",
    "ALTER TABLE fragmentos ADD COLUMN IF NOT EXISTS modificatorio BOOLEAN",
    "CREATE INDEX IF NOT EXISTS idx_fragmentos_texto ON fragmentos USING gin (to_tsvector('spanish', texto))",
]


def esperar_base(intentos: int = 60):
    for i in range(intentos):
        try:
            return psycopg.connect(get_database_url(), autocommit=True, row_factory=dict_row)
        except psycopg.OperationalError:
            print(f"[preparar] esperando a PostgreSQL ({i + 1}/{intentos})…")
            time.sleep(2)
    raise SystemExit("[preparar] PostgreSQL no respondió.")


def main() -> None:
    with esperar_base() as conn:
        for sql in MIGRACIONES:
            conn.execute(sql)
        print("[preparar] migraciones aplicadas")

        n = conn.execute("SELECT count(*) AS n FROM fragmentos").fetchone()["n"]
        if n == 0:
            if any(not (cargar_leychile.RAIZ / c["archivo"]).exists() for c in cargar_leychile.NORMAS):
                print("[preparar] faltan XML: se intenta descargarlos de LeyChile")
                descargar_leychile.main()
            cargadas = 0
            with conn.transaction():
                for cfg in cargar_leychile.NORMAS:
                    ruta = cargar_leychile.RAIZ / cfg["archivo"]
                    if not ruta.exists():
                        print(f"[preparar] falta {cfg['archivo']}: se omite {cfg['identificador']}")
                        continue
                    norma = leer_norma(ruta, cfg["parte_raiz"])
                    cargar_leychile.cargar(conn, cfg, norma)
                    cargadas += 1
                    print(f"[preparar] {cfg['identificador']}: {len(norma.articulos)} artículos")
            n = conn.execute("SELECT count(*) AS n FROM fragmentos").fetchone()["n"]
            print(f"[preparar] {cargadas} normas cargadas, {n} artículos en total")
        else:
            print(f"[preparar] corpus ya cargado ({n} artículos)")

        from app.repositories import fragmentos_repository
        n_mod = fragmentos_repository.marcar_modificatorios(conn)
        if n_mod:
            print(f"[preparar] {n_mod} artículos revisados (se marcan los que solo modifican otra ley)")
        calcular_embeddings.calcular(conn)
    print("[preparar] listo")


if __name__ == "__main__":
    main()
