-- Articla · Script de creación de la base de datos (versión final, Hito 3)
-- Motor: PostgreSQL 15+ con la extensión pgvector
-- Uso:   createdb articla && psql -d articla -f db/schema.sql

CREATE EXTENSION IF NOT EXISTS vector;

-- Limpieza para poder re-ejecutar el script desde cero
DROP TABLE IF EXISTS consulta_citas CASCADE;
DROP TABLE IF EXISTS consultas      CASCADE;
DROP TABLE IF EXISTS fragmentos     CASCADE;
DROP TABLE IF EXISTS fuentes        CASCADE;

-- Recurso 1: fuentes del corpus (leyes, códigos, libros)
CREATE TABLE fuentes (
    id            SERIAL PRIMARY KEY,
    tipo          VARCHAR(20)  NOT NULL CHECK (tipo IN ('ley', 'codigo', 'libro')),
    identificador VARCHAR(100) NOT NULL UNIQUE,   -- p. ej. 'Ley 18.101'
    titulo        VARCHAR(300) NOT NULL,
    url_oficial   TEXT,                           -- enlace a LeyChile u otra fuente
    licencia      VARCHAR(60)  NOT NULL DEFAULT 'dominio publico',
    creada_en     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Fragmentos (un artículo por fila, cargados desde el XML oficial de LeyChile) con su embedding para búsqueda semántica.
-- La dimensión 384 es un valor inicial: debe coincidir con el modelo de embeddings elegido.
CREATE TABLE fragmentos (
    id         SERIAL PRIMARY KEY,
    fuente_id  INTEGER      NOT NULL REFERENCES fuentes(id) ON DELETE CASCADE,
    articulo   VARCHAR(100),                      -- p. ej. 'art. 1545'
    texto      TEXT         NOT NULL,
    ubicacion  TEXT,                              -- p. ej. 'LIBRO CUARTO … > Título XII …'
    fecha_version DATE,                           -- fecha de la versión del artículo en LeyChile
    modificatorio BOOLEAN,                        -- true si solo modifica otra ley: no se usa para responder
    embedding  vector(384)
);
CREATE INDEX idx_fragmentos_fuente ON fragmentos(fuente_id);
-- Búsqueda de texto en español (provisoria, antes de la búsqueda semántica)
CREATE INDEX idx_fragmentos_texto ON fragmentos USING gin (to_tsvector('spanish', texto));
CREATE INDEX idx_fragmentos_embedding ON fragmentos
    USING hnsw (embedding vector_cosine_ops);

-- Recurso 2: consultas (pregunta del usuario y respuesta generada)
CREATE TABLE consultas (
    id         SERIAL PRIMARY KEY,
    pregunta   TEXT        NOT NULL CHECK (length(trim(pregunta)) >= 5),
    respuesta  TEXT,
    util       BOOLEAN,                           -- feedback opcional del usuario
    sesion     VARCHAR(64),                       -- identificador anónimo del navegador (no es dato personal)
    modo       VARCHAR(20),                       -- 'ia' (redactada por el modelo) o 'extractiva' (respaldo)
    duracion_ms INTEGER,                          -- tiempo de respuesta (métrica: menos de 1 minuto)
    reutilizable BOOLEAN,                         -- respuesta con IA y citas validadas: se reutiliza si se repite la pregunta
    creada_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_consultas_sesion ON consultas(sesion);
CREATE INDEX idx_consultas_reutilizables ON consultas(creada_en) WHERE reutilizable;  -- preguntas repetidas

-- Relación N:M entre consultas y los fragmentos que citó la respuesta
CREATE TABLE consulta_citas (
    consulta_id  INTEGER NOT NULL REFERENCES consultas(id)   ON DELETE CASCADE,
    fragmento_id INTEGER NOT NULL REFERENCES fragmentos(id)  ON DELETE CASCADE,
    orden        SMALLINT NOT NULL DEFAULT 0,          -- orden en que la respuesta cita los artículos
    PRIMARY KEY (consulta_id, fragmento_id)
);

-- El corpus (fuentes y artículos) lo carga scripts/preparar.py desde los XML oficiales de LeyChile.
