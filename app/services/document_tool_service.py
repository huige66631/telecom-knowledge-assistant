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

    def read_section(self, source_name: str, section_title: str, page: int | None = None) -> list[RetrievedChunk]:
        records = self.vector_store.get_all_chunks()
        normalized_target = self._normalize_section(section_title)
        anchor_record: dict[str, object] | None = None

        for record in records:
            metadata = record.get("metadata", {}) or {}
            if str(metadata.get("source_name", "")) != source_name:
                continue
            if page is not None and int(metadata.get("page", -1)) != page:
                continue

            record_section = self._normalize_section(str(metadata.get("section_title", "")).strip())
            record_parent = self._normalize_section(str(metadata.get("parent_section", "")).strip())
            if normalized_target and normalized_target not in {record_section, record_parent}:
                continue

            if anchor_record is None:
                anchor_record = record
            record_element = str(metadata.get("element_type", ""))
            if record_element == "heading" and record_section == normalized_target:
                anchor_record = record
                break

        if anchor_record is None:
            return []

        return self._collect_section_window(
            records=records,
            source_name=source_name,
            anchor_record=anchor_record,
        )

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

    def _chunk_sort_key(self, chunk_id: str) -> int:
        suffix = chunk_id.rsplit("-", 1)[-1]
        digits = "".join(char for char in suffix if char.isdigit())
        return int(digits) if digits else 0

    def _collect_section_window(
        self,
        records: list[dict[str, object]],
        source_name: str,
        anchor_record: dict[str, object],
    ) -> list[RetrievedChunk]:
        anchor_metadata = anchor_record.get("metadata", {}) or {}
        anchor_page = int(anchor_metadata.get("page", 0))
        anchor_chunk_index = int(anchor_metadata.get("chunk_index", 0))
        anchor_section = self._normalize_section(str(anchor_metadata.get("section_title", "")))
        anchor_heading_level = int(anchor_metadata.get("heading_level", 0) or 0)

        source_records = [
            record
            for record in records
            if str((record.get("metadata", {}) or {}).get("source_name", "")) == source_name
        ]
        source_records.sort(key=lambda item: int(((item.get("metadata", {}) or {}).get("chunk_index", 0))))

        collected: list[RetrievedChunk] = []
        started = False

        for record in source_records:
            metadata = record.get("metadata", {}) or {}
            record_chunk_index = int(metadata.get("chunk_index", 0))
            if record_chunk_index < anchor_chunk_index:
                continue

            if not started:
                started = True

            if record_chunk_index > anchor_chunk_index:
                if int(metadata.get("page", anchor_page)) != anchor_page:
                    break

                record_element = str(metadata.get("element_type", "paragraph"))
                record_heading_level = int(metadata.get("heading_level", 0) or 0)
                record_section = self._normalize_section(str(metadata.get("section_title", "")))

                if record_element == "heading":
                    if record_section == anchor_section:
                        pass
                    elif anchor_heading_level and record_heading_level and record_heading_level <= anchor_heading_level:
                        break
                    elif anchor_section and record_section and record_section != anchor_section:
                        break

            if str(metadata.get("element_type", "")) in {"page_summary", "footnote", "toc_entry"}:
                continue
            collected.append(self._to_chunk(record))
            if len(collected) >= 8:
                break

        return collected

    def _normalize_section(self, text: str) -> str:
        compact = "".join(char for char in text.lower() if char.isalnum())
        return compact
