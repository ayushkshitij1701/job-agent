import pytest

from job_agent.llm import PROVIDERS, make_client
from job_agent.llm import base
from job_agent.llm.gemini import GeminiLLM
from job_agent.llm.ollama import OllamaLLM
from tests.conftest import StubResponse

SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "integer"}, "tags": {"type": "array", "items": {"type": "string"}}},
    "required": ["score", "tags"],
    "additionalProperties": False,
}


def gemini_reply(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def ollama_reply(text):
    return {"message": {"role": "assistant", "content": text}}


# ---- Gemini ---------------------------------------------------------------

def test_gemini_request_shape_and_parsing(stub_session):
    session = stub_session([gemini_reply('{"score": 7, "tags": ["a"]}')])
    llm = GeminiLLM(model="gemini-2.5-flash", api_key="k-123", session=session)
    out = llm.ask_json(system="be strict", user="rate this", schema=SCHEMA)
    assert out == {"score": 7, "tags": ["a"]}
    call = session.calls[0]
    assert call["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    assert call["headers"]["x-goog-api-key"] == "k-123"
    assert "k-123" not in call["url"]
    body = call["json"]
    assert body["system_instruction"]["parts"] == [{"text": "be strict"}]
    assert body["contents"] == [{"role": "user", "parts": [{"text": "rate this"}]}]
    gen = body["generationConfig"]
    assert gen["responseMimeType"] == "application/json"
    assert gen["responseSchema"]["required"] == ["score", "tags"]
    assert "additionalProperties" not in gen["responseSchema"]       # Gemini rejects that keyword


def test_gemini_from_config_reads_key_from_env(monkeypatch, stub_session):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    llm = GeminiLLM.from_config({"model": "gemini-2.5-flash"}, stub_session([]))
    assert llm.api_key == "env-key"
    assert llm.model == "gemini-2.5-flash"


# ---- Ollama ---------------------------------------------------------------

def test_ollama_request_shape_and_parsing(stub_session):
    session = stub_session([ollama_reply('{"score": 3, "tags": []}')])
    llm = OllamaLLM(model="qwen3:8b", url="http://localhost:11434", session=session)
    out = llm.ask_json(system="sys", user="usr", schema=SCHEMA)
    assert out == {"score": 3, "tags": []}
    call = session.calls[0]
    assert call["url"] == "http://localhost:11434/api/chat"
    body = call["json"]
    assert body["model"] == "qwen3:8b"
    assert body["stream"] is False
    assert body["format"] == SCHEMA
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert body["options"]["num_ctx"] >= 8192
    assert body["think"] is False          # default: no reasoning chain, ~12x faster, same scores


def test_ollama_from_config_defaults(stub_session):
    llm = OllamaLLM.from_config({"model": "qwen3:8b"}, stub_session([]))
    assert llm.url == "http://localhost:11434"
    assert llm.think is False


def test_ollama_think_from_config(stub_session):
    session = stub_session([ollama_reply("{}")])
    llm = OllamaLLM.from_config({"model": "qwen3:8b", "think": True}, session)
    llm.ask_json(system="sys", user="usr", schema=SCHEMA)
    assert session.calls[0]["json"]["think"] is True


# ---- Shared plumbing --------------------------------------------------------

def test_retries_on_429_then_succeeds(monkeypatch, stub_session):
    sleeps = []
    monkeypatch.setattr(base.time, "sleep", sleeps.append)
    session = stub_session([StubResponse({}, status=429, headers={"Retry-After": "7"}),
                            ollama_reply('{"score": 1, "tags": []}')])
    llm = OllamaLLM(model="m", url="http://x", session=session)
    assert llm.ask_json(system="s", user="u", schema=SCHEMA)["score"] == 1
    assert sleeps == [7.0]
    assert len(session.calls) == 2


def test_gives_up_after_retries(monkeypatch, stub_session):
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    session = stub_session([StubResponse({}, status=503)] * (base.RETRIES + 1))
    llm = OllamaLLM(model="m", url="http://x", session=session)
    with pytest.raises(Exception):
        llm.ask_json(system="s", user="u", schema=SCHEMA)
    assert len(session.calls) == base.RETRIES + 1


# ---- Registry -------------------------------------------------------------

def test_make_client_picks_provider_from_config(monkeypatch, stub_session):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    cfg = {"provider": "gemini", "gemini": {"model": "gemini-2.5-flash"}, "ollama": {"model": "qwen3:8b"}}
    assert isinstance(make_client(cfg, stub_session([])), GeminiLLM)
    cfg["provider"] = "ollama"
    assert isinstance(make_client(cfg, stub_session([])), OllamaLLM)


def test_make_client_rejects_unknown_provider(stub_session):
    with pytest.raises(ValueError, match="openai"):
        make_client({"provider": "openai"}, stub_session([]))
    assert set(PROVIDERS) == {"gemini", "ollama"}
