"""
corpus_builder.py — Manages the Vertex AI RAG Engine corpus lifecycle.

Creates, populates, and maintains the RAG corpus used by all agents
for grounded, context-aware decision-making.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "tcs-1770741130267")
REGION     = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
GCS_BUCKET = os.environ.get("GCS_BUCKET", f"{PROJECT_ID}-waste-engine")
CORPUS_DISPLAY_NAME = "waste-engine-rag-corpus"
CORPUS_NAME_FILE    = Path(__file__).parent.parent / ".rag_corpus_name"


def _init_vertexai():
    """Initialize Vertex AI SDK with project credentials."""
    import vertexai
    sa_key = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        str(Path(__file__).parent.parent / "tcs-1770741130267-a4a73ebadced.json"),
    )
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", sa_key)
    vertexai.init(project=PROJECT_ID, location=REGION)


def get_or_create_corpus() -> str:
    """
    Return the RAG corpus resource name, creating it if it doesn't exist.

    Returns:
        Full corpus resource name, e.g.:
        "projects/123/locations/us-central1/ragCorpora/456"
    """
    # Check if we already have a cached corpus name
    if CORPUS_NAME_FILE.exists():
        corpus_name = CORPUS_NAME_FILE.read_text().strip()
        if corpus_name:
            print(f"[RAG] Using existing corpus: {corpus_name}")
            return corpus_name

    _init_vertexai()
    from vertexai.preview import rag

    # Check if corpus already exists
    try:
        existing = rag.list_corpora()
        for corpus in existing:
            if corpus.display_name == CORPUS_DISPLAY_NAME:
                corpus_name = corpus.name
                CORPUS_NAME_FILE.write_text(corpus_name)
                print(f"[RAG] Found existing corpus: {corpus_name}")
                return corpus_name
    except Exception as e:
        print(f"[RAG] Warning: Could not list corpora: {e}")

    # Create new corpus
    print(f"[RAG] Creating new RAG corpus: {CORPUS_DISPLAY_NAME}")
    corpus = rag.create_corpus(
        display_name=CORPUS_DISPLAY_NAME,
        description=(
            "Domain knowledge corpus for the Dynamic Waste Reduction Engine. "
            "Contains waste reduction strategies, price elasticity data, "
            "ESG standards, seasonal patterns, food safety regulations, "
            "and logistics guidelines for UK supermarket perishables."
        ),
    )
    corpus_name = corpus.name
    CORPUS_NAME_FILE.write_text(corpus_name)
    print(f"[RAG] Corpus created: {corpus_name}")
    return corpus_name


def import_documents_from_gcs(corpus_name: str) -> None:
    """
    Import all RAG knowledge documents from GCS into the corpus.

    Args:
        corpus_name: Full corpus resource name
    """
    _init_vertexai()
    from vertexai.preview import rag

    gcs_path = f"gs://{GCS_BUCKET}/rag-docs/"
    print(f"[RAG] Importing documents from: {gcs_path}")

    try:
        response = rag.import_files(
            corpus_name=corpus_name,
            paths=[gcs_path],
            chunk_size=512,
            chunk_overlap=100,
            max_embedding_requests_per_min=900,
        )
        print(f"[RAG] Import initiated. Response: {response}")
        print("[RAG] Waiting for indexing to complete (30s)...")
        time.sleep(30)
        print("[RAG] Documents indexed.")
    except Exception as e:
        print(f"[RAG] Error importing documents: {e}")
        raise


def verify_corpus(corpus_name: str) -> dict:
    """
    Run a test query to verify the corpus is populated and working.

    Returns:
        Dict with verification results.
    """
    _init_vertexai()
    from vertexai.preview import rag

    test_query = "What is the optimal discount strategy for chicken breast expiring today?"
    print(f"[RAG] Verifying corpus with test query: '{test_query}'")

    try:
        response = rag.retrieval_query(
            rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
            text=test_query,
            similarity_top_k=3,
        )
        contexts = response.contexts.contexts
        if contexts:
            print(f"[RAG] Corpus working. Retrieved {len(contexts)} context chunks.")
            return {
                "status": "healthy",
                "corpus_name": corpus_name,
                "chunks_retrieved": len(contexts),
                "sample": contexts[0].text[:200] if contexts else "",
            }
        else:
            return {"status": "empty", "corpus_name": corpus_name, "chunks_retrieved": 0}
    except Exception as e:
        return {"status": "error", "error": str(e), "corpus_name": corpus_name}


def setup_complete_corpus() -> str:
    """
    Full setup: create corpus, import documents, verify.

    Returns:
        Corpus name (resource path).
    """
    corpus_name = get_or_create_corpus()
    import_documents_from_gcs(corpus_name)
    result = verify_corpus(corpus_name)
    print(f"[RAG] Setup complete. Status: {result['status']}")
    return corpus_name


if __name__ == "__main__":
    name = setup_complete_corpus()
    print(f"\nCorpus resource name: {name}")
