"""
test_review.py
===============
Integration tests for the /api/review endpoint.

We mock the LLM provider so tests:
    - Run instantly (no network call, no local Ollama needed).
    - Are deterministic (same input always produces the same assertions).
    - Still exercise the full FastAPI request/response cycle, validation,
      and JSON-parsing logic in `code_analyzer.py`.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import code_analyzer

client = TestClient(app)

_FAKE_LLM_JSON_RESPONSE = json.dumps(
    {
        "summary": "The function works but has a minor style issue.",
        "findings": [
            {
                "line": 2,
                "category": "best_practice",
                "severity": "low",
                "title": "Missing docstring",
                "explanation": "Public functions should document their purpose.",
                "suggestion": "Add a one-line docstring.",
            }
        ],
    }
)


class _FakeProvider:
    """A stand-in LLM provider that returns a fixed, valid JSON response."""

    async def generate(self, prompt: str, timeout_seconds: int) -> str:  # noqa: D401
        return _FAKE_LLM_JSON_RESPONSE


@pytest.fixture(autouse=True)
def _patch_llm_provider(monkeypatch):
    """Replace the real LLM factory with our fake provider for every test."""
    monkeypatch.setattr(code_analyzer, "get_llm_provider", lambda settings: _FakeProvider())


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_review_valid_python_code():
    payload = {"code": "def add(a, b):\n    return a + b\n", "language": "python"}
    response = client.post("/api/review", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["language_detected"] == "python"
    assert body["summary"]
    assert isinstance(body["findings"], list)
    assert 0 <= body["overall_score"] <= 100


def test_review_rejects_empty_code():
    response = client.post("/api/review", json={"code": "   "})
    assert response.status_code == 422  # Pydantic validation error


def test_review_rejects_oversized_submission(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "MAX_CODE_LENGTH_CHARS", 10)
    response = client.post("/api/review", json={"code": "x" * 100, "language": "python"})
    assert response.status_code == 413
