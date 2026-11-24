# Articla · Tabla de la API REST (versión final)

**Base:** `/api/v1` · **Formato:** JSON · **Errores:** siempre con el cuerpo

```json
{ "error": { "codigo": "NO_ENCONTRADO", "mensaje": "La fuente 99 no existe." } }
```

Los errores de validación los devuelve FastAPI con **422**. Un error nunca se responde con 200.

## Recurso 1: `fuentes` (leyes, códigos y libros del corpus)

| Verbo | Ruta | Parámetros | Cuerpo de ejemplo | Éxito | Errores |
|---|---|---|---|---|---|
| POST | `/fuentes` | — | `{"tipo":"ley","identificador":"Ley 18.101","titulo":"Arrendamiento de predios urbanos","url_oficial":"https://www.bcn.cl/leychile"}` | **201** + fuente creada | 409 identificador duplicado · 422 datos inválidos |
| GET | `/fuentes` | `tipo`, `page`, `limit` (query) | — | **200** lista paginada | 422 parámetro inválido |
| GET | `/fuentes/{id}` | `id` (ruta) | — | **200** | 404 no existe |
| PUT | `/fuentes/{id}` | `id` (ruta) | igual que POST | **200** fuente actualizada | 404 · 409 · 422 |
| DELETE | `/fuentes/{id}` | `id` (ruta) | — | **204** sin cuerpo (borra sus fragmentos en cascada) | 404 |

**Regla de negocio de `fuentes`:** `licencia` es opcional y vale `dominio publico` por defecto, pero un `libro` **debe declarar su licencia** (puede tener derechos de autor); si no, responde **422** con código `REGLA_DE_NEGOCIO`.

## Sub-recurso: `fragmentos` (artículos del corpus, solo lectura)

Los artículos se cargan desde el XML oficial de LeyChile con `scripts/cargar_leychile.py`, por eso no hay POST.

| Verbo | Ruta | Parámetros | Éxito | Errores |
|---|---|---|---|---|
| GET | `/fuentes/{id}/fragmentos` | `id` (ruta), `page`, `limit` (query) | **200** lista paginada de artículos de esa fuente | 404 la fuente no existe · 422 |
| GET | `/fragmentos/{id}` | `id` (ruta) | **200** artículo con su texto oficial, ubicación y fecha de versión | 404 |

## Recurso 2: `consultas` (pregunta del usuario y respuesta con citas)

| Verbo | Ruta | Parámetros | Cuerpo de ejemplo | Éxito | Errores |
|---|---|---|---|---|---|
| POST | `/consultas` | — | `{"pregunta":"¿Mi arrendador puede subirme el arriendo a mitad de contrato?"}` | **201** + consulta con `respuesta` y `citas` | 422 pregunta de menos de 5 o más de 1000 caracteres · 503 si la base no responde |
| GET | `/consultas` | `page`, `limit` | — | **200** historial paginado | 422 |
| GET | `/consultas/{id}` | `id` | — | **200** con citas | 404 |
| PATCH | `/consultas/{id}` | `id` | `{"util": true}` (también `false` o `null`) | **200** | 404 · 422 |
| DELETE | `/consultas/{id}` | `id` | — | **204** | 404 |
| DELETE | `/consultas` | cabecera `X-Sesion` | — | **204** borra todo el historial de esa sesión | 422 si falta la cabecera |

**Respuesta de ejemplo de `POST /consultas` (201):**

```json
{
  "id": 7,
  "pregunta": "¿Mi arrendador puede subirme el arriendo a mitad de contrato?",
  "respuesta": "Estos son los artículos del corpus más relacionados con tu pregunta…\n\n• Codigo Civil, art. 1928: …",
  "citas": [{ "fragmento_id": 4351, "fuente": "Codigo Civil", "articulo": "art. 1928" }],
  "util": null,
  "creada_en": "2026-10-20T14:32:00Z"
}
```

## Cabecera `X-Sesion` (opcional)

Identificador anónimo que genera el navegador (8 a 64 letras, números o guiones). Si viene, `GET /consultas` y las operaciones sobre `/consultas/{id}` se limitan a esa sesión (una consulta de otra sesión responde 404). No es un dato personal. Si no viene (por ejemplo, desde Postman), no se filtra.

## Campos nuevos en la respuesta de `consultas`

- `modo`: `"ia"` si la redactó el modelo de lenguaje (Gemini) o `"extractiva"` si se usó el respaldo que muestra los artículos.
- `duracion_ms`: tiempo que tomó responder (la promesa es menos de 1 minuto).

`GET /fuentes` y `GET /fuentes/{id}` incluyen `articulos` (cantidad de artículos cargados). `GET /fragmentos/{id}` incluye `fuente_titulo` y `url_oficial`.

## Utilitario

| Verbo | Ruta | Éxito |
|---|---|---|
| GET | `/salud` | **200** `{"estado":"ok"}` (comprueba que la API y la base responden) |

## Reglas de negocio de `consultas`

- La pregunta se recorta (sin espacios sobrantes) y debe tener entre **5 y 1000** caracteres; si no, **422** con código `REGLA_DE_NEGOCIO`.
- Al crear una consulta se buscan los artículos más relacionados (**hasta 3**) y se guardan como sus citas, junto con la consulta, en **una sola transacción** (se guarda todo o nada).
- Si no se encuentra ningún artículo, la respuesta lo dice y `citas` queda vacía: **nunca se inventa una cita**.
- **Recuperación:** búsqueda por significado (embeddings + pgvector) y por palabras (texto completo en español), combinadas por ranking recíproco; se entregan hasta 6 artículos al modelo.
- **Redacción:** Gemini redacta en lenguaje simple solo con esos artículos; la API acepta únicamente citas a códigos entregados (máximo 3). Si el modelo no está disponible o responde algo inválido, la respuesta es extractiva.

## Notas de diseño

- `consultas` no tiene `PUT`: la pregunta y la respuesta no se editan, solo el feedback (`PATCH`).
- La base de datos y el diagrama están en `db/schema.sql` y `db/modelo_datos.png`.
- Sin cuentas de usuario: el historial se separa por sesión anónima. Las consultas se borran solas a los 90 días (`RETENCION_DIAS`).
