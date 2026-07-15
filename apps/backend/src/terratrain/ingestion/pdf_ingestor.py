"""PDF ingestion pipeline: PDF → text chunks → embeddings → pgvector.

Uses LlamaIndex for PDF parsing and chunking, Ollama for embeddings,
then stores chunks in the document_chunks table (pgvector).

Document IDs are derived deterministically from the filename so
re-ingestion is idempotent.
"""

from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.config import get_settings
from terratrain.db.models.document import DocumentChunk

logger = structlog.get_logger()


class PdfIngestor:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()

    async def ingest_path(self, path: Path) -> int:
        """Ingest a PDF file from disk by path."""
        content = path.read_bytes()
        return await self.ingest_bytes(content=content, filename=path.name)

    async def ingest_bytes(self, content: bytes, filename: str) -> int:
        """Ingest PDF bytes. Returns number of chunks created."""
        document_id = self._deterministic_id(filename, content)

        # Delete existing chunks for this document (idempotent re-ingest)
        await self._session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        # Parse PDF
        text = self._extract_text(content)
        chunks = self._chunk_text(text)

        if not chunks:
            logger.warning("pdf_ingestor.no_chunks", filename=filename)
            return 0

        # Embed and store in batches
        batch_size = 16
        total = 0
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start: batch_start + batch_size]
            embeddings = await self._embed_batch(batch)

            for idx, (chunk_text, embedding) in enumerate(
                zip(batch, embeddings), start=batch_start
            ):
                chunk = DocumentChunk(
                    document_id=document_id,
                    document_title=filename.removesuffix(".pdf").replace("_", " "),
                    document_source=filename,
                    chunk_index=idx,
                    content=chunk_text,
                    embedding=embedding,
                    metadata_={"filename": filename, "chunk_index": idx},
                )
                self._session.add(chunk)
            total += len(batch)

        await self._session.commit()
        logger.info("pdf_ingestor.done", filename=filename, chunks=total)
        return total

    def _extract_text(self, content: bytes) -> str:
        try:
            import pdfminer.high_level as pdfminer

            return pdfminer.extract_text(io.BytesIO(content))
        except ImportError:
            pass

        # Fallback: llama-index reader
        try:
            from llama_index.readers.file import PDFReader

            reader = PDFReader()
            docs = reader.load_data(file=io.BytesIO(content))
            return "\n\n".join(d.text for d in docs)
        except Exception as exc:
            logger.error("pdf_ingestor.extract_failed", error=str(exc))
            return ""

    def _chunk_text(self, text: str) -> list[str]:
        settings = self._settings
        size = settings.rag_chunk_size
        overlap = settings.rag_chunk_overlap

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        current_words: list[str] = []

        for para in paragraphs:
            words = para.split()
            current_words.extend(words)

            while len(current_words) >= size:
                chunk = " ".join(current_words[:size])
                chunks.append(chunk)
                current_words = current_words[size - overlap:]

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        settings = self._settings
        embeddings = []
        async with httpx.AsyncClient(timeout=120) as client:
            for text in texts:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": settings.ollama_embed_model, "prompt": text},
                )
                resp.raise_for_status()
                embeddings.append(resp.json()["embedding"])
        return embeddings

    @staticmethod
    def _deterministic_id(filename: str, content: bytes) -> uuid.UUID:
        digest = hashlib.sha256(filename.encode() + content[:1024]).hexdigest()
        return uuid.UUID(digest[:32])
