import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_renders_six_required_panel_titles(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    records = [
        {"event": "request_received", "ts": "2026-08-11T00:00:00Z"},
        {
            "event": "response_sent",
            "ts": "2026-08-11T00:00:01Z",
            "latency_ms": 240,
            "cost_usd": 0.002,
            "tokens_in": 20,
            "tokens_out": 40,
            "quality_score": 0.9,
        },
    ]
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LOG_PATH", str(log_path))

    app = AppTest.from_file(str(REPO_ROOT / "dashboard.py"))
    app.run(timeout=10)

    assert not app.exception
    assert [item.value for item in app.subheader] == [
        "Latency percentiles",
        "Request traffic",
        "Error rate and breakdown",
        "Cost over time",
        "Input and output tokens",
        "Quality proxy",
    ]
