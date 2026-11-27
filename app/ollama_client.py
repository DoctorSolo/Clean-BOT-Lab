"""Cliente HTTP local; não depende do SDK Ollama."""
from __future__ import annotations
import os
import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


async def available_models():
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            res = await client.get(f"{OLLAMA_URL}/api/tags")
            res.raise_for_status()
            names = [m["name"] for m in res.json().get("models", []) if m.get("name")]
            return {"connected": True, "models": names}
    except (httpx.HTTPError, KeyError, ValueError):
        return {"connected": False, "models": []}


async def chat_details(model: str, messages: list[dict], as_json: bool = False):
    payload = {"model": model, "messages": messages, "stream": False,
               "options": {"temperature": 0.2, "num_predict": 1024}}
    if as_json:
        payload["format"] = "json"
        payload["options"]["num_predict"] = 1024
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=8.0)) as client:
            res = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()
            answer = data["message"]["content"].strip()
            if not answer:
                raise RuntimeError(f"O modelo {model} devolveu uma resposta vazia. Experimente outro modelo ou aumente o limite de geração no cliente.")
            tokens = data.get("eval_count")
            duration = data.get("eval_duration")
            return {"answer": answer, "eval_count": tokens,
                    "tokens_per_second": round(tokens / (duration / 1e9), 1) if tokens and duration else None,
                    "load_ms": round(data["load_duration"] / 1e6) if data.get("load_duration") is not None else None,
                    "done_reason": data.get("done_reason") }
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise RuntimeError(f"Não foi possível gerar resposta no Ollama ({model}): {exc}") from exc


async def chat(model: str, messages: list[dict], as_json: bool = False):
    return (await chat_details(model, messages, as_json))["answer"]


async def embed(model: str, text: str) -> list[float]:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=8.0)) as client:
            res = await client.post(f"{OLLAMA_URL}/api/embed", json={"model": model, "input": text})
            res.raise_for_status()
            return res.json()["embeddings"][0]
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        raise RuntimeError(f"Embeddings indisponíveis ({model}): {exc}") from exc
