from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.pii import PII_PATTERNS


DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_SLO_PATH = REPO_ROOT / "config" / "slo.yaml"
PII_DETECTORS = {
    name: re.compile(pattern, re.IGNORECASE) for name, pattern in PII_PATTERNS.items()
}


def _thresholds(slo_path: Path) -> tuple[float, float]:
    config = yaml.safe_load(slo_path.read_text(encoding="utf-8")) or {}
    slis = config.get("slis", {})
    latency_ms = float(slis.get("latency_p95_ms", {}).get("objective", 3000))
    daily_cost_usd = float(slis.get("daily_cost_usd", {}).get("objective", 2.5))
    return latency_ms, daily_cost_usd


def analyze_logs(log_path: Path, slo_path: Path) -> dict[str, Any]:
    latency_limit, daily_cost_limit = _thresholds(slo_path)
    anomalies: list[dict[str, Any]] = []
    daily_costs: defaultdict[str, float] = defaultdict(float)
    valid_records = 0

    for line_number, line in enumerate(
        log_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            anomalies.append(
                {
                    "type": "invalid_json",
                    "severity": "warning",
                    "line": line_number,
                    "reason": exc.msg,
                }
            )
            continue

        valid_records += 1
        raw = json.dumps(record, ensure_ascii=False)
        pii_types = sorted(
            name for name, detector in PII_DETECTORS.items() if detector.search(raw)
        )
        if pii_types:
            anomalies.append(
                {
                    "type": "pii_leak",
                    "severity": "critical",
                    "line": line_number,
                    "correlation_id": record.get("correlation_id"),
                    "pii_types": pii_types,
                }
            )

        latency_ms = record.get("latency_ms")
        if (
            record.get("event") == "response_sent"
            and isinstance(latency_ms, (int, float))
            and latency_ms > latency_limit
        ):
            anomalies.append(
                {
                    "type": "latency_slo_breach",
                    "severity": "warning",
                    "line": line_number,
                    "correlation_id": record.get("correlation_id"),
                    "observed_ms": latency_ms,
                    "threshold_ms": latency_limit,
                }
            )

        if record.get("event") == "request_failed":
            anomalies.append(
                {
                    "type": "request_failure",
                    "severity": "warning",
                    "line": line_number,
                    "correlation_id": record.get("correlation_id"),
                    "error_type": record.get("error_type", "unknown"),
                }
            )

        cost = record.get("cost_usd")
        ts = str(record.get("ts", ""))
        if record.get("event") == "response_sent" and isinstance(cost, (int, float)):
            day = ts[:10] if len(ts) >= 10 else "unknown"
            daily_costs[day] += float(cost)

    for day, total in sorted(daily_costs.items()):
        if total > daily_cost_limit:
            anomalies.append(
                {
                    "type": "daily_cost_slo_breach",
                    "severity": "warning",
                    "day": day,
                    "observed_usd": round(total, 6),
                    "threshold_usd": daily_cost_limit,
                }
            )

    counts: defaultdict[str, int] = defaultdict(int)
    for anomaly in anomalies:
        counts[anomaly["type"]] += 1
    try:
        source = str(log_path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        source = str(log_path)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": source,
        "records_analyzed": valid_records,
        "thresholds": {
            "latency_ms": latency_limit,
            "daily_cost_usd": daily_cost_limit,
        },
        "anomaly_count": len(anomalies),
        "counts_by_type": dict(sorted(counts.items())),
        "anomalies": anomalies,
    }


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Detect PII leaks, latency/cost SLO breaches, and request failures in JSONL logs."
    )
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--slo-config", type=Path, default=DEFAULT_SLO_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-anomaly", action="store_true")
    args = parser.parse_args()

    if not args.log_path.exists():
        parser.error(f"log file not found: {args.log_path}")
    if not args.slo_config.exists():
        parser.error(f"SLO config not found: {args.slo_config}")

    report = analyze_logs(args.log_path, args.slo_config)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    print("--- Automated Anomaly Detection ---")
    print(f"Records analyzed: {report['records_analyzed']}")
    print(f"Anomalies: {report['anomaly_count']}")
    print(f"By type: {report['counts_by_type']}")
    if args.output:
        print(f"Report: {args.output}")

    if args.fail_on_anomaly and report["anomaly_count"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
