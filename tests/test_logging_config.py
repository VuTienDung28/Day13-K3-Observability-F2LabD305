from __future__ import annotations

import json
from pathlib import Path

from app import logging_config


def test_scrub_event_sanitizes_all_values_before_jsonl_write(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    raw_values = [
        "student@vinuni.edu.vn",
        "090 123 4567",
        "001234567890",
        "4111 1111 1111 1111",
        "A1234567",
        "Đường",
    ]
    event = {
        "ts": "2026-08-11T00:00:00Z",
        "event": "Contact student@vinuni.edu.vn",
        "correlation_id": "req-safe-123",
        "service": "api",
        "session_id": "session-090 123 4567",
        "payload": {
            "identity": {
                "cccd": "001234567890",
                "passport": "A1234567",
            },
            "payment": ["4111 1111 1111 1111"],
            "address": "Đường: 123",
        },
    }

    sanitized = logging_config.scrub_event(None, "info", event)
    logging_config.JsonlFileProcessor()(None, "info", sanitized)

    record = json.loads(log_path.read_text(encoding="utf-8"))
    normalized_record = json.dumps(record, ensure_ascii=False)
    for raw_value in raw_values:
        assert raw_value not in normalized_record
    assert record["correlation_id"] == "req-safe-123"
    assert record["service"] == "api"
    assert record["ts"] == "2026-08-11T00:00:00Z"
    assert "[REDACTED_EMAIL]" in record["event"]
    assert "[REDACTED_PHONE_VN]" in record["session_id"]
    assert record["payload"]["identity"]["cccd"] == "[REDACTED_CCCD]"
    assert record["payload"]["identity"]["passport"] == "[REDACTED_PASSPORT]"
    assert record["payload"]["payment"] == ["[REDACTED_CREDIT_CARD]"]
    assert record["payload"]["address"] == "[REDACTED_ADDRESS_VN]: 123"


def test_configure_logging_places_scrubber_between_timestamp_and_renderers(
    monkeypatch,
) -> None:
    captured: dict = {}
    monkeypatch.setattr(logging_config.logging, "basicConfig", lambda **_: None)
    monkeypatch.setattr(
        logging_config.structlog,
        "configure",
        lambda **kwargs: captured.update(kwargs),
    )

    logging_config.configure_logging()

    processors = captured["processors"]
    timestamp_index = next(
        index
        for index, processor in enumerate(processors)
        if isinstance(processor, logging_config.structlog.processors.TimeStamper)
    )
    scrub_index = processors.index(logging_config.scrub_event)
    file_index = next(
        index
        for index, processor in enumerate(processors)
        if isinstance(processor, logging_config.JsonlFileProcessor)
    )
    renderer_index = next(
        index
        for index, processor in enumerate(processors)
        if isinstance(processor, logging_config.structlog.processors.JSONRenderer)
    )

    assert timestamp_index < scrub_index < file_index < renderer_index
