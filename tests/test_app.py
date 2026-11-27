"""Testes rápidos, sem Ollama e sem conexão externa."""
import pytest
from fastapi.testclient import TestClient
from app import main, storage, memory

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "memories.sqlite3")
    storage.WORKING.clear();storage.SESSIONS.clear()
    with TestClient(main.app) as c:
        yield c

SID = "session_test_demo"

def body(text, types=(), **kwargs):
    return dict(session_id=SID, text=text, enabled_types=list(types), provider="simulation", **kwargs)

def test_memory_visibility_when_mode_off(client):
    seed=client.post("/api/demo/seed",json={"session_id":SID})
    assert len(seed.json()["created"]) == 5
    without=client.post("/api/chat",json=body("Qual linguagem de programação prefiro?")).json()
    assert without["retrieved"] == []
    assert without["saved"] == []
    assert "não consultei" in without["answer"]
    with_semantic=client.post("/api/chat",json=body("Qual linguagem de programação prefiro?",["semantic"])).json()
    assert any("Python" in m["content"] for m in with_semantic["retrieved"])
    assert with_semantic["trace"]["retrieval"] == "palavras-chave"


def test_session_reset_clears_working_not_persistent(client):
    client.post("/api/memories",json={"session_id":SID,"type":"working","content":"Meu objetivo de trabalho atual é preparar uma palestra"})
    client.post("/api/memories",json={"session_id":SID,"type":"semantic","content":"Prefiro estudar Python"})
    assert len(client.get("/api/memories",params={"session_id":SID}).json()["memories"]) == 2
    client.post("/api/session/reset",json={"session_id":SID})
    remaining=client.get("/api/memories",params={"session_id":SID}).json()["memories"]
    assert len(remaining) == 1 and remaining[0]["type"] == "semantic"


def test_crud_and_no_duplicate(client):
    data={"session_id":SID,"type":"procedural","content":"Primeiro teste, depois faça o deploy"}
    first=client.post("/api/memories",json=data).json()
    second=client.post("/api/memories",json=data).json()
    assert first["created"] is True and second["created"] is False
    key=first["memory"]["id"]
    updated=client.patch(f"/api/memories/{key}",json={"session_id":SID,"content":"Primeiro rode os testes, depois o deploy"})
    assert "rode os testes" in updated.json()["memory"]["content"]
    assert client.delete(f"/api/memories/{key}",params={"session_id":SID}).status_code==200
    assert len(client.get("/api/memories",params={"session_id":SID}).json()["memories"]) == 0


def test_compare_does_not_write_and_has_two_outputs(client):
    client.post("/api/demo/seed",json={"session_id":SID})
    count=len(client.get("/api/memories",params={"session_id":SID}).json()["memories"])
    result=client.post("/api/compare",json=body("Qual linguagem de programação eu prefiro?",["semantic"])).json()
    assert "não consultei" in result["without"]
    assert "Python" in result["with_memory"]
    assert result["retrieved"]
    assert count == len(client.get("/api/memories",params={"session_id":SID}).json()["memories"])


def test_simulation_capture_respects_module(client):
    payload=body("Eu prefiro Python para meus exemplos.",["working"],auto_capture=True)
    result=client.post("/api/chat",json=payload).json()
    assert result["saved"] == []
    payload["enabled_types"]=["semantic"]
    result=client.post("/api/chat",json=payload).json()
    assert len(result["saved"])==1 and result["saved"][0]["type"]=="semantic"


def test_lexical_and_model_prompt():
    assert memory.lexical_score("Qual linguagem de programação prefiro?", "O usuário prefere programação em Python") > 0
    messages=memory.build_messages("Oi",[],[])
    assert messages[-1]["role"]=="user" and messages[0]["role"]=="system"


def test_bad_type_is_rejected(client):
    res=client.post("/api/memories",json={"session_id":SID,"type":"none","content":"oi"})
    assert res.status_code==422


def test_real_ollama_http_contract_and_arena(client, monkeypatch):
    import httpx
    import json
    from app import ollama_client
    requests = []
    def handler(req):
        if req.url.path == '/api/tags':
            return httpx.Response(200, json={'models':[{'name':'alpha:1b'},{'name':'beta:2b'}]})
        assert req.url.path == '/api/chat'
        payload = json.loads(req.content)
        requests.append(payload)
        if payload['model']=='missing:1b':
            return httpx.Response(404, json={'error':'model not found'})
        return httpx.Response(200, json={'message':{'content':'Olá do '+payload['model']},'eval_count':20,'eval_duration':2_000_000_000,'load_duration':50_000_000,'done_reason':'stop'})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(ollama_client.httpx,'AsyncClient',lambda **kw: real_client(transport=httpx.MockTransport(handler),**kw))
    assert client.get('/api/status').json()['models'] == ['alpha:1b','beta:2b']
    client.post('/api/demo/seed',json={'session_id':SID})
    prior = client.get('/api/memories',params={'session_id':SID}).json()
    payload = body('Qual linguagem de programação prefiro?', ['semantic'], auto_capture=False)
    payload.update(provider='ollama',model='alpha:1b')
    result = client.post('/api/chat',json=payload).json()
    assert result['answer']=='Olá do alpha:1b' and result['retrieved']
    assert 'Clean BOT' in requests[-1]['messages'][0]['content']
    payload['models']=['alpha:1b','beta:2b','missing:1b']
    result = client.post('/api/compare-models',json=payload).json()
    assert len(result['results'])==3 and 'error' in result['results'][2]
    assert result['results'][0]['tokens_per_second']==10
    assert requests[-3]['messages']==requests[-2]['messages']==requests[-1]['messages']
    assert len(requests[-1]['messages'])==2
    assert 'Python' in requests[-1]['messages'][0]['content']
    assert client.get('/api/memories',params={'session_id':SID}).json()==prior
    payload['enabled_types']=[]
    result = client.post('/api/compare-models',json=payload).json()
    assert result['retrieved']==[] and 'Python' not in requests[-1]['messages'][0]['content']
    payload['models']=['alpha:1b','alpha:1b']
    assert client.post('/api/compare-models',json=payload).status_code==400


def test_avatar_served(client):
    assert client.get('/assets/clean-bot.jpg').headers['content-type']=='image/jpeg'
    assert 'Clean BOT' in client.get('/').text
