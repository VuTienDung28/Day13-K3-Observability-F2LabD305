import json
from datetime import datetime, timezone
from pathlib import Path

from app.dashboard_data import (
    build_dashboard_snapshot,
    load_jsonl,
    parse_timestamp,
    percentile,
)


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


def test_percentile_uses_nearest_rank_and_handles_empty_values() -> None:
    assert percentile([], 95) == 0.0
    assert percentile([100, 200, 300, 400], 50) == 200.0
    assert percentile([100, 200, 300, 400], 95) == 400.0


def test_build_dashboard_snapshot_aggregates_six_panels(tmp_path: Path) -> None:
    path = tmp_path / "logs.jsonl"
    records = [
        {
            "event": "response_sent",
            "ts": "2026-08-10T23:59:59Z",
            "latency_ms": 9999,
            "cost_usd": 9,
            "tokens_in": 999,
            "tokens_out": 999,
            "quality_score": 0.1,
        },
        {"event": "request_received", "ts": "2026-08-11T00:00:00Z"},
        {
            "event": "response_sent",
            "ts": "2026-08-11T00:01:00Z",
            "latency_ms": 100,
            "cost_usd": 0.01,
            "tokens_in": 10,
            "tokens_out": 20,
            "quality_score": 0.7,
        },
        {"event": "request_received", "ts": "2026-08-11T00:30:00Z"},
        {
            "event": "response_sent",
            "ts": "2026-08-11T00:31:00Z",
            "latency_ms": 200,
            "cost_usd": 0.01,
            "tokens_in": 10,
            "tokens_out": 15,
            "quality_score": 0.8,
        },
        {"event": "request_received", "ts": "2026-08-11T00:45:00Z"},
        {
            "event": "request_failed",
            "ts": "2026-08-11T00:45:30Z",
            "error_type": "RuntimeError",
        },
        {
            "event": "response_sent",
            "ts": "2026-08-11T00:46:00Z",
            "latency_ms": 2600,
            "cost_usd": 0.01,
            "tokens_in": 10,
            "tokens_out": 15,
            "quality_score": 0.9,
        },
        {"event": "dashboard_anchor", "ts": "2026-08-11T01:00:00Z"},
    ]
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    snapshot = build_dashboard_snapshot(path, window_minutes=60)

    assert snapshot.traffic_total == 3
    assert snapshot.failed_requests == 1
    assert snapshot.error_rate_pct == 33.33
    assert snapshot.error_breakdown == {"RuntimeError": 1}
    assert snapshot.latency_p50_ms == 200.0
    assert snapshot.latency_p95_ms == 2600.0
    assert snapshot.latency_p99_ms == 2600.0
    assert snapshot.total_cost_usd == 0.03
    assert snapshot.avg_cost_usd == 0.01
    assert snapshot.tokens_in_total == 30
    assert snapshot.tokens_out_total == 50
    assert snapshot.quality_avg == 0.8
    assert snapshot.window_minutes == 60
    assert snapshot.window_start == datetime(2026, 8, 11, tzinfo=timezone.utc)
    assert snapshot.window_end == datetime(2026, 8, 11, 1, tzinfo=timezone.utc)
