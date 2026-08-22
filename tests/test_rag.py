import pytest
from rag.ingestion.ingest import ingest
from rag.vector_store.store import PolicyVectorStore

PDF_PATH = "documents/policies/Policies_and_Guidelines.pdf"


@pytest.fixture(scope="module")
def store():
    chunks = ingest(PDF_PATH)
    return PolicyVectorStore().build(chunks)


def test_ingestion_extracts_chunks():
    chunks = ingest(PDF_PATH)
    assert len(chunks) > 0


def test_every_chunk_has_a_source(store):
    for c in store.chunks:
        assert c.source and "Extracted from" in c.source


def test_relevant_query_returns_results(store):
    results = store.search("student data privacy")
    assert len(results) > 0
    for r in results:
        assert "source" in r and "content" in r and "title" in r


def test_irrelevant_query_returns_no_results(store):
    results = store.search("recommend a chocolate cake recipe for tonight dinner")
    assert results == []


def test_results_include_relevance_scores_sorted_descending(store):
    results = store.search("human oversight accountability", top_k=5)
    scores = [r["relevance_score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_results_respect_top_k(store):
    results = store.search("privacy", top_k=2)
    assert len(results) <= 2
