from __future__ import annotations

from collections import Counter
import math
import re

from app.rag.chunker import ChunkRecord


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,2}")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


class KeywordIndex:
    """Small in-memory BM25-style index rebuilt from current vector-store chunks."""

    def __init__(self, documents: list[dict[str, object]]) -> None:
        self.documents = documents
        self.doc_count = len(documents)
        self.avg_doc_len = 0.0
        self.doc_freq: Counter[str] = Counter()
        self.term_freqs: dict[str, Counter[str]] = {}
        self.doc_lengths: dict[str, int] = {}
        self._build()

    @classmethod
    def from_chunks(cls, chunks: list[ChunkRecord]) -> "KeywordIndex":
        documents = [
            {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]
        return cls(documents)

    def _build(self) -> None:
        total_length = 0

        for document in self.documents:
            chunk_id = str(document["chunk_id"])
            tokens = tokenize(str(document["text"]))
            term_counter = Counter(tokens)
            self.term_freqs[chunk_id] = term_counter
            self.doc_lengths[chunk_id] = len(tokens)
            total_length += len(tokens)

            for token in term_counter:
                self.doc_freq[token] += 1

        self.avg_doc_len = total_length / self.doc_count if self.doc_count else 0.0

    def search(self, query: str, top_k: int) -> list[dict[str, object]]:
        if not self.documents:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: list[tuple[float, dict[str, object]]] = []

        for document in self.documents:
            chunk_id = str(document["chunk_id"])
            score = self._bm25_score(chunk_id, query_tokens)
            if score > 0:
                scores.append((score, document))

        scores.sort(key=lambda item: item[0], reverse=True)

        results: list[dict[str, object]] = []
        for score, document in scores[:top_k]:
            results.append(
                {
                    "chunk_id": str(document["chunk_id"]),
                    "text": str(document["text"]),
                    "metadata": document.get("metadata", {}),
                    "keyword_score": score,
                }
            )
        return results

    def _bm25_score(self, chunk_id: str, query_tokens: list[str]) -> float:
        k1 = 1.5
        b = 0.75
        score = 0.0
        doc_length = self.doc_lengths.get(chunk_id, 0)
        term_freq = self.term_freqs.get(chunk_id, Counter())

        for token in query_tokens:
            freq = term_freq.get(token, 0)
            if freq == 0:
                continue

            df = self.doc_freq.get(token, 0)
            idf = math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
            denom = freq + k1 * (1 - b + b * (doc_length / self.avg_doc_len if self.avg_doc_len else 0))
            score += idf * ((freq * (k1 + 1)) / denom)

        return score
