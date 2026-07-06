from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.rag.retriever import RetrievedChunk
from app.rag.vector_store import ChromaVectorStore
from app.services.generation_service import GenerationService


class DocumentToolService:
    """Lightweight document tools for page reading and table extraction."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.vector_store = ChromaVectorStore()
        self.generator = GenerationService()

    def read_page(self, source_name: str, page: int) -> list[RetrievedChunk]:
        records = self.vector_store.get_chunks_by_page(source_name=source_name, page=page)
        return [self._to_chunk(record) for record in records]

    def extract_tables(self, source_name: str, page: int | None = None) -> list[RetrievedChunk]:
        records = self.vector_store.get_chunks_by_element(
            source_name=source_name,
            element_type="table",
            page=page,
        )
        return [self._to_chunk(record) for record in records]

    def describe_figures(self, source_name: str, page: int | None = None) -> list[RetrievedChunk]:
        records = self.vector_store.get_chunks_by_element(
            source_name=source_name,
            element_type="figure_caption",
            page=page,
        )
        descriptions: list[RetrievedChunk] = []
        for record in records:
            chunk = self._to_chunk(record)
            description = self._generate_figure_description(chunk)
            descriptions.append(
                RetrievedChunk(
                    chunk_id=f"{chunk.chunk_id}-figure-desc",
                    text=description,
                    source=chunk.source,
                    source_type=chunk.source_type,
                    source_path=chunk.source_path,
                    page=chunk.page,
                    distance=None,
                    element_type="figure_description",
                    section_title=chunk.section_title,
                    parent_section=chunk.parent_section,
                    figure_caption=chunk.figure_caption,
                    page_summary=chunk.page_summary,
                )
            )

        return descriptions

    def _to_chunk(self, record: dict[str, object]) -> RetrievedChunk:
        metadata = record.get("metadata", {}) or {}
        return RetrievedChunk(
            chunk_id=str(record.get("chunk_id", "")),
            text=str(record.get("text", "")),
            source=str(metadata.get("source_name", "unknown")),
            source_type=str(metadata.get("source_type", "unknown")),
            source_path=str(metadata.get("source_path", "")),
            page=int(metadata["page"]) if "page" in metadata else None,
            distance=None,
            element_type=str(metadata.get("element_type", "paragraph")),
            section_title=str(metadata.get("section_title", "")),
            parent_section=str(metadata.get("parent_section", "")),
            table_title=str(metadata.get("table_title", "")),
            figure_caption=str(metadata.get("figure_caption", "")),
            page_summary=str(metadata.get("page_summary", "")),
        )

    def _generate_figure_description(self, chunk: RetrievedChunk) -> str:
        if not self.settings.figure_vision_enabled:
            return chunk.text

        try:
            return self.generator.describe_figure(
                figure_caption=chunk.figure_caption or chunk.text,
                page_summary=chunk.page_summary,
                section_title=chunk.section_title,
            )
        except Exception:
            return chunk.text
