from __future__ import annotations

from dataclasses import dataclass

from app.rag.loader import LoadedDocument


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    text: str
    metadata: dict[str, str | int | float | bool]


class TextChunker:
    """Simple character-based chunker with overlap and soft breakpoints."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: LoadedDocument) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        chunk_index = 0

        for section in document.sections:
            section_chunks = self._split_text(section.text)

            for section_chunk in section_chunks:
                chunk_index += 1
                metadata = {
                    "document_id": document.document_id,
                    "source_name": document.source_name,
                    "source_type": document.source_type,
                    "source_path": str(document.source_path),
                    "chunk_index": chunk_index,
                }
                metadata.update(section.metadata)

                chunks.append(
                    ChunkRecord(
                        chunk_id=f"{document.document_id}-chunk-{chunk_index:04d}",
                        text=section_chunk,
                        metadata=metadata,
                    )
                )

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
