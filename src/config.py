"""Central configuration for the Hybrid RAG system.

All paths, model names, environment variables, and pipeline hyperparameters
are defined here so the system is maintainable and viva-defensible.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. Project Directory Structure
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DOCS_DIR = DATA_DIR / "docs"
CHROMA_DIR = DATA_DIR / "chroma"
SQLITE_DB_PATH = DATA_DIR / "sales.db"
EVAL_DIR = BASE_DIR / "eval"
GOLDEN_SET_PATH = EVAL_DIR / "golden_set.json"

# Ensure essential data directories exist on startup
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# 2. Environment Variables & API Secrets
# ---------------------------------------------------------
load_dotenv(dotenv_path=BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

# ---------------------------------------------------------
# 3. Model Definitions
# ---------------------------------------------------------
# Groq LLMs: allow override via environment variable while defaulting to active endpoints
# 'openai/gpt-oss-120b' (or 'llama-3.3-70b-versatile') for complex reasoning/answers/SQL
# 'openai/gpt-oss-20b' (or 'llama-3.1-8b-instant') for fast routing & cheap tasks
LLM_MODEL_SMART = os.getenv("LLM_MODEL_SMART", "openai/gpt-oss-120b")
LLM_MODEL_FAST = os.getenv("LLM_MODEL_FAST", "openai/gpt-oss-20b")

# Local Embeddings: HuggingFace BGE (free, run 100% locally via sentence-transformers)
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL_NAME = "BAAI/bge-reranker-base"
EMBEDDING_DIMENSION = 384  # bge-small output vector size

# ---------------------------------------------------------
# 4. RAG Pipeline Parameters
# ---------------------------------------------------------
# Target chunk size: 500-800 tokens with ~10-15% overlap
CHUNK_SIZE_TOKENS = 650
CHUNK_OVERLAP_TOKENS = 75
DEFAULT_TOP_K = 5

# ---------------------------------------------------------
# 5. SQL Agent Guardrails
# ---------------------------------------------------------
SQL_DEFAULT_LIMIT = 20
SQL_MAX_LIMIT = 50
SQL_MAX_RETRIES = 2
