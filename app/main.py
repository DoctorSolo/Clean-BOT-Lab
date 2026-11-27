"""API do laboratório de memória modular. Inicie: python -m app.launch"""
from __future__ import annotations
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from . import memory, ollama_client, storage

Kind = Literal["working", "semantic", "episodic", "procedural"]
Provider = Literal["simulation", "ollama"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    yield

app = FastAPI(title="Clean BOT Lab", description="Laboratório visual de memórias para agentes", lifespan=lifespan)
ROOT = Path(__file__).parent / "static"

class SessionModel(BaseModel):
    session_id: str = Field(min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")

class MemoryCreate(SessionModel):
    type: Kind
    content: str = Field(min_length=1, max_length=1200)

class MemoryUpdate(SessionModel):
    content: str = Field(min_length=1, max_length=1200)

class ChatRequest(SessionModel):
    text: str = Field(min_length=1, max_length=1600)
    enabled_types: list[Kind] = Field(default_factory=list, max_length=4)
    provider: Provider = "simulation"
    model: str = Field(default="", max_length=100)
    auto_capture: bool = True
    use_embeddings: bool = False
    embedding_model: str = Field(default="embeddinggemma", max_length=100)

@app.get("/")
async def index():
    return FileResponse(ROOT / "index.html")

@app.get("/assets/styles.css")
async def styles():
    return FileResponse(ROOT / "styles.css", media_type="text/css")

@app.get("/assets/app.js")
async def javascript():
    return FileResponse(ROOT / "app.js", media_type="application/javascript")

@app.get("/assets/clean-bot.jpg")
async def avatar():
    return FileResponse(ROOT / "clean-bot.jpg", media_type="image/jpeg")

@app.get("/api/status")
async def status():
    result = await ollama_client.available_models()
    return {**result, "app": "Clean BOT Lab", "data_path": str(storage.DB_PATH),
            "persistent_count": len(storage.raw_persistent())}

@app.get("/api/memories")
async def memories(session_id: str = Query(min_length=8, max_length=80),
                   type: str = "all", search: str = ""):
    if type not in ("all", *storage.TYPES):
        raise HTTPException(400, "Tipo de memória inválido")
    return {"memories": storage.list_memories(session_id, type, search[:120])}

@app.post("/api/memories")
async def add_memory(payload: MemoryCreate):
    try:
        record, created = storage.insert_memory(payload.session_id, payload.type, payload.content)
        return {"memory": record, "created": created}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.patch("/api/memories/{memory_id}")
async def edit_memory(memory_id: str, payload: MemoryUpdate):
    try:
        result = storage.update_memory(payload.session_id, memory_id, payload.content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not result:
        raise HTTPException(404, "Memória não encontrada")
    return {"memory": result}

@app.delete("/api/memories/{memory_id}")
async def remove_memory(memory_id: str, session_id: str = Query(min_length=8, max_length=80)):
    if not storage.delete_memory(session_id, memory_id):
        raise HTTPException(404, "Memória não encontrada")
    return {"ok": True}

@app.post("/api/session/reset")
async def reset_session(payload: SessionModel):
    storage.clear_session(payload.session_id)
    return {"ok": True}

@app.post("/api/demo/seed")
async def demo_seed(payload: SessionModel):
    examples = [
        ("working", "Objetivo desta sessão: preparar uma demonstração de 1 hora sobre agentes com memória."),
        ("semantic", "O usuário prefere aprender programação com exemplos visuais em Python."),
        ("semantic", "O usuário gosta de explicações práticas e objetivas sobre inteligência artificial."),
        ("episodic", "Em novembro de 2026, o usuário preparou uma palestra sobre agentes de IA usando Python e Ollama."),
        ("procedural", "Para apresentar um projeto: primeiro explique o objetivo, depois execute a demonstração e por fim compare os resultados."),
    ]
    created = []
    for kind, content in examples:
        record, added = storage.insert_memory(payload.session_id, kind, content, source="cenário")
        if added:
            created.append(record)
    return {"created": created, "total": len(examples)}

@app.post("/api/demo/wipe")
async def wipe_all(payload: SessionModel):
    storage.wipe_persistent()
    storage.clear_session(payload.session_id)
    return {"ok": True}

async def get_matches(payload: ChatRequest):
    enabled = list(dict.fromkeys(payload.enabled_types))
    if not enabled:
        return [], "desativada", [], enabled
    matches, method, notices = await memory.retrieve(
        payload.session_id, payload.text, enabled,
        use_embeddings=(payload.use_embeddings and payload.provider == "ollama"),
        embedding_model=payload.embedding_model)
    return matches, method, notices, enabled

async def generate_answer(payload: ChatRequest, matches: list[dict], enabled: list[str], history: list[dict]):
    if payload.provider == "simulation":
        return memory.simulated_answer(payload.text, matches, enabled)
    if not payload.model:
        raise HTTPException(400, "Selecione um modelo Ollama instalado")
    try:
        return await ollama_client.chat(payload.model, memory.build_messages(payload.text, history, matches))
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc

@app.post("/api/chat")
async def chat(payload: ChatRequest):
    started = time.monotonic()
    matches, method, notices, enabled = await get_matches(payload)
    history = storage.session_history(payload.session_id)
    answer = await generate_answer(payload, matches, enabled, history)
    storage.append_exchange(payload.session_id, payload.text, answer)
    saved = []
    if enabled and payload.auto_capture:
        if payload.provider == "ollama":
            candidates, extra_notices = await memory.extract_with_model(payload.model, payload.text, enabled)
            notices += extra_notices
        else:
            candidates = memory.extract_simulated(payload.text, enabled)
        for kind, content in candidates:
            record, created = storage.insert_memory(payload.session_id, kind, content, source="automática" if payload.provider == "ollama" else "regra de simulação")
            if created: saved.append(record)
    return {
        "answer": answer, "retrieved": matches, "saved": saved,
        "trace": {"enabled": enabled, "retrieval": method, "provider": payload.provider,
                  "history_turns": len(history)//2, "elapsed_ms": int((time.monotonic()-started)*1000),
                  "warnings": notices, "auto_capture": bool(enabled and payload.auto_capture)}
    }

@app.post("/api/compare")
async def compare(payload: ChatRequest):
    """Comparação justa: duas respostas novas, sem histórico e sem gravar memórias."""
    started = time.monotonic()
    enabled = list(dict.fromkeys(payload.enabled_types)) or list(storage.TYPES)
    # Compute against an explicitly enabled set (default all if no types selected)
    requested = payload.model_copy(update={"enabled_types": enabled})
    matches, method, notices, enabled = await get_matches(requested)
    plain = await generate_answer(payload, [], [], [])
    enriched = await generate_answer(requested, matches, enabled, [])
    return {"without": plain, "with_memory": enriched, "retrieved": matches,
            "trace": {"retrieval": method, "enabled": enabled, "provider": payload.provider,
                      "elapsed_ms": int((time.monotonic()-started)*1000), "warnings": notices,
                      "note": "Mesmo texto, sem histórico; comparação não grava memórias."}}


class ModelComparison(ChatRequest):
    models: list[str] = Field(min_length=2, max_length=4)

@app.post("/api/compare-models")
async def compare_models(payload: ModelComparison):
    """Same prompt and retrieved context, no history or new memory records."""
    names = list(dict.fromkeys(m.strip() for m in payload.models))
    if len(names) < 2 or any(not m or len(m) > 100 for m in names):
        raise HTTPException(400, "Escolha de 2 a 4 modelos distintos e válidos.")
    if payload.provider != "ollama":
        raise HTTPException(400, "A comparação entre modelos requer Ollama real.")
    # Retrieval once, so all models see the exact same context.
    matches, method, notices, enabled = await get_matches(payload)
    messages = memory.build_messages(payload.text, [], matches)
    results = []
    for name in names:
        started = time.monotonic()
        try:
            result = await ollama_client.chat_details(name, messages)
            results.append({"model": name, **result, "elapsed_ms": round((time.monotonic()-started)*1000)})
        except RuntimeError as exc:
            results.append({"model": name, "error": str(exc), "elapsed_ms": round((time.monotonic()-started)*1000)})
    return {"results": results, "retrieved": matches, "trace": {"enabled": enabled, "retrieval": method, "warnings": notices, "note": "Mesmo prompt e contexto, sem histórico ou novas memórias. Execução sequencial."}}
