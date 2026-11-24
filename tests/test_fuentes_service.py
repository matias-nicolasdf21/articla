"""Pruebas de la capa de negocio con un repositorio falso en memoria (no necesitan base de datos).
Ejecutar:  python -m unittest discover -s tests -v
"""
import unittest

from app.errors import Conflicto, NoEncontrado, ReglaDeNegocio
from app.services import fuentes_service as service


class RepoFalso:
    def __init__(self):
        self.datos, self.sig = {}, 1

    def crear(self, conn, d):
        if any(f["identificador"] == d["identificador"] for f in self.datos.values()):
            raise Conflicto("duplicado")
        f = {"id": self.sig, **d}
        self.datos[self.sig] = f
        self.sig += 1
        return f

    def listar(self, conn, tipo, limit, offset, q=None):
        todas = [f for f in self.datos.values() if tipo is None or f["tipo"] == tipo]
        return todas[offset:offset + limit], len(todas)

    def obtener(self, conn, i):
        return self.datos.get(i)

    def reemplazar(self, conn, i, d):
        if i not in self.datos:
            return None
        self.datos[i] = {"id": i, **d}
        return self.datos[i]

    def eliminar(self, conn, i):
        return self.datos.pop(i, None) is not None


def ley(**kw):
    base = {"tipo": "ley", "identificador": " Ley 18.101 ", "titulo": "Arrendamiento"}
    return {**base, **kw}


class PruebasFuentes(unittest.TestCase):
    def setUp(self):
        self.repo = RepoFalso()

    def test_crear_normaliza_y_pone_licencia_por_defecto(self):
        f = service.crear(None, ley(), self.repo)
        self.assertEqual(f["identificador"], "Ley 18.101")
        self.assertEqual(f["licencia"], "dominio publico")

    def test_libro_sin_licencia_se_rechaza(self):
        with self.assertRaises(ReglaDeNegocio):
            service.crear(None, ley(tipo="libro"), self.repo)

    def test_libro_con_licencia_se_acepta(self):
        f = service.crear(None, ley(tipo="libro", licencia="autorizacion escrita del autor"), self.repo)
        self.assertEqual(f["licencia"], "autorizacion escrita del autor")

    def test_identificador_duplicado_da_conflicto(self):
        service.crear(None, ley(), self.repo)
        with self.assertRaises(Conflicto):
            service.crear(None, ley(), self.repo)

    def test_obtener_inexistente_da_no_encontrado(self):
        with self.assertRaises(NoEncontrado):
            service.obtener(None, 99, self.repo)

    def test_reemplazar_y_eliminar_inexistente(self):
        with self.assertRaises(NoEncontrado):
            service.reemplazar(None, 99, ley(), self.repo)
        with self.assertRaises(NoEncontrado):
            service.eliminar(None, 99, self.repo)

    def test_listar_pagina_y_filtra(self):
        for n in range(3):
            service.crear(None, ley(identificador=f"Ley {n}"), self.repo)
        service.crear(None, ley(tipo="codigo", identificador="CC"), self.repo)
        r = service.listar(None, "ley", 1, 2, self.repo)
        self.assertEqual((len(r["items"]), r["total"]), (2, 3))

    def test_listar_tipo_invalido(self):
        with self.assertRaises(ReglaDeNegocio):
            service.listar(None, "otro", 1, 10, self.repo)


if __name__ == "__main__":
    unittest.main()
