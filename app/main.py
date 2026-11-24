from contextlib import asynccontextmanager

import psycopg
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_database_url, origenes_permitidos, retencion_dias
from app.database import get_conn
from app.errors import ErrorDeAplicacion
from app.repositories import consultas_repository
from app.routers import consultas, estadisticas, fragmentos, fuentes


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    """Al iniciar, borra las consultas más antiguas que el plazo de conservación (90 días por defecto)."""
    try:
        with psycopg.connect(get_database_url(), autocommit=True) as conn:
            n = consultas_repository.purgar_antiguas(conn, retencion_dias())
            if n:
                print(f"[retención] {n} consultas con más de {retencion_dias()} días borradas")
    except Exception as e:
        print(f"[retención] no se pudo ejecutar: {e}")
    from app.ia import embeddings
    print(f"[embeddings] {'listo' if embeddings.disponible() else 'no disponible: se busca solo por palabras'}")
    yield


app = FastAPI(title="Articla API", version="1.0.0", lifespan=ciclo_de_vida)
app.add_middleware(CORSMiddleware, allow_origins=origenes_permitidos(),
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(fuentes.router)
app.include_router(fragmentos.router)
app.include_router(consultas.router)
app.include_router(estadisticas.router)


def _error(status: int, codigo: str, mensaje: str, detalle=None) -> JSONResponse:
    cuerpo = {"error": {"codigo": codigo, "mensaje": mensaje}}
    if detalle is not None:
        cuerpo["error"]["detalle"] = detalle
    return JSONResponse(status_code=status, content=cuerpo)


@app.exception_handler(ErrorDeAplicacion)
async def manejar_error_de_aplicacion(_: Request, e: ErrorDeAplicacion):
    return _error(e.status, e.codigo, e.mensaje)


@app.exception_handler(RequestValidationError)
async def manejar_validacion(_: Request, e: RequestValidationError):
    return _error(422, "DATOS_INVALIDOS", "Los datos enviados no son válidos.", jsonable_encoder(e.errors()))


@app.exception_handler(psycopg.OperationalError)
async def manejar_base_caida(_: Request, e: psycopg.OperationalError):
    return _error(503, "BASE_DE_DATOS_NO_DISPONIBLE", "No se pudo conectar con la base de datos.")


@app.get("/api/v1/salud")
def salud(conn=Depends(get_conn)):
    conn.execute("SELECT 1")
    return {"estado": "ok"}
