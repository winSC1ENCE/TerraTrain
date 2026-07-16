"""RAG retrieval service using pgvector + Ollama embeddings."""

from __future__ import annotations

import httpx
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception

from terratrain.config import get_settings

logger = structlog.get_logger()


def _is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.RequestError)


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

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(min=1, max=10),
        retry=retry_if_exception(_is_retryable_exception),
        reraise=True,
    )
    async def _embed(self, text_: str) -> list[float]:
        settings = self._settings
        provider = settings.resolved_embedding_provider

        if provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is not set. Please set it in your .env file.")

            headers = {
                "Authorization": f"Bearer {settings.gemini_api_key}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.gemini_api_base}/embeddings",
                    headers=headers,
                    json={
                        "model": settings.gemini_embed_model,
                        "input": text_,
                        "dimensions": 768,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["data"][0]["embedding"]
        else:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": settings.ollama_embed_model, "prompt": text_},
                )
                resp.raise_for_status()
                data = resp.json()
                return data["embedding"]
