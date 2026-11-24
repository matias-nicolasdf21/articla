# Articla — guía para revisar este repositorio

Proyecto semestral de INGT1003 (Universidad Mayor, 2026). Aplicación web que responde dudas legales cotidianas
citando artículos oficiales de la ley chilena (LeyChile, BCN). Integrantes: Matías del Fierro y Camilo González.

## Cómo levantarlo
1. Copiar `.env.example` como `.env` (los valores de ejemplo sirven para una prueba local).
2. `docker compose up --build` — esperar `[preparar] listo` y `Uvicorn running` (primera vez: 5–15 min).
3. Web: http://localhost:3000 · API: http://localhost:8000/docs · Salud: http://localhost:8000/api/v1/salud

## Qué esperar en un equipo nuevo
- **Corpus:** el repositorio trae las 15 normas base (unos 6.900 artículos). El corpus completo (unas 14.866 leyes y
  93.800 artículos) no está en Git por tamaño: se obtiene con `scripts/corpus_completo.py` (horas, por el límite
  de LeyChile) o restaurando un respaldo `pg_dump` (ver `docs/Manual_Tecnico_Articla.pdf`, capítulos 8 y 9).
- **Sin `GEMINI_API_KEY`** las respuestas salen en modo extractivo ("Artículos encontrados"). Es el respaldo
  diseñado, no un error. Con una clave gratuita de Google AI Studio se ve la respuesta redactada por secciones.

## Cómo verificar
- Pruebas de la capa de negocio (54): `docker compose exec api python -m unittest discover -s tests`
- Pruebas de la API: importar `docs/Articla_API.postman_collection.json` en Postman y ejecutar el Collection Runner.
- Cifras del corpus cargado: `GET /api/v1/estadisticas`.

## Mapa del código
- `web/` Next.js (presentación). `web/app/api/[...path]/route.js` solo reenvía a la API.
- `app/routers` HTTP · `app/services` reglas de negocio y RAG · `app/repositories` SQL · `app/ia` embeddings y Gemini.
- `scripts/` preparación de la base e ingesta (ETL). `db/schema.sql` crea la base. `docs/` documentos en PDF.

## Reglas del proyecto
- Ninguna cita puede apuntar a un artículo que no se entregó al modelo: lo valida
  `validar_redaccion` en `app/services/consultas_service.py` (con pruebas en `tests/test_consultas_service.py`).
- No hay secretos en el repositorio: `.env` está en `.gitignore`.
