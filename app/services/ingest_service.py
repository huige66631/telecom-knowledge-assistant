from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.core.logging import get_logger
from app.models.schemas import IngestResponse, ReindexResponse
from app.rag.chunker import TextChunker
from app.rag.loader import DocumentLoader, SUPPORTED_EXTENSIONS
from app.rag.vector_store import ChromaVectorStore
from app.services.document_registry_service import DocumentRegistryService


class IngestService:
    """Handle file persistence, parsing, chunking, and vector indexing."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.loader = DocumentLoader()
        self.chunker = TextChunker(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        self.registry = DocumentRegistryService()
        self._vector_store: ChromaVectorStore | None = None

    @property
    def vector_store(self) -> ChromaVectorStore:
        if self._vector_store is None:
            self._vector_store = ChromaVectorStore()
        return self._vector_store

    async def ingest_upload(self, upload_file: UploadFile) -> IngestResponse:
        if not upload_file.filename:
            raise BadRequestError("Uploaded file must have a filename.")

        file_bytes = await upload_file.read()
        file_hash = self._compute_file_hash(file_bytes)
        existing = self.registry.find_by_hash(file_hash)
        if existing:
            return IngestResponse(
                status="skipped",
                message=f"Skipped duplicate file '{upload_file.filename}'. Existing document reused.",
                document_id=str(existing.get("document_id", "")),
                chunks_indexed=0,
                source_path=str(existing.get("processed_path", existing.get("raw_path", ""))),
                duplicate_skipped=True,
                file_hash=file_hash,
            )

        document_id = f"doc-{uuid4().hex[:12]}"
        self.logger.info("Starting ingest for file '%s' as document '%s'.", upload_file.filename, document_id)
        raw_path = await self._save_upload(
            upload_file=upload_file,
            document_id=document_id,
            file_bytes=file_bytes,
        )
        return await run_in_threadpool(
            self._process_saved_upload,
            raw_path,
            document_id,
            upload_file.filename,
            file_hash,
        )

    def _process_saved_upload(self, raw_path: Path, document_id: str, source_name: str, file_hash: str) -> IngestResponse:
        loaded_document = self.loader.load(
            file_path=raw_path,
            document_id=document_id,
            source_name=source_name,
        )

        processed_path = self._save_processed_text(
            document_id=document_id,
            source_name=source_name,
            text=loaded_document.full_text,
        )

        chunks = self.chunker.chunk_document(loaded_document)
        indexed_count = self.vector_store.add_chunks(chunks)
        self.logger.info("Indexed %s chunks for document '%s'.", indexed_count, document_id)

        self.registry.upsert(
            {
                "document_id": document_id,
                "file_hash": file_hash,
                "source_name": source_name,
                "raw_path": str(raw_path),
                "processed_path": str(processed_path),
                "source_type": raw_path.suffix.lower().lstrip("."),
            }
        )

        return IngestResponse(
            status="success",
            message=f"Indexed {indexed_count} chunks from '{source_name}'.",
            document_id=document_id,
            chunks_indexed=indexed_count,
            source_path=str(processed_path),
            duplicate_skipped=False,
            file_hash=file_hash,
        )

    async def _save_upload(self, upload_file: UploadFile, document_id: str, file_bytes: bytes) -> Path:
        raw_dir = Path(self.settings.raw_data_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(upload_file.filename or "").suffix.lower()
        target_path = raw_dir / f"{document_id}{suffix}"
        target_path.write_bytes(file_bytes)
        return target_path

    def _save_processed_text(self, document_id: str, source_name: str, text: str) -> Path:
        processed_dir = Path(self.settings.processed_data_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)

        processed_path = processed_dir / f"{document_id}.txt"
        header = f"Source: {source_name}\nDocument ID: {document_id}\n\n"
        processed_path.write_text(header + text, encoding="utf-8")
        return processed_path

    def rebuild_index(self) -> ReindexResponse:
        records = self.registry.load()
        if not records:
            records = self._recover_registry_from_raw()
            if records:
                self.registry.save(records)
        self.vector_store.reset_collection()

        documents_processed = 0
        chunks_indexed = 0

        for record in records:
            raw_path = Path(str(record.get("raw_path", "")))
            document_id = str(record.get("document_id", ""))
            source_name = str(record.get("source_name", raw_path.name))

            if not raw_path.exists() or not document_id:
                continue

            loaded_document = self.loader.load(
                file_path=raw_path,
                document_id=document_id,
                source_name=source_name,
            )
            processed_path = self._save_processed_text(
                document_id=document_id,
                source_name=source_name,
                text=loaded_document.full_text,
            )
            chunks = self.chunker.chunk_document(loaded_document)
            chunks_indexed += self.vector_store.add_chunks(chunks)
            documents_processed += 1

            updated_record = dict(record)
            updated_record["processed_path"] = str(processed_path)
            self.registry.upsert(updated_record)

        collection_size = self.vector_store.collection.count()
        return ReindexResponse(
            status="success",
            documents_processed=documents_processed,
            chunks_indexed=chunks_indexed,
            collection_size=collection_size,
            message=f"Rebuilt index from {documents_processed} documents.",
        )

    def _compute_file_hash(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def _recover_registry_from_raw(self) -> list[dict[str, object]]:
        raw_dir = Path(self.settings.raw_data_dir)
        if not raw_dir.exists():
            return []

        records: list[dict[str, object]] = []
        seen_hashes: set[str] = set()

        for raw_path in sorted(raw_dir.iterdir()):
            if not raw_path.is_file():
                continue
            if raw_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            file_bytes = raw_path.read_bytes()
            file_hash = self._compute_file_hash(file_bytes)
            if file_hash in seen_hashes:
                continue
            seen_hashes.add(file_hash)

            document_id = raw_path.stem
            source_name = self._recover_source_name(document_id=document_id, raw_path=raw_path)
            processed_path = Path(self.settings.processed_data_dir) / f"{document_id}.txt"
            records.append(
                {
                    "document_id": document_id,
                    "file_hash": file_hash,
                    "source_name": source_name,
                    "raw_path": str(raw_path),
                    "processed_path": str(processed_path),
                    "source_type": raw_path.suffix.lower().lstrip("."),
                }
            )

        return records

    def _recover_source_name(self, document_id: str, raw_path: Path) -> str:
        processed_path = Path(self.settings.processed_data_dir) / f"{document_id}.txt"
        if processed_path.exists():
            try:
                first_line = processed_path.read_text(encoding="utf-8", errors="ignore").splitlines()[0].strip()
            except Exception:
                first_line = ""
            if first_line.startswith("Source:"):
                recovered = first_line.split(":", 1)[1].strip()
                if recovered:
                    return recovered
        return raw_path.name
