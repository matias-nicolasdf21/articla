"""Errores del dominio. No dependen de FastAPI: main.py los traduce a respuestas HTTP."""


class ErrorDeAplicacion(Exception):
    status = 400
    codigo = "ERROR"

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(ErrorDeAplicacion):
    status = 404
    codigo = "NO_ENCONTRADO"


class Conflicto(ErrorDeAplicacion):
    status = 409
    codigo = "CONFLICTO"


class ReglaDeNegocio(ErrorDeAplicacion):
    status = 422
    codigo = "REGLA_DE_NEGOCIO"
