from __future__ import annotations

from app.models.schemas import Citation
from app.rag.retriever import RetrievedChunk


class CitationService:
    """Convert retrieved chunks into consistent citation payloads."""

    def build_citations(self, matches: list[RetrievedChunk], snippet_length: int = 280) -> list[Citation]:
        citations: list[Citation] = []
        for match in matches:
            citations.append(
                Citation(
                    source=match.source,
                    snippet=match.text[:snippet_length],
                    chunk_id=match.chunk_id,
                    score=match.distance,
                    page=match.page,
                    element_type=match.element_type,
                    section_title=match.section_title,
                    table_title=match.table_title,
                    figure_caption=match.figure_caption,
                    keyword_score=match.keyword_score,
                    fused_score=match.fused_score,
                )
            )
        return citations
