#!/usr/bin/env python3
"""
setup_rag.py — Create and populate the Vertex AI RAG corpus.
Uploads documents to GCS and imports them into the RAG Engine.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

PROJECT_ID  = os.environ.get("GOOGLE_CLOUD_PROJECT", "tcs-1770741130267")
REGION      = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
GCS_BUCKET  = os.environ.get("GCS_BUCKET", f"{PROJECT_ID}-waste-engine")
SA_KEY_FILE = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(Path(__file__).parent.parent / "tcs-1770741130267-a4a73ebadced.json"),
)
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", SA_KEY_FILE)

DOCS_DIR = Path(__file__).parent.parent / "rag" / "documents"


def upload_docs_to_gcs() -> None:
    """Upload all RAG knowledge documents to GCS."""
    from google.cloud import storage

    print(f"[RAG SETUP] Uploading documents to gs://{GCS_BUCKET}/rag-docs/")
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET)

    doc_files = list(DOCS_DIR.glob("*.txt"))
    if not doc_files:
        print("[RAG SETUP] No .txt documents found in rag/documents/")
        return

    for doc_path in doc_files:
        blob_name = f"rag-docs/{doc_path.name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(doc_path))
        print(f"[RAG SETUP]   Uploaded: {doc_path.name}")

    print(f"[RAG SETUP] {len(doc_files)} documents uploaded.")


def setup_corpus() -> str:
    """Create the RAG corpus and import all documents."""
    from rag.corpus_builder import setup_complete_corpus
    corpus_name = setup_complete_corpus()
    return corpus_name


def main():
    print("=" * 60)
    print("  Vertex AI RAG Corpus Setup")
    print("=" * 60)
    print(f"  Project: {PROJECT_ID}")
    print(f"  Region:  {REGION}")
    print(f"  Bucket:  gs://{GCS_BUCKET}")
    print()

    # Step 1: Upload docs to GCS
    upload_docs_to_gcs()

    # Step 2: Create corpus and import
    corpus_name = setup_corpus()

    print()
    print("=" * 60)
    print("  RAG Setup Complete!")
    print("=" * 60)
    print(f"  Corpus: {corpus_name}")
    print()
    print("  The corpus name has been saved to .rag_corpus_name")
    print("  It will be used automatically by all agents.")


if __name__ == "__main__":
    main()
