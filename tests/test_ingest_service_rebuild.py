from pathlib import Path

from app.services.ingest_service import IngestService


class FakeRegistry:
    def __init__(self) -> None:
        self.saved_records: list[dict[str, object]] | None = None

    def load(self) -> list[dict[str, object]]:
        return []

    def save(self, records: list[dict[str, object]]) -> None:
        self.saved_records = records

    def upsert(self, record: dict[str, object]) -> None:
        pass


class FakeVectorStore:
    def __init__(self) -> None:
        self.added_chunks = 0

        class Collection:
            @staticmethod
            def count() -> int:
                return 1

        self.collection = Collection()

    def reset_collection(self) -> None:
        pass

    def add_chunks(self, chunks: list[object]) -> int:
        self.added_chunks += len(chunks)
        return len(chunks)


def test_rebuild_index_recovers_registry_from_raw(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    processed_dir.mkdir()

    document_id = "doc-123"
    raw_file = raw_dir / f"{document_id}.md"
    raw_file.write_text("1. Overview\n\nSupports SNMP and SSH.", encoding="utf-8")
    (processed_dir / f"{document_id}.txt").write_text(
        "Source: 企业手册.md\nDocument ID: doc-123\n\nSupports SNMP and SSH.",
        encoding="utf-8",
    )

    service = IngestService()
    service.settings.raw_data_dir = str(raw_dir)
    service.settings.processed_data_dir = str(processed_dir)
    service.registry = FakeRegistry()
    service._vector_store = FakeVectorStore()

    response = service.rebuild_index()

    assert response.documents_processed == 1
    assert service.registry.saved_records is not None
    assert service.registry.saved_records[0]["source_name"] == "企业手册.md"
