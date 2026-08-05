"""Unit tests for Gemini Integration."""

import json
from unittest.mock import AsyncMock

import pytest
import respx
from terratrain.config import Settings
from terratrain.ingestion.pdf_ingestor import PdfIngestor
from terratrain.services.coaching_agent import CoachingAgent
from terratrain.services.rag_service import RagService


def test_settings_provider_resolution():
    # 1. Default settings (no api key)
    settings = Settings(gemini_api_key="", llm_provider="ollama", embedding_provider="ollama")
    assert settings.resolved_llm_provider == "ollama"
    assert settings.resolved_embedding_provider == "ollama"

    # 2. Key set, provider remains default (ollama) -> Auto-switch to gemini
    settings = Settings(
        gemini_api_key="test_key", llm_provider="ollama", embedding_provider="ollama"
    )
    assert settings.resolved_llm_provider == "gemini"
    assert settings.resolved_embedding_provider == "gemini"

    # 3. Key set, provider explicitly set to ollama -> Keep ollama
    settings = Settings(
        gemini_api_key="test_key", llm_provider="ollama", embedding_provider="ollama"
    )
    settings.llm_provider = "ollama"
    settings.embedding_provider = "ollama"
    # The property checks if llm_provider == "ollama" and gemini_api_key is set
    # to automatically switch.
    # If they want Ollama even with a key, they can just unset LLM_PROVIDER
    # or set it to something else, or we can support that.
    # Currently: keys exist -> auto-switch.
    assert settings.resolved_llm_provider == "gemini"


@respx.mock
@pytest.mark.asyncio
async def test_rag_service_embed_gemini(monkeypatch):
    # Setup settings to use gemini
    settings = Settings(
        gemini_api_key="test_key", llm_provider="gemini", embedding_provider="gemini"
    )
    monkeypatch.setattr("terratrain.services.rag_service.get_settings", lambda: settings)

    session = AsyncMock()
    rag = RagService(session=session)

    # Mock the Gemini embedding HTTP request
    mock_route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/openai/embeddings"
    ).respond(json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})

    emb = await rag._embed("test query")
    assert emb == [0.1, 0.2, 0.3]
    assert mock_route.called

    # Check headers and payload
    req = mock_route.calls.last.request
    assert req.headers["authorization"] == "Bearer test_key"
    payload = json.loads(req.read())
    assert payload["model"] == "text-embedding-004"
    assert payload["input"] == "test query"
    assert payload["dimensions"] == 768


@respx.mock
@pytest.mark.asyncio
async def test_pdf_ingestor_embed_batch_gemini(monkeypatch):
    settings = Settings(
        gemini_api_key="test_key", llm_provider="gemini", embedding_provider="gemini"
    )
    monkeypatch.setattr("terratrain.ingestion.pdf_ingestor.get_settings", lambda: settings)

    session = AsyncMock()
    ingestor = PdfIngestor(session=session)

    mock_route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/openai/embeddings"
    ).respond(json={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]})

    embs = await ingestor._embed_batch(["chunk1", "chunk2"])
    assert embs == [[0.1, 0.2], [0.3, 0.4]]
    assert mock_route.called

    payload = json.loads(mock_route.calls.last.request.read())
    assert payload["input"] == ["chunk1", "chunk2"]
    assert payload["model"] == "text-embedding-004"
    assert payload["dimensions"] == 768


@respx.mock
@pytest.mark.asyncio
async def test_coaching_agent_call_gemini(monkeypatch):
    settings = Settings(
        gemini_api_key="test_key", llm_provider="gemini", embedding_provider="gemini"
    )
    monkeypatch.setattr("terratrain.services.coaching_agent.get_settings", lambda: settings)

    session = AsyncMock()
    agent = CoachingAgent(session=session)

    # Mock the Gemini chat completions HTTP request
    mock_route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    ).respond(
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Thinking...",
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "final_answer",
                                    "arguments": '{"name": "Gemini plan"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )

    response = await agent._call_llm(
        messages=[{"role": "user", "content": "Hello"}], provider="gemini"
    )
    assert mock_route.called

    # Assert conversion to Ollama-compatible structure
    msg = response["message"]
    assert msg["role"] == "assistant"
    assert msg["content"] == "Thinking..."
    assert len(msg["tool_calls"]) == 1
    assert msg["tool_calls"][0]["id"] == "call_abc"
    assert msg["tool_calls"][0]["function"]["name"] == "final_answer"
    assert msg["tool_calls"][0]["function"]["arguments"] == {"name": "Gemini plan"}
