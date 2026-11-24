"""Cliente mínimo del modelo de lenguaje Gemini (Google) por su API REST.

- La clave se lee de GEMINI_API_KEY (archivo .env, nunca en el código).
- El modelo se elige con GEMINI_MODEL (por defecto 'gemini-flash-latest'); se pueden poner varios separados por coma.
  Si un modelo está saturado (503/429/500), se reintenta una vez y luego se prueba el siguiente; siempre se
  agrega 'gemini-flash-lite-latest' como último respaldo.
- Se minimiza el "razonamiento" interno del modelo (thinkingLevel 'minimal' o thinkingBudget 0) y se limita la salida:
  con razonamiento activo una respuesta tardaba 20-30 s y a veces se pasaba del plazo; sin él tarda pocos
  segundos. Si un modelo no acepta esa opción (HTTP 400), se repite la llamada sin ella.
- Solo se envía la pregunta y los artículos recuperados: ningún dato de identidad.
Si no hay clave o la llamada falla, `redactar` devuelve None y la capa de negocio usa la respuesta extractiva.
"""
import json
import time
import urllib.error
import urllib.request

from app.config import gemini_api_key, gemini_modelo, gemini_pensamiento

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
TIMEOUT_S = 15          # por intento al redactar
TIMEOUT_BUSQUEDA_S = 8  # por intento al reformular: suele tardar 2 s; si se cuelga, conviene reintentar
PLAZO_TOTAL_S = 25      # por llamada (se hacen dos: buscar y redactar), para quedar bajo el minuto
RESPALDO = "gemini-flash-lite-latest"
REINTENTABLES = {500, 503, 504}
PAUSA_CUOTA_S = 600     # tras un HTTP 429 (cuota agotada) el modelo se salta por 10 minutos

INSTRUCCIONES = """Eres Articla, un asistente de orientación legal para personas en Chile.
Reglas obligatorias:
1. Todo lo que digas sobre derechos, obligaciones, plazos, montos o sanciones debe salir SOLO de los artículos
   entregados, cada uno identificado con un código como [F1]. Ignora los artículos que no tengan relación.
2. Nunca inventes artículos, números de ley, plazos ni montos que no estén en el texto entregado.
3. Escribe en español de Chile, en lenguaje simple y cercano, para alguien sin formación legal. Tutea.
4. Sé útil y concreto: explica qué derechos tiene la persona, qué puede pedir y cómo hacerlo.
5. Los pasos prácticos pueden incluir a qué institución acudir (por ejemplo: Tribunal de Familia, Juzgado de
   Policía Local, Inspección del Trabajo, SERNAC, Corporación de Asistencia Judicial, Fiscalía o Carabineros),
   qué documentos reunir y qué pedir. Esos pasos generales no necesitan código.
6. Si los artículos no responden la pregunta, dilo con honestidad en "resumen", deja "ley" vacío,
   pon "sin_respuesta": true y sugiere acudir a una Corporación de Asistencia Judicial o a un abogado.
7. No pidas datos personales.
8. Prefiere los artículos permanentes y generales que responden la duda de hoy. Los artículos "transitorios"
   suelen regular situaciones antiguas: úsalos solo si es evidente que aún se aplican.
Devuelve solo JSON con esta forma (máximo 300 palabras en total):
{"resumen": "respuesta directa de 1 a 3 frases",
 "ley": [{"texto": "lo que establece la ley, explicado en simple", "cita": "F2"}],
 "pasos": ["paso concreto 1", "paso concreto 2", "paso concreto 3"],
 "ten_en_cuenta": ["plazo, requisito o excepción importante, con su código [F3] si viene de un artículo"],
 "sin_respuesta": false}
"ley": de 2 a 4 puntos, cada uno con su código. "pasos": de 3 a 5. "ten_en_cuenta": de 0 a 3."""

INSTRUCCIONES_BUSQUEDA = """Eres un experto en derecho chileno. Recibes una duda legal escrita por una persona común.
Indica qué normas chilenas VIGENTES la regulan y qué términos jurídicos aparecerían en sus artículos.
Devuelve solo JSON:
{"leyes": ["hasta 4 normas, escritas como 'Ley 14.908', 'Ley 20.066', 'DL 3.500', 'Codigo Civil', 'Codigo del Trabajo'"],
 "articulos": ["hasta 6 artículos permanentes que responden directamente la duda, como 'Codigo Civil art. 1545' o 'Codigo del Trabajo art. 67'"],
 "terminos": "8 a 15 palabras clave jurídicas en español, separadas por espacios",
 "consulta": "la duda reescrita en una frase con lenguaje jurídico"}
Nombra solo artículos de los que estés seguro; prefiere los permanentes a los transitorios. Si una ley modificó un código o una ley anterior (por ejemplo, la Ley Karin modificó el Código del Trabajo), nombra el artículo vigente de ese código, como 'Codigo del Trabajo art. 211-B', y no la ley que lo modificó. Usa el número de ley con puntos. Para decretos ley escribe 'DL' y el número; prefiere siempre la norma vigente. Para los códigos usa su nombre sin tildes; para la Constitución escribe 'Constitucion Politica'."""


class ClienteGemini:
    def __init__(self, clave: str | None = None, modelo: str | None = None):
        self.clave = clave if clave is not None else gemini_api_key()
        lista = [m.strip() for m in (modelo or gemini_modelo()).split(",") if m.strip()]
        self.modelos = lista + ([RESPALDO] if RESPALDO not in lista else [])
        self.nivel = gemini_pensamiento()
        self.VARIANTES = self.NIVELES[self.nivel]

    def disponible(self) -> bool:
        return bool(self.clave)

    def redactar(self, prompt: str) -> dict | None:
        """Redacta la respuesta en lenguaje simple con los artículos entregados."""
        return self._generar(INSTRUCCIONES, prompt, temperatura=0.2, modelos=self.modelos, max_tokens=1500)

    def reformular(self, pregunta: str) -> dict | None:
        """Traduce la duda a términos jurídicos para buscar mejor (no se muestra al usuario)."""
        # Tarea simple: se usa primero el modelo liviano, que es más rápido y suele estar menos saturado.
        orden = [RESPALDO] + [m for m in self.modelos if m != RESPALDO]
        return self._generar(INSTRUCCIONES_BUSQUEDA, pregunta, temperatura=0.0, modelos=orden, max_tokens=700,
                             timeout=TIMEOUT_BUSQUEDA_S)

    # Formas de pedir "sin razonamiento", de la más nueva a la más antigua. Los modelos Gemini 3 piensan
    # "alto" por defecto (lento, y ese pensamiento consume el límite de salida); aceptan thinkingLevel
    # 'minimal'. Los 2.5 usan thinkingBudget 0. Si un modelo rechaza una forma (HTTP 400), se prueba la
    # siguiente y se recuerda la que funcionó para no repetir el rechazo en cada pregunta.
    NIVELES = {
        "minimo": ({"thinkingLevel": "minimal"}, {"thinkingBudget": 0}, None),
        "bajo": ({"thinkingLevel": "low"}, {"thinkingBudget": 1024}, None),
        "alto": (None,),
    }
    VARIANTES = NIVELES["minimo"]
    _variante_ok: dict[tuple, int] = {}
    _pausado_hasta: dict[str, float] = {}

    @staticmethod
    def _cuerpo(instrucciones: str, prompt: str, temperatura: float, max_tokens: int, pensamiento) -> bytes:
        config = {"temperature": temperatura, "responseMimeType": "application/json", "maxOutputTokens": max_tokens}
        if pensamiento:
            config["thinkingConfig"] = pensamiento
        return json.dumps({
            "systemInstruction": {"parts": [{"text": instrucciones}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": config,
        }).encode("utf-8")

    def _generar(self, instrucciones: str, prompt: str, temperatura: float, modelos: list[str],
                 max_tokens: int = 1500, timeout: float = TIMEOUT_S) -> dict | None:
        if not self.clave:
            return None
        inicio = time.monotonic()
        for i, modelo in enumerate(modelos):
            ultimo = i == len(modelos) - 1
            if not ultimo and time.monotonic() < self._pausado_hasta.get(modelo, 0):
                continue                   # cuota agotada hace poco: no perder tiempo con este modelo
            v = self._variante_ok.get((modelo, self.nivel), 0)
            intento = 0
            while intento < 2:
                if time.monotonic() - inicio > PLAZO_TOTAL_S:
                    print("[gemini] se agotó el plazo total")
                    return None
                t0 = time.monotonic()
                datos_json = self._cuerpo(instrucciones, prompt, temperatura, max_tokens, self.VARIANTES[v])
                codigo = self._llamar(modelo, datos_json, timeout)
                if isinstance(codigo, dict):
                    self._variante_ok[(modelo, self.nivel)] = v
                    print(f"[gemini] {modelo} ok en {time.monotonic() - t0:.1f} s (pensamiento: {self.VARIANTES[v]})")
                    return codigo
                if codigo == 400 and v < len(self.VARIANTES) - 1:
                    v += 1                 # el modelo no acepta esta forma: probar la siguiente, sin gastar intento
                    self._variante_ok[(modelo, self.nivel)] = v   # y no volver a pedirle la forma rechazada
                    continue
                if codigo == 429:
                    # Cuota agotada: reintentar al tiro no sirve. Se pasa al siguiente modelo y este se salta un rato.
                    self._pausado_hasta[modelo] = time.monotonic() + PAUSA_CUOTA_S
                    break
                if codigo not in REINTENTABLES and codigo != 0:
                    break                  # error no recuperable con este modelo: probar el siguiente
                if intento == 0:
                    time.sleep(1.0)        # saturación momentánea: esperar y reintentar una vez
                intento += 1
        return None

    def _llamar(self, modelo: str, datos_json: bytes, timeout: float = TIMEOUT_S):
        """Devuelve el JSON generado, o el código de error HTTP (0 si no hubo respuesta)."""
        req = urllib.request.Request(
            URL.format(modelo=modelo), data=datos_json, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.clave},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                datos = json.loads(r.read().decode("utf-8"))
            texto = datos["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(texto)
        except urllib.error.HTTPError as e:
            print(f"[gemini] {modelo}: HTTP {e.code}: {e.read()[:200]!r}")
            return e.code
        except Exception as e:   # sin red, tiempo agotado, respuesta vacía o JSON inválido
            print(f"[gemini] {modelo}: error: {e}")
            return 0
