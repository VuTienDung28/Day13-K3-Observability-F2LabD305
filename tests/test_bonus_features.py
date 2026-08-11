from __future__ import annotations

import json
from pathlib import Path

from app import audit, cost_optimization
from app.cost_optimization import CostOptimizationConfig
from app.incidents import STATE, disable, enable
from app.mock_llm import FakeLLM
from scripts.detect_anomalies import analyze_logs


def test_audit_log_contains_only_explicit_control_events(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_LOG_PATH", audit_path)
    original = STATE["cost_spike"]
    try:
        enable("cost_spike", actor="test")
        disable("cost_spike", actor="test")
    finally:
        STATE["cost_spike"] = original

    records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert [record["event"] for record in records] == [
        "incident_changed",
        "incident_changed",
    ]
    assert records[0]["action"] == "enable"
    assert records[1]["action"] == "disable"


def test_cost_spike_output_is_capped_when_optimization_enabled(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(audit, "AUDIT_LOG_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr("app.mock_llm.time.sleep", lambda _: None)
    monkeypatch.setattr("app.mock_llm.random.randint", lambda _start, _end: 120)
    monkeypatch.setitem(STATE, "cost_spike", True)
    monkeypatch.setattr(
        cost_optimization,
        "_CONFIG",
        CostOptimizationConfig(enabled=False, max_output_tokens=160),
    )
    llm = FakeLLM()

    assert llm.generate("prompt").usage.output_tokens == 480
    cost_optimization.update_config(enabled=True, max_output_tokens=160, actor="test")
    assert llm.generate("prompt").usage.output_tokens == 160


def test_anomaly_detector_finds_pii_latency_failure_and_daily_cost(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "logs.jsonl"
    slo_path = tmp_path / "slo.yaml"
    records = [
        {
            "ts": "2026-08-11T01:00:00Z",
            "event": "response_sent",
            "correlation_id": "req-1",
            "latency_ms": 3501,
            "cost_usd": 1.5,
            "payload": {"email": "leak@example.com"},
        },
        {
            "ts": "2026-08-11T02:00:00Z",
            "event": "response_sent",
            "correlation_id": "req-2",
            "latency_ms": 100,
            "cost_usd": 1.2,
        },
        {
            "ts": "2026-08-11T03:00:00Z",
            "event": "request_failed",
            "correlation_id": "req-3",
            "error_type": "RuntimeError",
        },
    ]
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    slo_path.write_text(
        "slis:\n"
        "  latency_p95_ms:\n"
        "    objective: 3000\n"
        "  daily_cost_usd:\n"
        "    objective: 2.5\n",
        encoding="utf-8",
    )

    report = analyze_logs(log_path, slo_path)

    assert report["counts_by_type"] == {
        "daily_cost_slo_breach": 1,
        "latency_slo_breach": 1,
        "pii_leak": 1,
        "request_failure": 1,
    }
