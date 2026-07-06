from __future__ import annotations

from dataclasses import dataclass

from app.rag.loader import LoadedDocument


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    text: str
    metadata: dict[str, str | int | float | bool]


class TextChunker:
    """Structure-aware chunker with overlap and context enrichment."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: LoadedDocument) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        chunk_index = 0

        for section in document.sections:
            if str(section.metadata.get("element_type", "")) == "toc_entry":
                continue
            section_chunks = self._split_section(section.text, element_type=str(section.metadata.get("element_type", "paragraph")))

            for sub_index, section_chunk in enumerate(section_chunks, start=1):
                chunk_index += 1
                metadata = {
                    "document_id": document.document_id,
                    "source_name": document.source_name,
                    "source_type": document.source_type,
                    "source_path": str(document.source_path),
                    "chunk_index": chunk_index,
                    "sub_chunk_index": sub_index,
                }
                metadata.update(section.metadata)
                enriched_text = self._build_chunk_text(section_chunk, metadata)

                chunks.append(
                    ChunkRecord(
                        chunk_id=f"{document.document_id}-chunk-{chunk_index:04d}",
                        text=enriched_text,
                        metadata=metadata,
                    )
                )

        return chunks

    def _split_section(self, text: str, element_type: str) -> list[str]:
        if not text.strip():
            return []

        if element_type in {"heading", "figure_caption", "footnote", "page_summary"}:
            return [text.strip()]

        if element_type == "table":
            return self._split_table_block(text)

        return self._split_text(text)

    def _split_table_block(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) <= 1:
            return [text.strip()]

        title = lines[0]
        body_lines = lines[1:]
        chunks: list[str] = []
        current_lines: list[str] = [title]
        current_length = len(title)

        for line in body_lines:
            if current_length + len(line) + 1 > self.chunk_size and len(current_lines) > 1:
                chunks.append("\n".join(current_lines).strip())
                overlap_lines = current_lines[-1:]
                current_lines = [title] + overlap_lines + [line]
                current_length = sum(len(item) for item in current_lines)
            else:
                current_lines.append(line)
                current_length += len(line) + 1

        if current_lines:
            chunks.append("\n".join(current_lines).strip())

        return chunks

    def _split_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text.strip()]

        chunks: list[str] = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            if end < text_length:
                breakpoints = [
                    text.rfind("\n\n", start, end),
                    text.rfind("\n", start, end),
                    text.rfind("。", start, end),
                    text.rfind("；", start, end),
                    text.rfind(" ", start, end),
                ]
                best_break = max(breakpoints)
                if best_break > start + int(self.chunk_size * 0.5):
                    end = best_break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            start = max(end - self.chunk_overlap, start + 1)

        return chunks

    def _build_chunk_text(self, section_chunk: str, metadata: dict[str, str | int | float | bool]) -> str:
        context_lines: list[str] = []
        section_title = str(metadata.get("section_title", "")).strip()
        parent_section = str(metadata.get("parent_section", "")).strip()
        table_title = str(metadata.get("table_title", "")).strip()
        figure_caption = str(metadata.get("figure_caption", "")).strip()
        page_summary = str(metadata.get("page_summary", "")).strip()
        page = metadata.get("page")
        element_type = str(metadata.get("element_type", "paragraph"))

        if parent_section:
            context_lines.append(f"Parent Section: {parent_section}")
        if section_title:
            context_lines.append(f"Section Title: {section_title}")
        if table_title:
            context_lines.append(f"Table Title: {table_title}")
        if figure_caption:
            context_lines.append(f"Figure Caption: {figure_caption}")
        if page:
            context_lines.append(f"Page: {page}")
        if element_type:
            context_lines.append(f"Element Type: {element_type}")
        if page_summary:
            context_lines.append(f"Page Summary: {page_summary}")

        context_lines.append("Content:")
        context_lines.append(section_chunk.strip())
        return "\n".join(context_lines).strip()
