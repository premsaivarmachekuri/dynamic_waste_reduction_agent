"""
retriever.py — Vertex AI RAG retrieval with intelligent fallback.

Provides contextual knowledge retrieval for all agents.
Falls back to local document search when Vertex AI RAG is unavailable.
"""

import os
import sys
import re
from pathlib import Path
from functools import lru_cache
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "tcs-1770741130267")
REGION     = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

DOCS_DIR           = Path(__file__).parent / "documents"
CORPUS_NAME_FILE   = Path(__file__).parent.parent / ".rag_corpus_name"
_rag_available     = None  # lazy-initialized
_local_docs: dict  = {}    # lazy-loaded local document fallback


def _get_corpus_name() -> Optional[str]:
    """Return the stored RAG corpus name, or env var override."""
    env_corpus = os.environ.get("RAG_CORPUS_NAME", "")
    if env_corpus:
        return env_corpus
    if CORPUS_NAME_FILE.exists():
        name = CORPUS_NAME_FILE.read_text().strip()
        return name if name else None
    return None


def _check_rag_available() -> bool:
    """Test whether Vertex AI RAG is reachable."""
    global _rag_available
    if _rag_available is not None:
        return _rag_available

    corpus_name = _get_corpus_name()
    if not corpus_name:
        _rag_available = False
        return False

    try:
        import vertexai
        sa_key = os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS",
            str(Path(__file__).parent.parent / "tcs-1770741130267-a4a73ebadced.json"),
        )
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", sa_key)
        vertexai.init(project=PROJECT_ID, location=REGION)
        _rag_available = True
    except Exception:
        _rag_available = False

    return _rag_available


def _load_local_docs() -> dict:
    """Load all local RAG documents into memory for fallback search."""
    global _local_docs
    if _local_docs:
        return _local_docs

    docs = {}
    if DOCS_DIR.exists():
        for doc_path in DOCS_DIR.glob("*.txt"):
            with open(doc_path) as f:
                docs[doc_path.stem] = f.read()
    _local_docs = docs
    return docs


def _local_retrieval(query: str, top_k: int = 5) -> str:
    """
    Simple keyword-based retrieval from local documents.
    Used as fallback when Vertex AI RAG is unavailable.
    """
    docs = _load_local_docs()
    if not docs:
        return "No domain knowledge documents available."

    query_lower = query.lower()
    query_terms = set(re.findall(r'\b\w{3,}\b', query_lower))

    scored_chunks = []
    for doc_name, content in docs.items():
        # Split into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
        for para in paragraphs:
            para_lower = para.lower()
            score = sum(1 for term in query_terms if term in para_lower)
            if score > 0:
                scored_chunks.append((score, para))

    scored_chunks.sort(key=lambda x: -x[0])
    top_chunks = [chunk for _, chunk in scored_chunks[:top_k]]

    if not top_chunks:
        # Return first paragraph of most relevant doc as fallback
        for doc_name, content in docs.items():
            paras = content.split('\n\n')
            if paras:
                return paras[0][:500]
        return "No relevant context found in knowledge base."

    return "\n\n---\n\n".join(top_chunks[:top_k])


def retrieve_context(query: str, top_k: int = 5) -> str:
    """
    Retrieve relevant context from the RAG corpus for a given query.

    Uses Vertex AI RAG Engine when available, falls back to local document search.

    Args:
        query: The question or context needed
        top_k: Number of context chunks to retrieve

    Returns:
        Concatenated relevant context text from the knowledge base.
    """
    corpus_name = _get_corpus_name()

    if corpus_name and _check_rag_available():
        try:
            from vertexai.preview import rag

            response = rag.retrieval_query(
                rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
                text=query,
                similarity_top_k=top_k,
            )
            contexts = response.contexts.contexts
            if contexts:
                chunks = [ctx.text for ctx in contexts]
                return "\n\n---\n\n".join(chunks)
            # Corpus empty — use local fallback
            return _local_retrieval(query, top_k)
        except Exception as e:
            # Silently fall through to local fallback
            return _local_retrieval(query, top_k)

    return _local_retrieval(query, top_k)


def retrieve_waste_strategy(product_name: str, category: str, days_to_expiry: int) -> str:
    """Retrieve specific waste reduction strategy for a product."""
    query = (
        f"What is the optimal action for {product_name} in category {category} "
        f"with {days_to_expiry} days to expiry? "
        f"Discount percentage, transfer decision, or loyalty coupon recommendation."
    )
    return retrieve_context(query, top_k=4)


def retrieve_pricing_strategy(category: str, discount_scenario: str) -> str:
    """Retrieve pricing elasticity and discount strategy for a category."""
    query = f"Price elasticity and discount strategy for {category}. {discount_scenario}"
    return retrieve_context(query, top_k=3)


def retrieve_esg_benchmarks(metric: str) -> str:
    """Retrieve ESG reporting benchmarks and calculation methods."""
    query = f"ESG metric calculation: {metric}. CO2 emission factors, waste reduction targets."
    return retrieve_context(query, top_k=3)


def retrieve_logistics_guidance(from_store: str, to_store: str, category: str) -> str:
    """Retrieve transfer logistics guidance for a store pair and category."""
    query = (
        f"Transfer logistics from {from_store} to {to_store} for {category}. "
        f"Cold chain requirements, cost per unit, viability criteria."
    )
    return retrieve_context(query, top_k=3)


def retrieve_seasonal_context(category: str, month: int = None) -> str:
    """Retrieve seasonal demand patterns for a category."""
    import datetime
    if month is None:
        month = datetime.date.today().month
    month_name = datetime.date(2000, month, 1).strftime("%B")
    query = f"Seasonal demand pattern for {category} in {month_name}. Day-of-week demand index."
    return retrieve_context(query, top_k=3)


def retrieve_food_safety_rules(category: str, action_type: str) -> str:
    """Retrieve food safety compliance rules for a given action and category."""
    query = (
        f"Food safety regulations for {action_type} of {category}. "
        f"Temperature requirements, use-by date rules, legal constraints."
    )
    return retrieve_context(query, top_k=3)
