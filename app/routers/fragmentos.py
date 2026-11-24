"""Ruteo de `fragmentos`: solo lectura (el corpus se carga con scripts/cargar_leychile.py)."""
from fastapi import APIRouter, Depends, Query

from app.database import get_conn
from app.schemas.fragmentos import FragmentoLista, FragmentoSalida
from app.services import fragmentos_service as service

router = APIRouter(prefix="/api/v1", tags=["fragmentos"])


@router.get("/fuentes/{fuente_id}/fragmentos", response_model=FragmentoLista)
def listar_de_una_fuente(
    fuente_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_conn),
):
    return service.listar_por_fuente(conn, fuente_id, page, limit)


@router.get("/fragmentos/{fragmento_id}", response_model=FragmentoSalida)
def obtener(fragmento_id: int, conn=Depends(get_conn)):
    return service.obtener(conn, fragmento_id)
