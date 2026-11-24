"""Capa de ruteo de `consultas`: solo traduce HTTP <-> servicio.

La cabecera opcional `X-Sesion` es un identificador anónimo generado por el navegador: si viene,
el historial se limita a esa sesión."""
from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.database import get_conn
from app.ia.embeddings import Vectorizador
from app.ia.gemini import ClienteGemini
from app.schemas.consultas import ConsultaEntrada, ConsultaFeedback, ConsultaLista, ConsultaSalida
from app.services import consultas_service as service

router = APIRouter(prefix="/api/v1/consultas", tags=["consultas"])
_vectorizador = Vectorizador()


@router.post("", response_model=ConsultaSalida, status_code=status.HTTP_201_CREATED)
def crear(cuerpo: ConsultaEntrada, conn=Depends(get_conn), x_sesion: str | None = Header(None)):
    return service.crear(conn, cuerpo.pregunta, vectorizador=_vectorizador, llm=ClienteGemini(), sesion=x_sesion)


@router.get("", response_model=ConsultaLista)
def listar(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), conn=Depends(get_conn),
           x_sesion: str | None = Header(None)):
    return service.listar(conn, page, limit, sesion=x_sesion)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def borrar_historial(conn=Depends(get_conn), x_sesion: str | None = Header(None)):
    service.eliminar_historial(conn, x_sesion)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{consulta_id}", response_model=ConsultaSalida)
def obtener(consulta_id: int, conn=Depends(get_conn), x_sesion: str | None = Header(None)):
    return service.obtener(conn, consulta_id, sesion=x_sesion)


@router.patch("/{consulta_id}", response_model=ConsultaSalida)
def actualizar_feedback(consulta_id: int, cuerpo: ConsultaFeedback, conn=Depends(get_conn),
                        x_sesion: str | None = Header(None)):
    return service.actualizar_util(conn, consulta_id, cuerpo.util, sesion=x_sesion)


@router.delete("/{consulta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(consulta_id: int, conn=Depends(get_conn), x_sesion: str | None = Header(None)):
    service.eliminar(conn, consulta_id, sesion=x_sesion)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
