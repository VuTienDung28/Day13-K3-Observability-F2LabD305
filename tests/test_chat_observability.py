from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient

from app import logging_config
from app.main import agent, app, handle_unexpected_error


CHAT_PAYLOAD = {
    "user_id": "student-01",
    "session_id": "session-01",
    "feature": "qa",
    "message": "Explain observability",
}


def test_chat_generates_and_returns_correlation_id() -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json=CHAT_PAYLOAD)

    correlation_id = response.json()["correlation_id"]
    assert correlation_id.startswith("req-")
    assert len(correlation_id) == 12
    assert response.headers["x-request-id"] == correlation_id
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_chat_propagates_valid_request_id() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "upstream-request-42"},
            json=CHAT_PAYLOAD,
        )

    assert response.json()["correlation_id"] == "upstream-request-42"
    assert response.headers["x-request-id"] == "upstream-request-42"


def test_chat_replaces_unsafe_request_id() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "unsafe request id\nvalue"},
            json=CHAT_PAYLOAD,
        )

    correlation_id = response.json()["correlation_id"]
    assert correlation_id.startswith("req-")
    assert correlation_id != "unsafe request id\nvalue"


def test_chat_does_not_leak_correlation_id_between_requests() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/chat",
            headers={"x-request-id": "upstream-first"},
            json=CHAT_PAYLOAD,
        )
        second = client.post("/chat", json=CHAT_PAYLOAD)

    assert first.json()["correlation_id"] == "upstream-first"
    assert second.json()["correlation_id"].startswith("req-")
    assert second.json()["correlation_id"] != "upstream-first"


def test_chat_logs_required_request_metadata(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "upstream-metadata"},
            json=CHAT_PAYLOAD,
        )

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    request_event = next(event for event in events if event["event"] == "request_received")
    assert request_event["correlation_id"] == "upstream-metadata"
    assert request_event["user_id_hash"] != CHAT_PAYLOAD["user_id"]
    assert request_event["session_id"] == CHAT_PAYLOAD["session_id"]
    assert request_event["feature"] == CHAT_PAYLOAD["feature"]
    assert request_event["model"] == agent.model
    assert request_event["env"] == "dev"


def test_chat_failure_returns_and_logs_correlation_id(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    def fail(**_):
        raise RuntimeError("provider failed")

    monkeypatch.setattr(agent, "run", fail)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "upstream-failure"},
            json=CHAT_PAYLOAD,
        )

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "upstream-failure"
    assert float(response.headers["x-response-time-ms"]) >= 0
    assert response.json() == {
        "detail": "RuntimeError",
        "correlation_id": "upstream-failure",
    }
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    failure_event = next(event for event in events if event["event"] == "request_failed")
    assert failure_event["correlation_id"] == "upstream-failure"
    assert failure_event["user_id_hash"] != CHAT_PAYLOAD["user_id"]
    assert failure_event["session_id"] == CHAT_PAYLOAD["session_id"]
    assert failure_event["feature"] == CHAT_PAYLOAD["feature"]
    assert failure_event["model"] == agent.model
    assert failure_event["env"] == "dev"
    assert failure_event["error_type"] == "RuntimeError"


def test_global_exception_handler_handles_non_chat_request(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/unexpected",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )
    request.state.correlation_id = "upstream-global"
    request.state.request_started_at = time.perf_counter()

    response = asyncio.run(handle_unexpected_error(request, RuntimeError("failed")))

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "upstream-global"


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "user_id": "student-01",
                "session_id": "session-01",
                "feature": "qa",
                "message": "Explain observability",
            },
        )

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
