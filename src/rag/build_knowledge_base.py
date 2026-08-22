"""
Builds the policy RAG knowledge base from the provided PDF and persists
it to disk for fast loading by the API/router.

Run: python -m src.rag.build_knowledge_base
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from rag.ingestion.ingest import ingest
from rag.vector_store.store import PolicyVectorStore

PDF_PATH = os.path.join("documents", "policies", "Policies_and_Guidelines.pdf")
STORE_PATH = os.path.join("rag", "vector_store", "policy_store.pkl")


def main():
    print(f"Ingesting: {PDF_PATH}")
    chunks = ingest(PDF_PATH)
    print(f"Extracted {len(chunks)} policy chunks")

    store = PolicyVectorStore().build(chunks)
    store.save(STORE_PATH)
    print(f"Saved vector store -> {STORE_PATH}")

    # Quick sanity check
    results = store.search("student data privacy", top_k=3)
    print("\nSanity check query: 'student data privacy'")
    for r in results:
        print(f"  [{r['chunk_id']}] {r['title']} (score={r['relevance_score']:.3f})")


if __name__ == "__main__":
    main()
