"""Servicios externos de inteligencia artificial, aislados tras una interfaz propia:
- embeddings.py: convierte texto en vectores (modelo abierto que corre en el servidor).
- gemini.py: redacta la respuesta con el modelo de lenguaje de Google por API.
Si alguno no está disponible, la aplicación sigue funcionando con su respaldo."""
