from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FuenteEntrada(BaseModel):
    tipo: Literal["ley", "codigo", "libro"]
    identificador: str = Field(min_length=1, max_length=100)
    titulo: str = Field(min_length=1, max_length=300)
    url_oficial: str | None = None
    licencia: str | None = Field(default=None, max_length=60)


class FuenteSalida(BaseModel):
    id: int
    tipo: str
    identificador: str
    titulo: str
    url_oficial: str | None
    licencia: str
    creada_en: datetime
    articulos: int = 0                 # cantidad de artículos cargados de esta fuente


class FuenteLista(BaseModel):
    items: list[FuenteSalida]
    total: int
    page: int
    limit: int
