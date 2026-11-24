from datetime import datetime

from pydantic import BaseModel, Field


class ConsultaEntrada(BaseModel):
    pregunta: str = Field(min_length=1, max_length=1000)


class ConsultaFeedback(BaseModel):
    util: bool | None            # obligatorio en el cuerpo: true, false o null (quitar el feedback)


class CitaSalida(BaseModel):
    fragmento_id: int
    fuente: str
    articulo: str | None


class ConsultaSalida(BaseModel):
    id: int
    pregunta: str
    respuesta: str | None
    citas: list[CitaSalida]
    util: bool | None
    modo: str | None = None            # 'ia' (redactada por el modelo) o 'extractiva' (respaldo)
    duracion_ms: int | None = None     # tiempo que tomó responder
    alerta: str | None = None          # teléfonos de ayuda si la pregunta sugiere riesgo (no se guarda)
    creada_en: datetime


class ConsultaLista(BaseModel):
    items: list[ConsultaSalida]
    total: int
    page: int
    limit: int
