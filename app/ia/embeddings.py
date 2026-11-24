"""Embeddings con un modelo multilingüe de código abierto que corre en el servidor (sin costo por uso).

Modelo: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (384 dimensiones, soporta español),
ejecutado con fastembed (ONNX, sin necesidad de PyTorch). La primera vez se descarga (~220 MB).
Si fastembed no está instalado o EMBEDDINGS=no, `disponible()` es False y la búsqueda usa solo texto.
"""
import os
from functools import lru_cache

from app.config import embeddings_activos

MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSION = 384


@lru_cache(maxsize=1)
def _modelo():
    if not embeddings_activos():
        return None
    try:
        from fastembed import TextEmbedding
        return TextEmbedding(model_name=MODELO, cache_dir=os.environ.get("MODELOS_DIR") or None)
    except Exception as e:  # sin la librería o sin poder descargar el modelo
        print(f"[embeddings] no disponible: {e}")
        return None


def disponible() -> bool:
    return _modelo() is not None


def vectorizar(textos: list[str], lote: int = 64) -> list[list[float]]:
    m = _modelo()
    if m is None:
        raise RuntimeError("El modelo de embeddings no está disponible.")
    return [list(map(float, v)) for v in m.embed(textos, batch_size=lote)]


def como_literal(vector: list[float]) -> str:
    """Formato que entiende pgvector: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"


class Vectorizador:
    """Interfaz que usa la capa de negocio (en las pruebas se reemplaza por una falsa)."""
    def disponible(self) -> bool:
        return disponible()

    def pregunta(self, texto: str) -> list[float] | None:
        if not disponible():
            return None
        try:
            return vectorizar([texto])[0]
        except Exception as e:
            print(f"[embeddings] error al vectorizar la pregunta: {e}")
            return None
