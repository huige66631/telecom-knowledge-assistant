from __future__ import annotations

from collections import Counter
import math
import re

from app.rag.chunker import ChunkRecord


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,2}")
ASCII_PHRASE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _./+-]{1,}")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def extract_query_signals(text: str) -> list[str]:
    signals: list[str] = []
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return signals

    for token in tokenize(normalized):
        if token not in signals:
            signals.append(token)

    lower_text = normalized.lower()
    ascii_phrases = [match.group(0).strip().lower() for match in ASCII_PHRASE_PATTERN.finditer(normalized)]
    for phrase in ascii_phrases:
        compact = re.sub(r"\s+", "", phrase)
        if len(compact) >= 4:
            for candidate in (phrase, compact):
                if candidate not in signals:
                    signals.append(candidate)

    for candidate in (
        "16 bit",
        "16bit",
        "linear pcm",
        "pcm编码",
        "线性 pcm",
        "线性pcm",
    ):
        if candidate in lower_text or candidate in normalized:
            normalized_candidate = candidate.lower().replace(" ", "")
            if candidate.lower() not in signals:
                signals.append(candidate.lower())
            if normalized_candidate not in signals:
                signals.append(normalized_candidate)

    return signals


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
        query_signals = extract_query_signals(query)
        if not query_tokens:
            return []

        scores: list[tuple[float, dict[str, object]]] = []

        for document in self.documents:
            chunk_id = str(document["chunk_id"])
            score = self._bm25_score(chunk_id, query_tokens)
            score += self._signal_boost(document=document, query_signals=query_signals)
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

    def _signal_boost(self, document: dict[str, object], query_signals: list[str]) -> float:
        if not query_signals:
            return 0.0

        text = str(document.get("text", ""))
        if not text:
            return 0.0

        lowered = text.lower()
        compact = re.sub(r"\s+", "", lowered)
        boost = 0.0

        for signal in query_signals:
            normalized_signal = signal.lower().strip()
            compact_signal = re.sub(r"\s+", "", normalized_signal)
            if not compact_signal:
                continue

            if normalized_signal in lowered:
                boost += 1.2 if " " in normalized_signal else 0.45
                continue

            if len(compact_signal) >= 4 and compact_signal in compact:
                boost += 0.9

        return boost

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
