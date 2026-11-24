"""Pruebas del lector de LeyChile con los XML oficiales incluidos en data/leychile/ (no usan base de datos).
Ejecutar:  python -m unittest discover -s tests -v
"""
import unittest
from pathlib import Path

from app.ingesta.leychile import leer_norma

DATOS = Path(__file__).resolve().parent.parent / "data" / "leychile"


class CodigoCivil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.norma = leer_norma(DATOS / "codigo_civil.xml", parte_raiz="2")
        cls.por_etiqueta = {a.articulo: a for a in cls.norma.articulos}

    def test_identifica_la_norma(self):
        self.assertEqual(self.norma.id_norma, "172986")

    def test_articulo_1545_es_el_texto_oficial_citado_en_el_prototipo(self):
        a = self.por_etiqueta["art. 1545"]
        self.assertIn("Todo contrato legalmente celebrado es una ley para los contratantes", a.texto)
        self.assertIn("Título XII", a.ubicacion)
        self.assertIn("LIBRO CUARTO", a.ubicacion)

    def test_solo_el_codigo_y_no_las_otras_leyes_del_decreto(self):
        self.assertGreater(len(self.norma.articulos), 2400)
        self.assertLess(len(self.norma.articulos), 2700)
        self.assertNotIn("Déjase sin efecto el D.F.L.", self.por_etiqueta["art. 1"].texto)

    def test_etiquetas_unicas_y_dentro_del_largo_de_la_columna(self):
        self.assertEqual(len(self.por_etiqueta), len(self.norma.articulos))
        self.assertTrue(all(len(a.articulo) <= 100 for a in self.norma.articulos))

    def test_no_incluye_articulos_derogados(self):
        self.assertGreater(self.norma.derogados_omitidos, 0)
        import re
        solo_marca = [a.articulo for a in self.norma.articulos
                      if re.match(r"Art(?:ículo|\.)\s+\S+\s*[-–]?\s*Derogado", a.texto)]
        self.assertEqual(solo_marca, [])
        for derogado in ("art. 29", "art. 105", "art. 1273"):
            self.assertNotIn(derogado, self.por_etiqueta)
        self.assertIn("art. 1005", self.por_etiqueta)      # tiene un numeral derogado, pero el artículo rige

    def test_une_las_lineas_cortadas_del_xml(self):
        self.assertNotIn("\n ", self.por_etiqueta["art. 1545"].texto)
        self.assertEqual(self.por_etiqueta["art. 1545"].texto.count("\n"), 0)


class Ley18101(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.norma = leer_norma(DATOS / "ley_18101.xml")
        cls.por_etiqueta = {a.articulo: a for a in cls.norma.articulos}

    def test_identifica_la_norma(self):
        self.assertEqual(self.norma.id_norma, "29526")

    def test_articulo_1_es_el_texto_oficial_citado_en_el_prototipo(self):
        t = self.por_etiqueta["art. 1"].texto
        self.assertIn("se regirá por las disposiciones especiales de esta ley y, en lo no previsto en ella, "
                      "por el Código Civil", t)

    def test_el_articulo_transitorio_no_choca_con_el_articulo_1(self):
        self.assertIn("art. 1 transitorio", self.por_etiqueta)
        self.assertNotEqual(self.por_etiqueta["art. 1"].texto, self.por_etiqueta["art. 1 transitorio"].texto)

    def test_tiene_fecha_de_version(self):
        self.assertIsNotNone(self.por_etiqueta["art. 1"].fecha_version)


if __name__ == "__main__":
    unittest.main()


class CasosEspeciales(unittest.TestCase):
    """XML mínimos armados a mano con los casos raros vistos en otros códigos."""

    XML = """<?xml version="1.0" encoding="UTF-8"?>
<Norma xmlns="http://www.leychile.cl/esquemas" normaId="1">
 <Metadatos><TituloNorma>PRUEBA</TituloNorma></Metadatos>
 <EstructurasFuncionales>
  <EstructuraFuncional tipoParte="Artículo" transitorio="no transitorio" derogado="no derogado" idParte="1" fechaVersion="2000-01-01">
   <Texto>Que aprueba el Código. Por cuanto el Congreso ha dado su aprobación.</Texto>
   <Metadatos><NombreParte presente="no"> </NombreParte><TituloParte presente="no"> </TituloParte></Metadatos>
  </EstructuraFuncional>
  <EstructuraFuncional tipoParte="Artículo" transitorio="no transitorio" derogado="no derogado" idParte="2" fechaVersion="2000-01-01">
   <Texto>Artículo 1º.- Texto del uno.</Texto>
   <Metadatos><NombreParte presente="si">1</NombreParte></Metadatos>
  </EstructuraFuncional>
  <EstructuraFuncional tipoParte="Artículo" transitorio="transitorio" derogado="no derogado" idParte="3" fechaVersion="2000-01-01">
   <Texto>Artículo transitorio.- Reglas transitorias.</Texto>
   <Metadatos><NombreParte presente="si">transitorio</NombreParte></Metadatos>
  </EstructuraFuncional>
 </EstructurasFuncionales>
</Norma>"""

    def test_omite_texto_sin_numero_y_no_duplica_la_palabra_transitorio(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "x.xml"
            ruta.write_text(self.XML, encoding="utf-8")
            n = leer_norma(ruta)
        self.assertEqual([a.articulo for a in n.articulos], ["art. 1", "art. transitorio"])
        self.assertEqual(n.derogados_omitidos, 1)


class CargaALaBase(unittest.TestCase):
    """El cargador, con una conexión falsa: comprueba qué SQL se ejecuta y con qué datos."""

    def test_carga_la_fuente_reemplaza_fragmentos_y_los_inserta(self):
        from scripts.cargar_leychile import NORMAS, cargar

        class Cur:
            def __init__(self, reg): self.reg = reg
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def executemany(self, sql, filas): self.reg.append(("many", sql, list(filas)))

        class Conn:
            def __init__(self): self.reg = []
            def execute(self, sql, params=None):
                self.reg.append(("execute", sql, params))
                class R:
                    def fetchone(_): return {"id": 7}
                return R()
            def cursor(self): return Cur(self.reg)

        cfg = NORMAS[1]
        norma = leer_norma(DATOS / "ley_18101.xml")
        conn = Conn()
        self.assertEqual(cargar(conn, cfg, norma), 7)
        tipos = [r[0] for r in conn.reg]
        self.assertEqual(tipos, ["execute", "execute", "many"])                  # upsert, delete, insert
        self.assertIn("ON CONFLICT (identificador)", conn.reg[0][1])
        self.assertIn("DELETE FROM fragmentos", conn.reg[1][1])
        filas = conn.reg[2][2]
        self.assertEqual(len(filas), len(norma.articulos))
        self.assertEqual(filas[0][0], 7)
        self.assertEqual(conn.reg[0][2]["url"], "https://www.bcn.cl/leychile/navegar?idNorma=29526")


class LeyesRefundidasEnElDFL1(unittest.TestCase):
    """El DFL 1 de 2000 trae, además del Código Civil, el texto refundido de otras leyes (artículos 3 a 8)."""
    def test_ley_14908_de_pensiones_de_alimentos(self):
        n = leer_norma(DATOS / "codigo_civil.xml", "7")
        arts = {a.articulo: a.texto for a in n.articulos}
        self.assertGreater(len(arts), 40)
        self.assertIn("alimentos", arts["art. 14"])
        self.assertIn("retención", arts["art. 8"])

    def test_cada_parte_es_independiente(self):
        self.assertNotEqual(len(leer_norma(DATOS / "codigo_civil.xml", "2").articulos), len(leer_norma(DATOS / "codigo_civil.xml", "6").articulos))
