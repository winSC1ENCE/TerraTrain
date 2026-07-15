"""Smoke test for Ollama connectivity, model availability, and embeddings."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps/backend/src"))

import httpx
from terratrain.config import get_settings


async def smoke_test() -> None:
    settings = get_settings()
    base = settings.ollama_base_url
    chat_model = settings.ollama_chat_model
    embed_model = settings.ollama_embed_model

    print(f"Ollama URL: {base}")
    print(f"Chat model: {chat_model}")
    print(f"Embed model: {embed_model}")
    print()

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Check server reachable
        try:
            resp = await client.get(f"{base}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            print(f"Available models: {models}")
        except Exception as exc:
            print(f"ERROR: Cannot reach Ollama at {base}: {exc}")
            sys.exit(1)

        # 2. Check chat model
        if not any(chat_model in m for m in models):
            print(f"WARNING: {chat_model} not found — run 'make pull-models-gpu'")
        else:
            print(f"OK: {chat_model} is available")

        # 3. Check embed model
        if not any(embed_model in m for m in models):
            print(f"WARNING: {embed_model} not found — run 'make pull-models-gpu'")
        else:
            print(f"OK: {embed_model} is available")

        # 4. Test embedding
        print("\nTesting embedding...")
        try:
            resp = await client.post(
                f"{base}/api/embeddings",
                json={"model": embed_model, "prompt": "VO2 max interval training"},
            )
            resp.raise_for_status()
            vec = resp.json()["embedding"]
            print(f"OK: Embedding vector length = {len(vec)}")
        except Exception as exc:
            print(f"ERROR: Embedding failed: {exc}")

        # 5. Test chat
        print("\nTesting chat (one-shot)...")
        try:
            resp = await client.post(
                f"{base}/api/chat",
                json={
                    "model": chat_model,
                    "stream": False,
                    "messages": [
                        {"role": "user", "content": "Reply with exactly: TERRATRAIN_OK"}
                    ],
                    "options": {"temperature": 0},
                },
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            print(f"OK: Chat response = {content!r}")
        except Exception as exc:
            print(f"ERROR: Chat failed: {exc}")


if __name__ == "__main__":
    asyncio.run(smoke_test())
