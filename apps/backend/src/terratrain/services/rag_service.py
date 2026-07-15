"""RAG retrieval service using pgvector + Ollama embeddings."""

from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.config import get_settings

logger = structlog.get_logger()


class RagService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()

    async def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """Embed query and return top-k similar document chunks.

        Degrades gracefully to an empty list if the embedding model is
        unavailable or no documents have been ingested yet — the coach can
        still produce a workout without RAG grounding.
        """
        k = top_k or self._settings.rag_top_k

        try:
            embedding = await self._embed(query)
        except Exception as exc:
            logger.warning("rag.embed_failed", error=str(exc))
            return []

        try:
            # pgvector cosine similarity search via raw SQL
            result = await self._session.execute(
                text(
                    """
                    SELECT
                        content,
                        document_title,
                        document_source,
                        1 - (embedding <=> CAST(:emb AS vector)) AS score
                    FROM document_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT :k
                    """
                ),
                {"emb": str(embedding), "k": k},
            )
            rows = result.fetchall()
        except Exception as exc:
            logger.warning("rag.query_failed", error=str(exc))
            return []

        return [
            {
                "content": r.content,
                "title": r.document_title,
                "source": r.document_source,
                "score": float(r.score),
            }
            for r in rows
        ]

    async def _embed(self, text_: str) -> list[float]:
        import httpx

        settings = self._settings
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": text_},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]
