# API de Articla (FastAPI). La construye docker-compose.yml.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 MODELOS_DIR=/modelos
COPY requirements.txt requirements-ia.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ia.txt
# Descarga el modelo de embeddings al construir la imagen, para no depender de internet al iniciar.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/modelos')" \
    || echo "No se pudo descargar el modelo ahora: se intentará al iniciar."
COPY app ./app
COPY scripts ./scripts
COPY data ./data
COPY db ./db
COPY tests ./tests
EXPOSE 8000
# preparar.py aplica migraciones, carga el corpus si falta y calcula embeddings; luego inicia la API.
CMD ["sh", "-c", "python -m scripts.preparar && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
