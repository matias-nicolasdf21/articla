"""Pruebas de la capa de negocio de `consultas` y `fragmentos` con repositorios falsos en memoria.
Ejecutar:  python -m unittest discover -s tests -v
"""
import unittest

from app.errors import NoEncontrado, ReglaDeNegocio
from app.services import consultas_service as service
from app.services import fragmentos_service


class RepoConsultasFalso:
    def __init__(self):
        self.datos, self.sig = {}, 1

    def crear(self, conn, pregunta, respuesta, fragmento_ids, sesion=None, modo="extractiva", duracion_ms=None,
              reutilizable=False):
        c = {"id": self.sig, "pregunta": pregunta, "respuesta": respuesta, "util": None, "sesion": sesion,
             "modo": modo, "duracion_ms": duracion_ms, "reutilizable": reutilizable,
             "citas": [{"fragmento_id": i, "fuente": "Codigo Civil", "articulo": f"art. {i}"} for i in fragmento_ids]}
        self.datos[self.sig] = c
        self.sig += 1
        return c

    def _visible(self, c, sesion):
        return c is not None and (sesion is None or c["sesion"] == sesion)

    def listar(self, conn, limit, offset, sesion=None):
        todas = [c for c in self.datos.values() if self._visible(c, sesion)]
        return todas[offset:offset + limit], len(todas)

    def obtener(self, conn, i, sesion=None):
        c = self.datos.get(i)
        return c if self._visible(c, sesion) else None

    def actualizar_util(self, conn, i, util, sesion=None):
        c = self.obtener(conn, i, sesion)
        if c is None:
            return None
        c["util"] = util
        if util is False:      # igual que el repositorio real: invalida el caché de esa pregunta
            clave = " ".join(c["pregunta"].lower().strip("¿?¡! ").split())
            for otra in self.datos.values():
                if " ".join(otra["pregunta"].lower().strip("¿?¡! ").split()) == clave:
                    otra["reutilizable"] = False
        return c

    def eliminar(self, conn, i, sesion=None):
        if self.obtener(conn, i, sesion) is None:
            return False
        del self.datos[i]
        return True

    def eliminar_de_sesion(self, conn, sesion):
        ids = [i for i, c in self.datos.items() if c["sesion"] == sesion]
        for i in ids:
            del self.datos[i]
        return len(ids)


class RepoFragmentosFalso:
    def __init__(self, resultados=None):
        self.resultados = resultados or []
        self.ultima_busqueda = None

    def buscar(self, conn, tsquery, limite):
        self.ultima_busqueda = (tsquery, limite)
        return self.resultados[:limite]

    def buscar_semantico(self, conn, vector, limite):
        self.ultimo_vector = vector
        return list(reversed(self.resultados))[:limite]

    def obtener(self, conn, i):
        return next((f for f in self.resultados if f["id"] == i), None)

    def listar_por_fuente(self, conn, fuente_id, limit, offset):
        return self.resultados[offset:offset + limit], len(self.resultados)


def frag(i, texto="Art. 1545. Todo contrato legalmente celebrado es una ley para los contratantes."):
    return {"id": i, "fuente_id": 1, "fuente": "Codigo Civil", "articulo": f"art. {i}", "texto": texto}


class PruebasConsultas(unittest.TestCase):
    def setUp(self):
        self.repo = RepoConsultasFalso()
        self.frags = RepoFragmentosFalso([frag(1545), frag(1928), frag(1956), frag(1959)])

    def crear(self, pregunta="¿Mi arrendador puede subirme el arriendo?"):
        return service.crear(None, pregunta, self.repo, self.frags)

    def test_crear_guarda_la_pregunta_normalizada_y_hasta_tres_citas(self):
        c = self.crear("  ¿Mi arrendador puede subirme el arriendo?  ")
        self.assertEqual(c["pregunta"], "¿Mi arrendador puede subirme el arriendo?")
        self.assertEqual(len(c["citas"]), 3)
        self.assertIn("Codigo Civil, art. 1545", c["respuesta"])

    def test_sin_modelo_la_respuesta_es_extractiva_con_aviso(self):
        c = self.crear()
        self.assertEqual(c["modo"], "extractiva")
        self.assertIn("no reemplaza", c["respuesta"])
        self.assertIsInstance(c["duracion_ms"], int)

    def test_pregunta_muy_corta_o_vacia_da_regla_de_negocio(self):
        for p in ("", "   ", "hola"):
            with self.assertRaises(ReglaDeNegocio):
                self.crear(p)

    def test_pregunta_muy_larga_da_regla_de_negocio(self):
        with self.assertRaises(ReglaDeNegocio):
            self.crear("a" * 1001)

    def test_sin_resultados_no_inventa_citas(self):
        sin = RepoFragmentosFalso([])
        c = service.crear(None, "¿Qué dice la ley sobre dragones?", self.repo, sin)
        self.assertEqual(c["citas"], [])
        self.assertIn("No encontré artículos", c["respuesta"])

    def test_pregunta_solo_con_palabras_cortas_no_busca(self):
        sin = RepoFragmentosFalso([frag(1)])
        c = service.crear(None, "¿y yo que se?", self.repo, sin)
        self.assertIsNone(sin.ultima_busqueda)
        self.assertEqual(c["citas"], [])

    def test_terminos_de_busqueda_solo_letras_y_sin_repetidos(self):
        t = service.terminos_de_busqueda("Arriendo; DROP TABLE arriendo -- ¿contrato? 12345 | & ' !")
        self.assertEqual(t, "arriendo | drop | table | contrato")

    def test_obtener_inexistente(self):
        with self.assertRaises(NoEncontrado):
            service.obtener(None, 99, self.repo)

    def test_feedback_util_y_quitarlo(self):
        c = self.crear()
        self.assertTrue(service.actualizar_util(None, c["id"], True, self.repo)["util"])
        self.assertIsNone(service.actualizar_util(None, c["id"], None, self.repo)["util"])

    def test_feedback_y_eliminar_inexistente(self):
        with self.assertRaises(NoEncontrado):
            service.actualizar_util(None, 99, True, self.repo)
        with self.assertRaises(NoEncontrado):
            service.eliminar(None, 99, self.repo)

    def test_listar_pagina(self):
        for _ in range(3):
            self.crear()
        r = service.listar(None, 2, 2, self.repo)
        self.assertEqual((len(r["items"]), r["total"], r["page"]), (1, 3, 2))

    def test_eliminar(self):
        c = self.crear()
        service.eliminar(None, c["id"], self.repo)
        with self.assertRaises(NoEncontrado):
            service.obtener(None, c["id"], self.repo)


class VectorizadorFalso:
    def __init__(self, vector=(0.1, 0.2)): self.vector = list(vector) if vector else None
    def pregunta(self, texto): return self.vector


class LLMFalso:
    def __init__(self, salida, disponible=True):
        self.salida, self._disp, self.prompt = salida, disponible, None
    def disponible(self): return self._disp
    def redactar(self, prompt):
        self.prompt = prompt
        return self.salida


class PruebasRAG(unittest.TestCase):
    def setUp(self):
        self.repo = RepoConsultasFalso()
        self.frags = RepoFragmentosFalso([frag(1545), frag(1928), frag(1956), frag(1959)])

    def crear(self, llm=None, vect=None, sesion=None):
        return service.crear(None, "¿Mi arrendador puede subirme el arriendo?", self.repo, self.frags,
                             vectorizador=vect, llm=llm, sesion=sesion)

    def test_fusion_premia_lo_que_aparece_en_ambas_listas(self):
        a, b, c = frag(1), frag(2), frag(3)
        r = service.fusionar([a, b], [c, b], limite=3)
        self.assertEqual(r[0]["id"], 2)
        self.assertEqual(len(r), 3)

    def test_usa_las_dos_vias_de_busqueda(self):
        self.crear(vect=VectorizadorFalso())
        self.assertTrue(self.frags.ultimo_vector.startswith("["))
        self.assertIsNotNone(self.frags.ultima_busqueda)

    def test_con_modelo_redacta_y_cita_solo_codigos_existentes(self):
        llm = LLMFalso({"respuesta": "Lo pactado obliga a las partes [F1]. Algo inventado [F9].", "citas": ["F1", "F9"]})
        c = self.crear(llm=llm)
        self.assertEqual(c["modo"], "ia")
        self.assertEqual([x["fragmento_id"] for x in c["citas"]], [1545])
        self.assertIn("(Codigo Civil, art. 1545)", c["respuesta"])
        self.assertNotIn("[F", c["respuesta"])
        self.assertIn("[F1] Codigo Civil, art. 1545", llm.prompt)

    def test_los_pasos_se_agregan_numerados_con_sus_citas(self):
        llm = LLMFalso({"respuesta": "Te corresponde indemnización [F2].",
                        "pasos": ["1. Pide tu carta de despido [F2]", "Acude a la Inspección del Trabajo"], "citas": ["F2"]})
        c = self.crear(llm=llm)
        self.assertIn("Qué puedes hacer:\n1. Pide tu carta de despido (Codigo Civil, art. 1928)\n2. Acude", c["respuesta"])

    def test_formato_por_secciones_descarta_puntos_legales_sin_cita_valida(self):
        llm = LLMFalso({"resumen": "Puedes exigir la reparación.",
                        "ley": [{"texto": "El arrendador debe hacer las reparaciones", "cita": "F2"},
                                {"texto": "Algo inventado", "cita": "F9"}, {"texto": "Sin cita"}],
                        "pasos": ["1. Reúne tu contrato", "- Escribe al arrendador"],
                        "ten_en_cuenta": ["Guarda los comprobantes [F1]"], "sin_respuesta": False})
        c = self.crear(llm=llm)
        r = c["respuesta"]
        self.assertEqual(c["modo"], "ia")
        self.assertIn("Qué dice la ley:\n- El arrendador debe hacer las reparaciones (Codigo Civil, art. 1928)", r)
        self.assertNotIn("inventado", r)
        self.assertNotIn("Sin cita", r)
        self.assertIn("Qué puedes hacer:\n1. Reúne tu contrato\n2. Escribe al arrendador", r)
        self.assertIn("Ten en cuenta:\n- Guarda los comprobantes (Codigo Civil, art. 1545)", r)
        self.assertEqual([x["fragmento_id"] for x in c["citas"]], [1928, 1545])

    def test_sin_respuesta_declarado_se_acepta(self):
        llm = LLMFalso({"resumen": "Las leyes cargadas no tratan ese tema.", "ley": [], "pasos": ["Consulta a la CAJ"],
                        "sin_respuesta": True})
        c = self.crear(llm=llm)
        self.assertEqual((c["modo"], c["citas"]), ("ia", []))

    def test_formato_sin_puntos_validos_ni_declaracion_vuelve_a_extractiva(self):
        llm = LLMFalso({"resumen": "Sí puede.", "ley": [{"texto": "x", "cita": "F7"}], "pasos": ["a"]})
        self.assertEqual(self.crear(llm=llm)["modo"], "extractiva")

    def test_alerta_por_violencia_y_por_riesgo_vital(self):
        self.assertIn("133", service.alerta_para("Mi pareja me golpea, ¿qué hago?"))
        self.assertIn("1455", service.alerta_para("sufro violencia intrafamiliar"))
        self.assertIn("*4141", service.alerta_para("no quiero vivir más"))
        self.assertIsNone(service.alerta_para("¿Me pueden subir el arriendo?"))
        c = service.crear(None, "Mi expareja me amenaza por WhatsApp", self.repo, self.frags)
        self.assertIn("149", c["alerta"])

    def test_respuesta_del_modelo_sin_citas_validas_vuelve_a_extractiva(self):
        c = self.crear(llm=LLMFalso({"respuesta": "Sí puede, según el art. 99 [F9].", "citas": ["F9"]}))
        self.assertEqual(c["modo"], "extractiva")
        self.assertEqual(len(c["citas"]), 3)

    def test_modelo_que_falla_o_responde_basura_vuelve_a_extractiva(self):
        for salida in (None, "texto", {"respuesta": ""}, {"citas": ["F1"]}):
            self.assertEqual(self.crear(llm=LLMFalso(salida))["modo"], "extractiva")

    def test_reformulacion_agrega_terminos_juridicos_a_la_busqueda(self):
        llm = LLMFalso({"respuesta": "x [F1]", "citas": ["F1"]})
        llm.reformular = lambda p: {"terminos": "despido indemnizacion", "consulta": "termino del contrato"}
        self.crear(llm=llm)
        self.assertIn("despido", self.frags.ultima_busqueda[0])
        self.assertIn("indemnizacion", self.frags.ultima_busqueda[0])

    def test_leyes_nombradas_se_buscan_aparte_y_pesan_mas(self):
        llamadas = []
        self.frags.buscar_en_fuentes = lambda conn, ids, q, lim: (llamadas.append(ids), [frag(1959)])[1]
        self.frags.buscar_semantico_en_fuentes = lambda conn, ids, v, lim: [frag(1959)]
        llm = LLMFalso({"respuesta": "x [F1]", "citas": ["F1"]})
        llm.reformular = lambda p: {"leyes": ["Ley 14.908", "Código Civil"], "terminos": "alimentos"}
        c = self.crear(llm=llm, vect=VectorizadorFalso())
        self.assertEqual(llamadas[0], ["ley 14908", "codigo civil"])
        self.assertEqual(c["citas"][0]["fragmento_id"], 1959)

    def test_normalizar_nombres_de_normas(self):
        n = service.normalizar_ley
        self.assertEqual(n("Ley N° 14.908"), "ley 14908")
        self.assertEqual(n("Decreto Ley 3.500"), "dl 3500")
        self.assertEqual(n("DL 3.500"), "dl 3500")
        self.assertEqual(n("Código del Trabajo"), "codigo del trabajo")

    def test_cita_repetida_por_el_modelo_se_deja_una_sola_vez(self):
        llm = LLMFalso({"resumen": "Puedes pedir apremios.",
                        "ley": [{"texto": "El juez puede ordenar arresto (Codigo Civil, art. 1928).", "cita": "F2"}],
                        "pasos": ["Ve al tribunal"]})
        r = self.crear(llm=llm)["respuesta"]
        self.assertEqual(r.count("(Codigo Civil, art. 1928)"), 1)

    def test_etiqueta_con_numero_usa_el_identificador(self):
        f = {"fuente": "Ley 18.290", "fuente_titulo": "Ley De Transito", "articulo": "art. 185"}
        self.assertEqual(service._etiqueta(f), "Ley 18.290, art. 185")
        f = {"fuente": "DFL 1 (idNorma 1234)", "fuente_titulo": "Algo", "articulo": "art. 2"}
        self.assertEqual(service._etiqueta(f), "DFL 1, art. 2")

    def test_etiqueta_usa_el_numero_si_el_titulo_esta_en_mayusculas(self):
        f = {"fuente": "Ley 14.550", "fuente_titulo": "CREA LOS JUZGADOS DE LETRAS DE MENORES", "articulo": "art. 23"}
        self.assertEqual(service._etiqueta(f), "Ley 14.550, art. 23")

    def test_reformulacion_fallida_no_rompe_la_busqueda(self):
        llm = LLMFalso({"respuesta": "x [F1]", "citas": ["F1"]})
        llm.reformular = lambda p: None
        self.assertEqual(self.crear(llm=llm)["modo"], "ia")

    def test_modelo_sin_clave_no_se_llama(self):
        llm = LLMFalso({"respuesta": "x [F1]"}, disponible=False)
        self.assertEqual(self.crear(llm=llm)["modo"], "extractiva")
        self.assertIsNone(llm.prompt)

    def test_modelo_que_declara_no_encontrar_respuesta_se_acepta_sin_citas(self):
        c = self.crear(llm=LLMFalso({"respuesta": "Los artículos entregados no regulan ese caso.", "citas": []}))
        self.assertEqual((c["modo"], c["citas"]), ("ia", []))

    def test_sesion_invalida_es_regla_de_negocio(self):
        with self.assertRaises(ReglaDeNegocio):
            self.crear(sesion="hola mundo!")

    def test_historial_separado_por_sesion_y_borrado(self):
        s1, s2 = "sesion-aaaa-1111", "sesion-bbbb-2222"
        c1 = self.crear(sesion=s1)
        self.crear(sesion=s2)
        self.assertEqual(service.listar(None, 1, 10, self.repo, sesion=s1)["total"], 1)
        with self.assertRaises(NoEncontrado):
            service.obtener(None, c1["id"], self.repo, sesion=s2)
        self.assertEqual(service.eliminar_historial(None, s1, self.repo), 1)
        self.assertEqual(service.listar(None, 1, 10, self.repo)["total"], 1)

    def test_borrar_historial_sin_sesion_es_regla_de_negocio(self):
        with self.assertRaises(ReglaDeNegocio):
            service.eliminar_historial(None, None, self.repo)


class PruebasFragmentos(unittest.TestCase):
    class RepoFuentes:
        def __init__(self, existe=True): self.existe = existe
        def obtener(self, conn, i): return {"id": i} if self.existe else None

    def test_obtener_inexistente(self):
        with self.assertRaises(NoEncontrado):
            fragmentos_service.obtener(None, 9, RepoFragmentosFalso())

    def test_listar_de_fuente_inexistente(self):
        with self.assertRaises(NoEncontrado):
            fragmentos_service.listar_por_fuente(None, 9, 1, 10, RepoFragmentosFalso(), self.RepoFuentes(False))

    def test_listar_de_fuente_pagina(self):
        repo = RepoFragmentosFalso([frag(i) for i in range(5)])
        r = fragmentos_service.listar_por_fuente(None, 1, 2, 2, repo, self.RepoFuentes())
        self.assertEqual((len(r["items"]), r["total"]), (2, 5))


if __name__ == "__main__":
    unittest.main()


class RepoConCache(RepoConsultasFalso):
    """Repositorio falso que además recuerda respuestas redactadas con IA (caché de preguntas repetidas)."""
    def buscar_reciente(self, conn, pregunta, dias):
        clave = " ".join(pregunta.lower().strip("¿?¡! ").split())
        for c in reversed(list(self.datos.values())):
            if c["reutilizable"] and c["util"] is not False and " ".join(c["pregunta"].lower().strip("¿?¡! ").split()) == clave:
                return c
        return None


class PruebasCache(unittest.TestCase):
    def setUp(self):
        self.repo = RepoConCache()
        self.frags = RepoFragmentosFalso([frag(1545), frag(1928)])

    def test_pregunta_repetida_reutiliza_la_respuesta_sin_llamar_al_modelo(self):
        llm = LLMFalso({"respuesta": "Lo pactado obliga [F1].", "citas": ["F1"]})
        primera = service.crear(None, "¿Mi arrendador puede subirme el arriendo?", self.repo, self.frags, llm=llm,
                                sesion="sesion-aaaa1111")
        llm.salida = None          # si se llamara al modelo otra vez, la respuesta caería al modo extractivo
        segunda = service.crear(None, "mi arrendador puede subirme el arriendo", self.repo, self.frags, llm=llm,
                                sesion="sesion-bbbb2222")
        self.assertEqual(segunda["modo"], "ia")
        self.assertEqual(segunda["respuesta"], primera["respuesta"])
        self.assertEqual([c["fragmento_id"] for c in segunda["citas"]], [1545])
        self.assertEqual(segunda["sesion"], "sesion-bbbb2222")   # queda en el historial de quien preguntó

    def test_respuestas_extractivas_no_se_reutilizan(self):
        service.crear(None, "¿Mi arrendador puede subirme el arriendo?", self.repo, self.frags)
        llm = LLMFalso({"respuesta": "Lo pactado obliga [F1].", "citas": ["F1"]})
        c = service.crear(None, "¿Mi arrendador puede subirme el arriendo?", self.repo, self.frags, llm=llm)
        self.assertEqual(c["modo"], "ia")


class PruebasClienteGemini(unittest.TestCase):
    def test_prueba_las_formas_de_minimizar_el_razonamiento_y_recuerda_la_que_funciona(self):
        import json
        from app.ia.gemini import ClienteGemini
        ClienteGemini._variante_ok.clear()
        cliente = ClienteGemini(clave="x", modelo="modelo-a")
        cliente.VARIANTES = ClienteGemini.NIVELES["minimo"]
        cliente.nivel = "minimo"
        cuerpos = []

        def llamar(modelo, datos):
            cuerpos.append(json.loads(datos)["generationConfig"])
            return 400 if len(cuerpos) <= 2 else {"ok": True}
        cliente._llamar = lambda m, d, t=15: llamar(m, d)
        self.assertEqual(cliente.redactar("hola"), {"ok": True})
        self.assertEqual(cuerpos[0]["thinkingConfig"], {"thinkingLevel": "minimal"})
        self.assertEqual(cuerpos[1]["thinkingConfig"], {"thinkingBudget": 0})
        self.assertNotIn("thinkingConfig", cuerpos[2])
        self.assertEqual(cuerpos[0]["maxOutputTokens"], 1500)
        cuerpos.clear()
        cliente._llamar = lambda m, d, t=15: (cuerpos.append(json.loads(d)["generationConfig"]) or {"ok": True})
        cliente.redactar("otra")
        self.assertEqual(len(cuerpos), 1)               # recordó la forma que funcionó: sin rechazos nuevos
        self.assertNotIn("thinkingConfig", cuerpos[0])
        ClienteGemini._variante_ok.clear()

    def test_cuota_agotada_pasa_al_siguiente_modelo_y_lo_salta_despues(self):
        from app.ia.gemini import ClienteGemini
        ClienteGemini._variante_ok.clear()
        ClienteGemini._pausado_hasta.clear()
        cliente = ClienteGemini(clave="x", modelo="modelo-a,modelo-b")
        llamadas = []

        def llamar(modelo, datos):
            llamadas.append(modelo)
            return 429 if modelo == "modelo-a" else {"ok": True}
        cliente._llamar = lambda m, d, t=15: llamar(m, d)
        self.assertEqual(cliente.redactar("hola"), {"ok": True})
        self.assertEqual(llamadas, ["modelo-a", "modelo-b"])      # sin reintentar modelo-a
        llamadas.clear()
        cliente.redactar("otra")
        self.assertEqual(llamadas, ["modelo-b"])                   # modelo-a queda en pausa
        ClienteGemini._pausado_hasta.clear()
        ClienteGemini._variante_ok.clear()


class PruebasArticulosDirectos(unittest.TestCase):
    def test_normaliza_articulos_nombrados_por_el_modelo(self):
        self.assertEqual(service.normalizar_articulo("Código Civil art. 1545"), ("codigo civil", "art. 1545"))
        self.assertEqual(service.normalizar_articulo("Ley 18.101, artículo 3"), ("ley 18101", "art. 3"))
        self.assertEqual(service.normalizar_articulo("Ley 21.461 art. 2 transitorio"), ("ley 21461", "art. 2 transitorio"))
        self.assertEqual(service.normalizar_articulo("Codigo del Trabajo art. 161 bis"), ("codigo del trabajo", "art. 161 bis"))
        self.assertEqual(service.normalizar_articulo("Codigo del Trabajo art. 211-B"), ("codigo del trabajo", "art. 211-b"))
        self.assertEqual(service.normalizar_articulo("Ley 18.101 art. 3 a la fecha"), ("ley 18101", "art. 3"))
        self.assertEqual(service.normalizar_articulo("Ley 21.643 art. 1 bis"), ("ley 21643", "art. 1 bis"))
        self.assertIsNone(service.normalizar_articulo("el contrato de arriendo"))

    def test_articulos_nombrados_encabezan_y_transitorios_van_al_final(self):
        class Repo(RepoFragmentosFalso):
            def buscar_articulos(self, conn, pares):
                self.pares = pares
                return [frag(1545)]
        transitorio = {**frag(2), "articulo": "art. 2 transitorio"}
        repo = Repo([transitorio, frag(1928)])
        llm = LLMFalso(None)
        llm.reformular = lambda p: {"articulos": ["Codigo Civil art. 1545"], "terminos": "renta arriendo"}
        r = service.recuperar(None, "¿Me pueden subir el arriendo?", repo, None, llm)
        self.assertEqual(repo.pares, [("codigo civil", "art. 1545")])
        self.assertEqual(r[0]["id"], 1545)
        self.assertEqual(r[-1]["articulo"], "art. 2 transitorio")

    def test_respuesta_marcada_como_no_util_no_se_reutiliza(self):
        repo = RepoConCache()
        frags = RepoFragmentosFalso([frag(1545)])
        llm = LLMFalso({"respuesta": "Lo pactado obliga [F1].", "citas": ["F1"]})
        c = service.crear(None, "¿Mi arrendador puede subirme el arriendo?", repo, frags, llm=llm)
        service.actualizar_util(None, c["id"], False, repo)
        llm.salida = None
        otra = service.crear(None, "¿Mi arrendador puede subirme el arriendo?", repo, frags, llm=llm)
        self.assertEqual(otra["modo"], "extractiva")


class PruebasCacheCopias(unittest.TestCase):
    def test_marcar_no_en_una_copia_del_cache_invalida_la_original(self):
        repo = RepoConCache()
        frags = RepoFragmentosFalso([frag(1545)])
        llm = LLMFalso({"respuesta": "Lo pactado obliga [F1].", "citas": ["F1"]})
        service.crear(None, "¿Mi arrendador puede subirme el arriendo?", repo, frags, llm=llm)
        copia = service.crear(None, "¿Mi arrendador puede subirme el arriendo?", repo, frags, llm=llm)
        service.actualizar_util(None, copia["id"], False, repo)
        llm.salida = None
        nueva = service.crear(None, "¿Mi arrendador puede subirme el arriendo?", repo, frags, llm=llm)
        self.assertEqual(nueva["modo"], "extractiva")   # ya no salió del caché


class PruebasLimpieza(unittest.TestCase):
    def test_quita_citas_repetidas_en_la_misma_linea(self):
        linea = ("- Debe investigar (Código del Trabajo, art. 211 C), con reserva (Código del Trabajo, art. 211 B). "
                 "(Código del Trabajo, art. 211 C)")
        self.assertEqual(service._sin_citas_repetidas(linea),
                         "- Debe investigar (Código del Trabajo, art. 211 C), con reserva (Código del Trabajo, art. 211 B).")

    def test_no_toca_lineas_sin_repeticion(self):
        linea = "- Lo pactado obliga (Código Civil, art. 1545)."
        self.assertEqual(service._sin_citas_repetidas(linea), linea)
