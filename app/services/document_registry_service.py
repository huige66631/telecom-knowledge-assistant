from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings


class DocumentRegistryService:
    """Persist lightweight document metadata for dedup and index rebuild."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.registry_path = Path(self.settings.document_registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict[str, object]]:
        if not self.registry_path.exists():
            return []
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def save(self, records: list[dict[str, object]]) -> None:
        self.registry_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def find_by_hash(self, file_hash: str) -> dict[str, object] | None:
        for record in self.load():
            if str(record.get("file_hash", "")) == file_hash:
                return record
        return None

    def upsert(self, record: dict[str, object]) -> None:
        records = self.load()
        file_hash = str(record.get("file_hash", ""))
        updated = False

        for index, existing in enumerate(records):
            if str(existing.get("file_hash", "")) == file_hash:
                records[index] = record
                updated = True
                break

        if not updated:
            records.append(record)

        self.save(records)
