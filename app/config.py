"""Configuración leída del entorno (.env). Nada sensible vive en el código."""
import os
from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta DATABASE_URL. Copia .env.example como .env y completa los valores.")
    return url


def gemini_api_key() -> str | None:
    clave = os.environ.get("GEMINI_API_KEY", "").strip()
    return clave or None


def gemini_modelo() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest,gemini-flash-latest").strip()


def gemini_pensamiento() -> str:
    """Cuánto 'piensa' Gemini antes de responder: minimo (rápido, por defecto), bajo, o alto (lo que
    el modelo traiga por defecto: más lento). Permite comparar con scripts/evaluar.py sin tocar código."""
    v = os.environ.get("GEMINI_PENSAMIENTO", "minimo").strip().lower()
    return v if v in ("minimo", "bajo", "alto") else "minimo"


def retencion_dias() -> int:
    return int(os.environ.get("RETENCION_DIAS", "90"))


def embeddings_activos() -> bool:
    return os.environ.get("EMBEDDINGS", "si").strip().lower() not in ("no", "0", "false")


def origenes_permitidos() -> list[str]:
    return [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
