from pathlib import Path

from app.services.document_registry_service import DocumentRegistryService
from app.services.ingest_service import IngestService


def test_document_registry_upsert_and_find(tmp_path: Path) -> None:
    service = DocumentRegistryService()
    service.registry_path = tmp_path / "registry.json"

    record = {
        "document_id": "doc-1",
        "file_hash": "hash-1",
        "source_name": "a.pdf",
        "raw_path": "data/raw/doc-1.pdf",
        "processed_path": "data/processed/doc-1.txt",
    }
    service.upsert(record)

    found = service.find_by_hash("hash-1")
    assert found is not None
    assert found["document_id"] == "doc-1"


def test_ingest_service_rebuild_index_returns_counts(tmp_path: Path) -> None:
    ingest = IngestService()
    original_chroma_dir = ingest.settings.chroma_persist_dir
    original_collection_name = ingest.settings.knowledge_collection_name
    original_processed_dir = ingest.settings.processed_data_dir

    ingest.settings.chroma_persist_dir = str(tmp_path / "chroma")
    ingest.settings.knowledge_collection_name = "test_rebuild_index_collection"
    ingest.settings.processed_data_dir = str(tmp_path / "processed")
    ingest.registry.registry_path = tmp_path / "registry.json"
    ingest._vector_store = None

    raw_file = tmp_path / "doc-1.md"
    raw_file.write_text("# 标题\n\n设备支持 SSH 与 HTTPS。", encoding="utf-8")

    ingest.registry.save(
        [
            {
                "document_id": "doc-1",
                "file_hash": "hash-1",
                "source_name": "doc-1.md",
                "raw_path": str(raw_file),
                "processed_path": "",
                "source_type": "md",
            }
        ]
    )

    try:
        response = ingest.rebuild_index()
        assert response.status == "success"
        assert response.documents_processed == 1
        assert response.chunks_indexed >= 1
        assert response.collection_size >= 1
    finally:
        ingest.vector_store.client.delete_collection(ingest.settings.knowledge_collection_name)
        ingest.settings.chroma_persist_dir = original_chroma_dir
        ingest.settings.knowledge_collection_name = original_collection_name
        ingest.settings.processed_data_dir = original_processed_dir
