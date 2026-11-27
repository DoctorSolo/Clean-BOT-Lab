"""Memória persistente (SQLite) e memória de trabalho volátil por sessão."""
from __future__ import annotations
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("MEMORY_LAB_DATA", str(BASE_DIR / "data")))
DB_PATH = DATA_DIR / "memories.sqlite3"
TYPES = ("working", "semantic", "episodic", "procedural")
PERSISTENT = ("semantic", "episodic", "procedural")
WORKING: dict[str, list[dict]] = {}
SESSIONS: dict[str, list[dict]] = {}
LOCK = threading.RLock()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS memories (
           id TEXT PRIMARY KEY, type TEXT NOT NULL, content TEXT NOT NULL,
           source TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
           embedding TEXT, embedding_model TEXT
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(type)")


def from_row(row):
    d = dict(row)
    d.pop("embedding", None)
    d.pop("embedding_model", None)
    d["temporary"] = False
    return d


def list_memories(session_id: str, memory_type: str | None = None, query: str = ""):
    with LOCK:
        work = list(WORKING.get(session_id, []))
    with connect() as c:
        rows = c.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()
    all_items = [dict(m) for m in work] + [from_row(r) for r in rows]
    if memory_type and memory_type != "all":
        all_items = [m for m in all_items if m["type"] == memory_type]
    if query.strip():
        q = query.strip().casefold()
        all_items = [m for m in all_items if q in m["content"].casefold()]
    return all_items


def raw_persistent():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()]


def insert_memory(session_id: str, kind: str, content: str, source: str = "manual"):
    if kind not in TYPES:
        raise ValueError("Tipo inválido")
    content = content.strip()
    if not content or len(content) > 1200:
        raise ValueError("Memória deve ter de 1 a 1200 caracteres")
    now = utcnow()
    record = dict(id=uuid4().hex[:12], type=kind, content=content, source=source,
                  created_at=now, updated_at=now, temporary=(kind == "working"))
    with LOCK:
        items = list_memories(session_id)
        # Prevent duplicates of same type and content in current visibility scope
        for existing in items:
            if existing["type"] == kind and existing["content"].casefold() == content.casefold():
                return existing, False
        if kind == "working":
            WORKING.setdefault(session_id, []).insert(0, record)
        else:
            with connect() as c:
                c.execute("INSERT INTO memories (id,type,content,source,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                          (record["id"], kind, content, source, now, now))
        return record, True


def update_memory(session_id: str, memory_id: str, content: str):
    content = content.strip()
    if not content or len(content) > 1200:
        raise ValueError("Memória deve ter de 1 a 1200 caracteres")
    with LOCK:
        for m in WORKING.get(session_id, []):
            if m["id"] == memory_id:
                m["content"] = content
                m["updated_at"] = utcnow()
                return m
        with connect() as c:
            exists = c.execute("SELECT id FROM memories WHERE id=?", (memory_id,)).fetchone()
            if exists:
                c.execute("UPDATE memories SET content=?,updated_at=?,embedding=NULL,embedding_model=NULL WHERE id=?",
                          (content, utcnow(), memory_id))
                row = c.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
                return from_row(row)
    return None


def delete_memory(session_id: str, memory_id: str):
    with LOCK:
        work = WORKING.get(session_id, [])
        for i, m in enumerate(work):
            if m["id"] == memory_id:
                del work[i]
                return True
        with connect() as c:
            cur = c.execute("DELETE FROM memories WHERE id=?", (memory_id,))
            return cur.rowcount > 0


def wipe_persistent():
    with connect() as c:
        c.execute("DELETE FROM memories")


def clear_session(session_id: str):
    with LOCK:
        WORKING.pop(session_id, None)
        SESSIONS.pop(session_id, None)


def session_history(session_id: str):
    with LOCK:
        return list(SESSIONS.get(session_id, []))


def append_exchange(session_id: str, user_text: str, assistant_text: str):
    with LOCK:
        history = SESSIONS.setdefault(session_id, [])
        history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": assistant_text}]
        if len(history) > 16:
            SESSIONS[session_id] = history[-16:]


def set_embedding(memory_id: str, values: list[float], model: str):
    with connect() as c:
        c.execute("UPDATE memories SET embedding=?,embedding_model=? WHERE id=?",
                  (json.dumps(values), model, memory_id))
