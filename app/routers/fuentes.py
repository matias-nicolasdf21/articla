"""Capa de ruteo: solo traduce HTTP <-> servicio. No contiene lógica de negocio ni SQL."""
from fastapi import APIRouter, Depends, Query, Response, status

from app.database import get_conn
from app.schemas.fuentes import FuenteEntrada, FuenteLista, FuenteSalida
from app.services import fuentes_service as service

router = APIRouter(prefix="/api/v1/fuentes", tags=["fuentes"])


@router.post("", response_model=FuenteSalida, status_code=status.HTTP_201_CREATED)
def crear(cuerpo: FuenteEntrada, conn=Depends(get_conn)):
    return service.crear(conn, cuerpo.model_dump())


@router.get("", response_model=FuenteLista)
def listar(
    tipo: str | None = None,
    q: str | None = Query(None, description="Texto a buscar en el título o identificador"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_conn),
):
    return service.listar(conn, tipo, page, limit, q=q)


@router.get("/{fuente_id}", response_model=FuenteSalida)
def obtener(fuente_id: int, conn=Depends(get_conn)):
    return service.obtener(conn, fuente_id)


@router.put("/{fuente_id}", response_model=FuenteSalida)
def reemplazar(fuente_id: int, cuerpo: FuenteEntrada, conn=Depends(get_conn)):
    return service.reemplazar(conn, fuente_id, cuerpo.model_dump())


@router.delete("/{fuente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(fuente_id: int, conn=Depends(get_conn)):
    service.eliminar(conn, fuente_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
