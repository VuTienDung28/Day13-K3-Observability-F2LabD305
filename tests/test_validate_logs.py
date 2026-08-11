from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import validate_logs


def write_record(path: Path, message: str) -> None:
    record = {
        "ts": "2026-08-11T00:00:00Z",
        "level": "info",
        "service": "api",
        "event": "request_received",
        "correlation_id": "req-12345678",
        "user_id_hash": "abc123",
        "session_id": "session-01",
        "feature": "monitoring",
        "model": "fake-llm",
        "payload": {"message_preview": message},
    }
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("pii_type", "raw_value"),
    [
        ("email", "student@vinuni.edu.vn"),
        ("phone_vn", "090 123 4567"),
        ("cccd", "001234567890"),
        ("credit_card", "4111 1111 1111 1111"),
        ("passport", "b12345678"),
        ("address_vn", "Đường"),
    ],
)
def test_validator_detects_each_raw_pii_type(
    pii_type: str,
    raw_value: str,
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "logs.jsonl"
    write_record(log_path, f"Raw PII: {raw_value}")
    monkeypatch.setattr(validate_logs, "LOG_PATH", log_path)

    validate_logs.main()

    output = capsys.readouterr().out
    assert "Potential PII leaks detected: 1" in output
    assert pii_type in output
    assert "[FAILED] PII scrubbing" in output


def test_validator_passes_a_sanitized_record(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    log_path = tmp_path / "logs.jsonl"
    write_record(
        log_path,
        " ".join(
            [
                "[REDACTED_EMAIL]",
                "[REDACTED_PHONE_VN]",
                "[REDACTED_CCCD]",
                "[REDACTED_CREDIT_CARD]",
                "[REDACTED_PASSPORT]",
                "[REDACTED_ADDRESS_VN]",
            ]
        ),
    )
    monkeypatch.setattr(validate_logs, "LOG_PATH", log_path)

    validate_logs.main()

    output = capsys.readouterr().out
    assert "Potential PII leaks detected: 0" in output
    assert "[PASSED] PII scrubbing" in output
