from datetime import datetime, timezone
from pathlib import Path

from app.dashboard_data import load_jsonl, parse_timestamp


def test_load_jsonl_keeps_objects_and_counts_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "logs.jsonl"
    path.write_text(
        '{"event":"request_received","ts":"2026-08-11T00:00:00Z"}\n'
        "not-json\n"
        "[1,2,3]\n"
        "\n",
        encoding="utf-8",
    )

    result = load_jsonl(path)

    assert result.records == [
        {"event": "request_received", "ts": "2026-08-11T00:00:00Z"}
    ]
    assert result.skipped_lines == 2


def test_parse_timestamp_normalizes_zulu_time_to_utc() -> None:
    parsed = parse_timestamp("2026-08-11T00:00:00Z")

    assert parsed == datetime(2026, 8, 11, tzinfo=timezone.utc)


def test_parse_timestamp_rejects_missing_or_invalid_values() -> None:
    assert parse_timestamp(None) is None
    assert parse_timestamp("invalid") is None
