from pathlib import Path

from app.rag.chunker import TextChunker
from app.rag.loader import LoadedDocument, LoadedSection


def test_text_chunker_splits_long_text() -> None:
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    document = LoadedDocument(
        document_id="doc-test",
        source_name="sample.txt",
        source_type="txt",
        source_path=Path("sample.txt"),
        sections=[
            LoadedSection(
                text="A" * 120,
                metadata={"section_index": 0},
            )
        ],
    )

    chunks = chunker.chunk_document(document)

    assert len(chunks) >= 3
    assert chunks[0].chunk_id.startswith("doc-test-chunk-")
