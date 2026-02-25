from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import app.main as main
from app.kb import KnowledgeBase


def _test_client_with_temp_kb(tmp_path, monkeypatch):
    temp_kb = KnowledgeBase(storage_path=str(tmp_path / "knowledge.json"))
    monkeypatch.setattr(main, "kb", temp_kb)
    return TestClient(main.app)


def test_health_endpoint(tmp_path, monkeypatch):
    client = _test_client_with_temp_kb(tmp_path, monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "documents": "0"}


def test_upload_txt_knowledge(tmp_path, monkeypatch):
    client = _test_client_with_temp_kb(tmp_path, monkeypatch)

    response = client.post(
        "/knowledge/upload-txt",
        files={"file": ("faq.txt", b"Shipping takes 3-5 business days")},
    )

    assert response.status_code == 200
    assert response.json()["chunks_added"] == 1
    assert response.json()["total_chunks"] == 1


def test_add_url_knowledge(tmp_path, monkeypatch):
    client = _test_client_with_temp_kb(tmp_path, monkeypatch)

    def fake_get(*_args, **_kwargs):
        return SimpleNamespace(
            text="<html><body><h1>FAQ</h1><p>Returns accepted in 30 days.</p></body></html>",
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr(main.requests, "get", fake_get)

    response = client.post("/knowledge/add-url", json={"url": "https://example.com/faq"})

    assert response.status_code == 200
    assert response.json()["chunks_added"] == 1
    assert response.json()["total_chunks"] == 1


def test_webhook_verification_success(tmp_path, monkeypatch):
    client = _test_client_with_temp_kb(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "VERIFY_TOKEN", "secret-token")

    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "secret-token",
            "hub.challenge": "abc123",
        },
    )

    assert response.status_code == 200
    assert response.text == '"abc123"'


def test_webhook_comment_processing(tmp_path, monkeypatch):
    client = _test_client_with_temp_kb(tmp_path, monkeypatch)

    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(main, "generate_reply", lambda _message: "Thanks for commenting!")
    monkeypatch.setattr(
        main,
        "post_comment_reply",
        lambda comment_id, message: calls.append((comment_id, message)),
    )

    payload = {
        "object": "page",
        "entry": [
            {
                "changes": [
                    {
                        "field": "feed",
                        "value": {
                            "item": "comment",
                            "comment_id": "123_456",
                            "message": "How long does shipping take?",
                        },
                    }
                ]
            }
        ],
    }

    response = client.post("/webhook", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert calls == [("123_456", "Thanks for commenting!")]
