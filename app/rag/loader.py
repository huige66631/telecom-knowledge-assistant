from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@dataclass(slots=True)
class LoadedSection:
    text: str
    metadata: dict[str, str | int | float | bool]


@dataclass(slots=True)
class LoadedDocument:
    document_id: str
    source_name: str
    source_type: str
    source_path: Path
    sections: list[LoadedSection]

    @property
    def full_text(self) -> str:
        return "\n\n".join(section.text for section in self.sections if section.text.strip())


class DocumentLoader:
    """Load raw files into normalized text sections."""

    def load(self, file_path: Path, document_id: str, source_name: str | None = None) -> LoadedDocument:
        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file type '{suffix}'. Supported types: {supported}.")

        if suffix == ".pdf":
            sections = self._load_pdf(file_path)
        elif suffix == ".docx":
            sections = self._load_docx(file_path)
        else:
            sections = self._load_text(file_path)

        readable_sections = [section for section in sections if section.text.strip()]
        if not readable_sections:
            raise ValueError(f"No readable text found in '{file_path.name}'.")

        return LoadedDocument(
            document_id=document_id,
            source_name=source_name or file_path.name,
            source_type=suffix.lstrip("."),
            source_path=file_path,
            sections=readable_sections,
        )

    def _load_pdf(self, file_path: Path) -> list[LoadedSection]:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        sections: list[LoadedSection] = []

        for index, page in enumerate(reader.pages, start=1):
            text = self._normalize_text(page.extract_text() or "")
            if not text:
                continue

            sections.append(
                LoadedSection(
                    text=text,
                    metadata={"page": index, "section_index": index - 1},
                )
            )

        return sections

    def _load_docx(self, file_path: Path) -> list[LoadedSection]:
        from docx import Document

        document = Document(str(file_path))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        text = self._normalize_text("\n".join(paragraphs))
        if not text:
            return []

        return [LoadedSection(text=text, metadata={"section_index": 0})]

    def _load_text(self, file_path: Path) -> list[LoadedSection]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        normalized = self._normalize_text(text)
        if not normalized:
            return []

        return [LoadedSection(text=normalized, metadata={"section_index": 0})]

    def _normalize_text(self, text: str) -> str:
        compact = text.replace("\u0000", " ")
        compact = re.sub(r"\r\n?", "\n", compact)
        compact = re.sub(r"[ \t]+", " ", compact)
        compact = re.sub(r"\n{3,}", "\n\n", compact)
        return compact.strip()
