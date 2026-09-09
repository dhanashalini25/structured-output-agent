import pytest
from pydantic import BaseModel

from src import agent
from src.agent import MAX_ATTEMPTS, Ticket, coerce_json, extract


class Tiny(BaseModel):
    name: str
    n: int


def test_coerce_strips_code_fence():
    raw = 'Here you go:\n```json\n{"name": "x", "n": 1}\n```'
    assert coerce_json(raw) == '{"name": "x", "n": 1}'


def test_coerce_strips_prose():
    assert coerce_json('Sure! {"name": "x", "n": 1} Hope that helps!') == '{"name": "x", "n": 1}'


def test_coerce_raises_without_json():
    with pytest.raises(ValueError):
        coerce_json("I'd rather not.")


def test_schema_rejects_bad_priority():
    with pytest.raises(Exception):
        Ticket(title="Fix login", priority="urgent", estimate_hours=1)


def test_valid_on_first_attempt(monkeypatch):
    monkeypatch.setattr(agent, "complete", lambda m, **k: '{"name": "ok", "n": 2}')
    assert extract("x", Tiny).name == "ok"


def test_repair_loop_recovers(monkeypatch):
    replies = iter(['{"name": "bad"}', '{"name": "good", "n": 7}'])
    monkeypatch.setattr(agent, "complete", lambda m, **k: next(replies))
    obj = extract("x", Tiny)
    assert obj.n == 7


def test_error_is_fed_back_to_the_model(monkeypatch):
    seen = []

    def fake(messages, **kwargs):
        seen.append(messages[-1]["content"])
        return '{"name": "good", "n": 1}' if len(seen) > 1 else "{}"

    monkeypatch.setattr(agent, "complete", fake)
    extract("x", Tiny)
    assert "failed validation" in seen[-1]


def test_exhausted_attempts_raise(monkeypatch):
    monkeypatch.setattr(agent, "complete", lambda m, **k: "nonsense")
    with pytest.raises(RuntimeError):
        extract("x", Tiny)


def test_soft_fail_returns_partial(monkeypatch):
    monkeypatch.setattr(agent, "complete", lambda m, **k: '{"name": "half"}')
    obj = extract("x", Ticket, strict=False)
    assert obj.confidence == 0.0


def test_attempt_cap_respected(monkeypatch):
    calls = []
    monkeypatch.setattr(agent, "complete", lambda m, **k: calls.append(1) or "junk")
    with pytest.raises(RuntimeError):
        extract("x", Tiny)
    assert len(calls) == MAX_ATTEMPTS
