from __future__ import annotations

from pathlib import Path

import chromadb

from app.core.config import get_settings
from app.rag.chunker import ChunkRecord
from app.rag.embeddings import build_embedding_function


class ChromaVectorStore:
    """Persistent Chroma wrapper for document chunk indexing and search."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_function = build_embedding_function()
        Path(self.settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.settings.chroma_persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.settings.knowledge_collection_name,
            metadata={"domain": "telecom_knowledge_assistant"},
        )

    def add_chunks(self, chunks: list[ChunkRecord]) -> int:
        if not chunks:
            return 0

        embeddings = self.embedding_function([chunk.text for chunk in chunks])
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._sanitize_metadata(chunk.metadata) for chunk in chunks],
            embeddings=embeddings,
        )
        return len(chunks)

    def query(self, query_text: str, top_k: int) -> list[dict[str, object]]:
        if self.collection.count() == 0:
            return []

        query_embeddings = self.embedding_function([query_text])
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        matches: list[dict[str, object]] = []
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            matches.append(
                {
                    "chunk_id": chunk_id,
                    "text": document,
                    "metadata": metadata or {},
                    "distance": float(distance) if distance is not None else None,
                }
            )

        return matches

    def get_all_chunks(self) -> list[dict[str, object]]:
        if self.collection.count() == 0:
            return []

        results = self.collection.get(include=["documents", "metadatas"])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        ids = results.get("ids", [])

        chunks: list[dict[str, object]] = []
        for chunk_id, document, metadata in zip(ids, documents, metadatas):
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": document,
                    "metadata": metadata or {},
                }
            )
        return chunks

    def get_chunks_by_page(self, source_name: str, page: int) -> list[dict[str, object]]:
        return self._filter_chunks(source_name=source_name, page=page)

    def get_chunks_by_element(
        self,
        source_name: str,
        element_type: str,
        page: int | None = None,
    ) -> list[dict[str, object]]:
        return self._filter_chunks(source_name=source_name, page=page, element_type=element_type)

    def _filter_chunks(
        self,
        source_name: str,
        page: int | None = None,
        element_type: str | None = None,
    ) -> list[dict[str, object]]:
        chunks = self.get_all_chunks()
        filtered: list[dict[str, object]] = []

        for chunk in chunks:
            metadata = chunk.get("metadata", {}) or {}
            if str(metadata.get("source_name", "")) != source_name:
                continue
            if page is not None and int(metadata.get("page", -1)) != page:
                continue
            if element_type is not None and str(metadata.get("element_type", "")) != element_type:
                continue
            filtered.append(chunk)

        filtered.sort(key=lambda item: int((item.get("metadata", {}) or {}).get("chunk_index", 0)))
        return filtered

    def _sanitize_metadata(
        self,
        metadata: dict[str, str | int | float | bool],
    ) -> dict[str, str | int | float | bool]:
        sanitized: dict[str, str | int | float | bool] = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized
