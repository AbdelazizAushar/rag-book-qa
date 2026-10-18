"""Answer-generation tests with a fake retriever and a fake LLM client.

No network, no index and no API key needed.
"""
from types import SimpleNamespace

import httpx
import openai
import pytest

import ragbook.generate.answer as A


class FakeRetriever:
    chunks = []

    def __init__(self, index_dir):
        pass

    def search(self, query, top_k=5):
        return [dict(c) for c in FakeRetriever.chunks][:top_k]


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def chunk(page, score, images=()):
    return {"page": page, "score": score, "text": f"text {page}",
            "heading": "h", "images": list(images)}


def reply(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def http_error(cls, status):
    response = httpx.Response(status, request=httpx.Request("POST", "http://test"))
    return cls("error", response=response, body=None)


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "some/model")
    monkeypatch.setattr(A, "Retriever", FakeRetriever)
    monkeypatch.setattr(A.time, "sleep", lambda seconds: None)


def make(outcomes, chunks):
    FakeRetriever.chunks = chunks
    generator = A.AnswerGenerator("unused", page_offset=2)
    generator.client = FakeClient(outcomes)
    return generator


def test_gate_refusal_keeps_chunks_and_never_calls_llm():
    g = make([], [chunk(100, 1.8)])
    r = g.generate_answer("Who won the World Cup?")
    assert r["status"] == "refused_by_gate"
    assert r["chunks"] and g.client.calls == 0


def test_answer_has_printed_pages_and_deduplicated_images():
    g = make([reply("An array is a list (Page 107).")],
             [chunk(109, 0.7, ["images/a.jpg"]),
              chunk(109, 0.8, ["images/a.jpg", "images/b.jpg"]),
              chunk(108, 0.9)])
    r = g.generate_answer("What is an array?")
    assert r["status"] == "answered"
    assert r["sources"] == [106, 107]
    assert r["images"] == ["images/a.jpg", "images/b.jpg"]
    assert r["chunks"][0]["printed_page"] == 107


def test_model_refusal_is_detected():
    g = make([reply(A.NOT_FOUND_ANSWER + " But high-level is easier (Page 110).")],
             [chunk(112, 0.9)])
    assert g.generate_answer("Best language?")["status"] == "refused_by_model"


def test_rate_limit_is_retried():
    g = make([http_error(openai.RateLimitError, 429), reply("ok")], [chunk(109, 0.7)])
    r = g.generate_answer("q")
    assert r["status"] == "answered" and g.client.calls == 2


def test_bad_key_is_not_retried_and_message_is_clear():
    g = make([http_error(openai.AuthenticationError, 401)], [chunk(109, 0.7)])
    r = g.generate_answer("q")
    assert r["status"] == "error" and g.client.calls == 1
    assert "OPENROUTER_API_KEY" in r["answer"] and r["chunks"]


def test_rate_limit_exhausted_gives_friendly_message():
    g = make([http_error(openai.RateLimitError, 429)] * 3, [chunk(109, 0.7)])
    r = g.generate_answer("q")
    assert r["status"] == "error" and g.client.calls == 3 and "busy" in r["answer"]


def test_empty_response_is_retried():
    g = make([SimpleNamespace(choices=[]), reply("fine")], [chunk(109, 0.7)])
    assert g.generate_answer("q")["status"] == "answered"


def test_missing_model_setting_is_reported(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL")
    with pytest.raises(RuntimeError, match="OPENROUTER_MODEL"):
        A.AnswerGenerator("unused")


def test_retrieval_failure_is_reported():
    g = make([], [])
    g.retriever.search = lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("no index"))
    assert g.generate_answer("q")["status"] == "error"