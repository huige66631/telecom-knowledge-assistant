from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.rag.keyword_index import KeywordIndex
from app.rag.reranker import SimpleReranker
from app.rag.vector_store import ChromaVectorStore


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    source: str
    source_type: str
    source_path: str
    page: int | None
    distance: float | None
    element_type: str = "paragraph"
    section_title: str = ""
    parent_section: str = ""
    table_title: str = ""
    figure_caption: str = ""
    page_summary: str = ""
    keyword_score: float | None = None
    vector_rank: int | None = None
    keyword_rank: int | None = None
    fused_score: float | None = None


class KnowledgeRetriever:
    """Hybrid retriever with vector search, keyword search, and RRF fusion."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._vector_store: ChromaVectorStore | None = None
        self.reranker = SimpleReranker()

    @property
    def vector_store(self) -> ChromaVectorStore:
        if self._vector_store is None:
            self._vector_store = ChromaVectorStore()
        return self._vector_store

    def search(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        final_limit = top_k or self.settings.retrieval_top_k
        candidate_limit = max(final_limit, self.settings.hybrid_candidate_k)

        vector_matches = self.vector_store.query(query_text=query, top_k=candidate_limit)
        keyword_matches = self._build_keyword_index().search(query=query, top_k=candidate_limit)

        fused = self._rrf_fuse(vector_matches=vector_matches, keyword_matches=keyword_matches)
        reranked = self.reranker.rerank(fused)
        filtered = self._filter_candidates(reranked)
        return [self._to_retrieved_chunk(item) for item in filtered[:final_limit]]

    def _build_keyword_index(self) -> KeywordIndex:
        chunks = self.vector_store.get_all_chunks()
        return KeywordIndex(chunks)

    def _rrf_fuse(
        self,
        vector_matches: list[dict[str, object]],
        keyword_matches: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        combined: dict[str, dict[str, object]] = {}

        for rank, match in enumerate(vector_matches, start=1):
            chunk_id = str(match["chunk_id"])
            entry = combined.setdefault(chunk_id, self._copy_match(match))
            entry["vector_rank"] = rank
            entry["distance"] = match.get("distance")

        for rank, match in enumerate(keyword_matches, start=1):
            chunk_id = str(match["chunk_id"])
            entry = combined.setdefault(chunk_id, self._copy_match(match))
            entry["keyword_rank"] = rank
            entry["keyword_score"] = match.get("keyword_score")

        scored: list[dict[str, object]] = []
        rrf_k = self.settings.rrf_k

        for entry in combined.values():
            fused_score = 0.0
            vector_rank = entry.get("vector_rank")
            keyword_rank = entry.get("keyword_rank")

            if isinstance(vector_rank, int):
                fused_score += 1.0 / (rrf_k + vector_rank)
            if isinstance(keyword_rank, int):
                fused_score += 1.0 / (rrf_k + keyword_rank)

            entry["fused_score"] = fused_score
            scored.append(entry)

        scored.sort(key=lambda item: float(item.get("fused_score", 0.0)), reverse=True)
        return scored

    def _filter_candidates(self, candidates: list[dict[str, object]]) -> list[dict[str, object]]:
        filtered: list[dict[str, object]] = []

        for candidate in candidates:
            distance = candidate.get("distance")
            keyword_score = candidate.get("keyword_score")

            passes_vector = isinstance(distance, float) and distance <= self.settings.vector_max_distance
            passes_keyword = isinstance(keyword_score, float) and keyword_score >= self.settings.keyword_min_score

            if passes_vector or passes_keyword:
                filtered.append(candidate)

        return filtered

    def _to_retrieved_chunk(self, match: dict[str, object]) -> RetrievedChunk:
        metadata = match["metadata"]
        return RetrievedChunk(
            chunk_id=str(match["chunk_id"]),
            text=str(match["text"]),
            source=str(metadata.get("source_name", "unknown")),
            source_type=str(metadata.get("source_type", "unknown")),
            source_path=str(metadata.get("source_path", "")),
            page=int(metadata["page"]) if "page" in metadata else None,
            distance=match["distance"] if isinstance(match.get("distance"), float) else None,
            element_type=str(metadata.get("element_type", "paragraph")),
            section_title=str(metadata.get("section_title", "")),
            parent_section=str(metadata.get("parent_section", "")),
            table_title=str(metadata.get("table_title", "")),
            figure_caption=str(metadata.get("figure_caption", "")),
            page_summary=str(metadata.get("page_summary", "")),
            keyword_score=(
                float(match["keyword_score"])
                if isinstance(match.get("keyword_score"), (float, int))
                else None
            ),
            vector_rank=match["vector_rank"] if isinstance(match.get("vector_rank"), int) else None,
            keyword_rank=match["keyword_rank"] if isinstance(match.get("keyword_rank"), int) else None,
            fused_score=float(match["fused_score"]) if isinstance(match.get("fused_score"), float) else None,
        )

    def _copy_match(self, match: dict[str, object]) -> dict[str, object]:
        return {
            "chunk_id": str(match["chunk_id"]),
            "text": str(match["text"]),
            "metadata": match.get("metadata", {}),
            "distance": match.get("distance"),
            "keyword_score": match.get("keyword_score"),
            "vector_rank": match.get("vector_rank"),
            "keyword_rank": match.get("keyword_rank"),
        }
