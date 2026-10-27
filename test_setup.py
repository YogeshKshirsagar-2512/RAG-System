"""Sanity verification script for Step 1.

Verifies:
1. .env variables loaded properly (without revealing secrets).
2. Groq LLM connectivity via fast model (llama-3.1-8b-instant).
3. Local Hugging Face embedding model (BAAI/bge-small-en-v1.5) inference.
"""

import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure root directory is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import (
    GROQ_API_KEY,
    LLM_MODEL_FAST,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIMENSION,
    RAW_DATA_DIR,
    DOCS_DIR,
    CHROMA_DIR,
)
from src.llm import simple_prompt


def test_environment() -> bool:
    print("--- [1/3] Testing Environment & Directories ---")
    if not GROQ_API_KEY:
        print("FAIL: GROQ_API_KEY is missing or empty in .env!")
        return False
    print(f"PASS: GROQ_API_KEY detected (Length: {len(GROQ_API_KEY)} chars, starts with '{GROQ_API_KEY[:4]}***')")
    
    assert RAW_DATA_DIR.exists(), "RAW_DATA_DIR does not exist"
    assert DOCS_DIR.exists(), "DOCS_DIR does not exist"
    assert CHROMA_DIR.exists(), "CHROMA_DIR does not exist"
    print("PASS: Core directories verified (raw, docs, chroma).")
    return True


def test_groq_connection() -> bool:
    print("\n--- [2/3] Testing Groq LLM Connectivity ---")
    start_time = time.time()
    try:
        response = simple_prompt(
            user_prompt="Reply with exactly the phrase: 'Groq connection successful!'",
            model=LLM_MODEL_FAST,
            temperature=0.0,
            max_tokens=150,
        )
        elapsed = time.time() - start_time
        print(f"PASS: Groq responded in {elapsed:.2f}s using {LLM_MODEL_FAST}")
        print(f"Response: \"{response.strip()}\"")
        return True
    except Exception as e:
        print(f"FAIL: Groq connection failed: {e}")
        return False


def test_local_embeddings() -> bool:
    print("\n--- [3/3] Testing Local Hugging Face Embeddings ---")
    start_time = time.time()
    try:
        from sentence_transformers import SentenceTransformer

        print(f"Loading local embedding model: '{EMBEDDING_MODEL_NAME}'...")
        embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        sample_text = "Business Analyst Q3 Sales Report"
        embedding = embedder.encode(sample_text)
        elapsed = time.time() - start_time

        dim = len(embedding)
        print(f"PASS: Embedding generated in {elapsed:.2f}s.")
        print(f"Vector dimension: {dim} (Expected: {EMBEDDING_DIMENSION})")
        assert dim == EMBEDDING_DIMENSION, f"Expected dim {EMBEDDING_DIMENSION}, got {dim}"
        return True
    except Exception as e:
        print(f"FAIL: Local embedding test failed: {e}")
        return False


def main():
    print("==================================================")
    print("      Step 1 Verification: Environment & Stack    ")
    print("==================================================")
    
    env_ok = test_environment()
    if not env_ok:
        sys.exit(1)
        
    groq_ok = test_groq_connection()
    if not groq_ok:
        sys.exit(1)
        
    embed_ok = test_local_embeddings()
    if not embed_ok:
        sys.exit(1)

    print("\n==================================================")
    print("  ALL STEP 1 TESTS PASSED SUCCESSFULLY!          ")
    print("==================================================")


if __name__ == "__main__":
    main()
