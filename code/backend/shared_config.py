"""
Backend shared config (module at backend root).

NOTE: User requested not to use a `shared/` package directory.
This module replaces `backend/shared/config.py`.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env if present
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=False)

# OpenAI / Azure OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Models (override via env if needed)
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
AZURE_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME", "")

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_GRPC_PORT = int(os.getenv("QDRANT_GRPC_PORT", "6334"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "edu-agentic-rag")

# Chunking defaults
DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE", "900"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "120"))


def validate_api_keys(require_embeddings: bool = False) -> bool:
    """
    Validate that required keys are set.
    - require_embeddings=True: require OpenAI or Azure embedding configuration.
    """
    missing = []

    if require_embeddings:
        has_openai = bool(OPENAI_API_KEY)
        has_azure_embed = bool(AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_EMBEDDING_DEPLOYMENT_NAME)
        if not (has_openai or has_azure_embed):
            missing.append("OPENAI_API_KEY (or AZURE_OPENAI_* + AZURE_EMBEDDING_DEPLOYMENT_NAME)")

    if missing:
        print("누락된 설정:", ", ".join(missing))
        return False
    return True


