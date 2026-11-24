from datetime import date

from pydantic import BaseModel


class FragmentoSalida(BaseModel):
    id: int
    fuente_id: int
    fuente: str                  # identificador de la fuente, p. ej. 'Codigo Civil'
    fuente_titulo: str | None = None
    url_oficial: str | None = None
    articulo: str | None
    texto: str
    ubicacion: str | None
    fecha_version: date | None


class FragmentoLista(BaseModel):
    items: list[FragmentoSalida]
    total: int
    page: int
    limit: int
