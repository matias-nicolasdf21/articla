"""Capa de ruteo: cifras del corpus cargado."""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.database import get_conn
from app.services import fragmentos_service as service

router = APIRouter(prefix="/api/v1/estadisticas", tags=["estadisticas"])


class Estadisticas(BaseModel):
    fuentes: int
    articulos: int
    con_embedding: int
    version_mas_reciente: date | None = None


@router.get("", response_model=Estadisticas)
def obtener(conn=Depends(get_conn)):
    return service.estadisticas(conn)
