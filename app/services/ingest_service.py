from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.core.logging import get_logger
from app.models.schemas import IngestResponse
from app.rag.chunker import TextChunker
from app.rag.loader import DocumentLoader
from app.rag.vector_store import ChromaVectorStore


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
        self._vector_store: ChromaVectorStore | None = None

    @property
    def vector_store(self) -> ChromaVectorStore:
        if self._vector_store is None:
            self._vector_store = ChromaVectorStore()
        return self._vector_store

    async def ingest_upload(self, upload_file: UploadFile) -> IngestResponse:
        if not upload_file.filename:
            raise BadRequestError("Uploaded file must have a filename.")

        document_id = f"doc-{uuid4().hex[:12]}"
        self.logger.info("Starting ingest for file '%s' as document '%s'.", upload_file.filename, document_id)
        raw_path = await self._save_upload(upload_file=upload_file, document_id=document_id)
        return await run_in_threadpool(
            self._process_saved_upload,
            raw_path,
            document_id,
            upload_file.filename,
        )

    def _process_saved_upload(self, raw_path: Path, document_id: str, source_name: str) -> IngestResponse:
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

        return IngestResponse(
            status="success",
            message=f"Indexed {indexed_count} chunks from '{source_name}'.",
            document_id=document_id,
            chunks_indexed=indexed_count,
            source_path=str(processed_path),
        )

    async def _save_upload(self, upload_file: UploadFile, document_id: str) -> Path:
        raw_dir = Path(self.settings.raw_data_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(upload_file.filename or "").suffix.lower()
        target_path = raw_dir / f"{document_id}{suffix}"
        file_bytes = await upload_file.read()
        target_path.write_bytes(file_bytes)
        return target_path

    def _save_processed_text(self, document_id: str, source_name: str, text: str) -> Path:
        processed_dir = Path(self.settings.processed_data_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)

        processed_path = processed_dir / f"{document_id}.txt"
        header = f"Source: {source_name}\nDocument ID: {document_id}\n\n"
        processed_path.write_text(header + text, encoding="utf-8")
        return processed_path
