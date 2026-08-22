"""
RAG ingestion: load the policy PDF, extract text, clean it, and split it
into chunks with source references.

The provided document is a curated policy reference where each entry is
already a self-contained numbered item ("1. AI Risk Classification",
"2. Principle 1 — Fairness", ...) ending with an "Extracted from: ..."
citation line. We chunk on these natural entry boundaries rather than a
fixed character window, since each entry is already a coherent unit of
policy content with its own source attribution -- splitting mid-entry
would separate content from its citation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from pypdf import PdfReader


@dataclass
class PolicyChunk:
    chunk_id: int
    title: str
    content: str
    source: str
    full_text: str  # title + content + source, used for embedding/search


def load_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def clean_text(text: str) -> str:
    """Normalize whitespace without altering wording/meaning."""
    text = text.replace("\u2019", "'").replace("\u2014", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


ENTRY_PATTERN = re.compile(
    r"^\s*(\d{1,2})\.\s+(.+?)\s*\n(.*?)(?=^\s*\d{1,2}\.\s+|\Z)",
    re.DOTALL | re.MULTILINE,
)


def split_into_chunks(raw_text: str) -> List[PolicyChunk]:
    """
    Split the cleaned document text into one chunk per numbered policy
    entry (1..30). Each chunk's content includes its 'Extracted from'
    source line so the source travels with the content.
    """
    text = clean_text(raw_text)
    chunks: List[PolicyChunk] = []

    for match in ENTRY_PATTERN.finditer(text):
        num = int(match.group(1))
        title = match.group(2).strip()
        body = match.group(3).strip()

        # Separate the "Extracted from: ..." citation line(s) from content.
        source_match = re.search(r"Extracted from:.*", body, re.DOTALL)
        source = source_match.group(0).strip() if source_match else "Source not found in document"

        chunks.append(PolicyChunk(
            chunk_id=num,
            title=title,
            content=body,
            source=source,
            full_text=f"{title}\n{body}",
        ))

    return chunks


def ingest(pdf_path: str) -> List[PolicyChunk]:
    raw_text = load_pdf_text(pdf_path)
    return split_into_chunks(raw_text)


if __name__ == "__main__":
    chunks = ingest("documents/policies/Policies_and_Guidelines.pdf")
    print(f"Extracted {len(chunks)} policy chunks")
    for c in chunks[:3]:
        print(f"\n--- Chunk {c.chunk_id}: {c.title} ---")
        print(c.content[:200], "...")
        print("SOURCE:", c.source[:120])
