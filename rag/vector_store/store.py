"""
Local vector store for the policy RAG system.

Uses TF-IDF + cosine similarity rather than a remote embedding API. This
is a deliberate choice for a self-contained hackathon prototype: the
knowledge base is small (30 curated entries), TF-IDF requires no network
access or API keys, and it is fully reproducible. The retrieval interface
is embedding-agnostic, so a transformer-based embedding model could be
swapped in later without changing the router/API contract.
"""
from __future__ import annotations

import json
import os
import pickle
from dataclasses import asdict
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag.ingestion.ingest import PolicyChunk


class PolicyVectorStore:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = None
        self.chunks: List[PolicyChunk] = []

    def build(self, chunks: List[PolicyChunk]):
        self.chunks = chunks
        texts = [c.full_text for c in chunks]
        self.matrix = self.vectorizer.fit_transform(texts)
        return self

    def search(self, query: str, top_k: int = 3, min_score: float = 0.10):
        """
        Returns up to top_k chunks whose cosine similarity to the query
        exceeds min_score, ranked by similarity. Returns an empty list if
        nothing meets the threshold -- callers must treat this as "the
        knowledge base does not contain an answer to this query" rather
        than fabricating a response.
        """
        if self.matrix is None:
            raise RuntimeError("Vector store has not been built yet.")
        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
        results = []
        for i in ranked[:top_k]:
            if scores[i] >= min_score:
                c = self.chunks[i]
                results.append({
                    "chunk_id": c.chunk_id,
                    "title": c.title,
                    "content": c.content,
                    "source": c.source,
                    "relevance_score": float(scores[i]),
                })
        return results

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "PolicyVectorStore":
        with open(path, "rb") as f:
            return pickle.load(f)
