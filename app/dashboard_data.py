from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class JsonlLoadResult:
    records: list[dict[str, Any]]
    skipped_lines: int


@dataclass(frozen=True)
class DashboardSnapshot:
    window_minutes: int
    window_start: datetime | None
    window_end: datetime | None
    records_total: int
    skipped_lines: int
    traffic_total: int
    traffic_by_minute: list[dict[str, Any]]
    failed_requests: int
    error_rate_pct: float
    error_breakdown: dict[str, int]
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_series: list[dict[str, Any]]
    total_cost_usd: float
    avg_cost_usd: float
    cost_series: list[dict[str, Any]]
    tokens_in_total: int
    tokens_out_total: int
    quality_avg: float
    quality_series: list[dict[str, Any]]


def load_jsonl(path: Path) -> JsonlLoadResult:
    records: list[dict[str, Any]] = []
    skipped_lines = 0

    if not path.exists():
        return JsonlLoadResult(records=[], skipped_lines=0)

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            skipped_lines += 1
            continue
        if not isinstance(value, dict):
            skipped_lines += 1
            continue
        records.append(value)

    return JsonlLoadResult(records=records, skipped_lines=skipped_lines)


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    index = max(0, min(len(items) - 1, math.ceil((p / 100) * len(items)) - 1))
    return float(items[index])


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _minute(timestamp: datetime) -> datetime:
    return timestamp.replace(second=0, microsecond=0)


def _series(counter: dict[datetime, float], value_name: str) -> list[dict[str, Any]]:
    return [
        {"timestamp": timestamp.isoformat(), value_name: value}
        for timestamp, value in sorted(counter.items())
    ]


def build_dashboard_snapshot(
    path: Path, window_minutes: int = 60
) -> DashboardSnapshot:
    loaded = load_jsonl(path)
    timestamped = [
        (timestamp, record)
        for record in loaded.records
        if (timestamp := parse_timestamp(record.get("ts"))) is not None
    ]
    timestamped.sort(key=lambda item: item[0])
    window_end = timestamped[-1][0] if timestamped else None
    window_start = (
        window_end - timedelta(minutes=window_minutes) if window_end else None
    )
    windowed = [
        (timestamp, record)
        for timestamp, record in timestamped
        if window_start is not None and timestamp >= window_start
    ]

    traffic_by_minute: Counter[datetime] = Counter()
    error_breakdown: Counter[str] = Counter()
    latency_values: list[float] = []
    latency_series: list[dict[str, Any]] = []
    cost_values: list[float] = []
    cost_by_minute: defaultdict[datetime, float] = defaultdict(float)
    tokens_in_total = 0
    tokens_out_total = 0
    quality_values: list[float] = []
    quality_by_minute: defaultdict[datetime, list[float]] = defaultdict(list)

    for timestamp, record in windowed:
        event = record.get("event")
        minute = _minute(timestamp)
        if event == "request_received":
            traffic_by_minute[minute] += 1
        elif event == "request_failed":
            error_type = record.get("error_type")
            label = error_type if isinstance(error_type, str) and error_type else "UnknownError"
            error_breakdown[label] += 1
        elif event == "response_sent":
            latency = _number(record.get("latency_ms"))
            if latency is not None:
                latency_values.append(latency)
                latency_series.append(
                    {"timestamp": timestamp.isoformat(), "latency_ms": latency}
                )

            cost = _number(record.get("cost_usd"))
            if cost is not None:
                cost_values.append(cost)
                cost_by_minute[minute] += cost

            tokens_in = _number(record.get("tokens_in"))
            if tokens_in is not None:
                tokens_in_total += int(tokens_in)
            tokens_out = _number(record.get("tokens_out"))
            if tokens_out is not None:
                tokens_out_total += int(tokens_out)

            quality = _number(record.get("quality_score"))
            if quality is not None:
                quality_values.append(quality)
                quality_by_minute[minute].append(quality)

    traffic_total = sum(traffic_by_minute.values())
    failed_requests = sum(error_breakdown.values())
    quality_minute_means = {
        timestamp: round(mean(values), 4)
        for timestamp, values in quality_by_minute.items()
    }

    return DashboardSnapshot(
        window_minutes=window_minutes,
        window_start=window_start,
        window_end=window_end,
        records_total=len(windowed),
        skipped_lines=loaded.skipped_lines,
        traffic_total=traffic_total,
        traffic_by_minute=_series(dict(traffic_by_minute), "requests"),
        failed_requests=failed_requests,
        error_rate_pct=(
            round((failed_requests / traffic_total) * 100, 2)
            if traffic_total
            else 0.0
        ),
        error_breakdown=dict(error_breakdown),
        latency_p50_ms=percentile(latency_values, 50),
        latency_p95_ms=percentile(latency_values, 95),
        latency_p99_ms=percentile(latency_values, 99),
        latency_series=latency_series,
        total_cost_usd=round(sum(cost_values), 4),
        avg_cost_usd=round(mean(cost_values), 4) if cost_values else 0.0,
        cost_series=_series(dict(cost_by_minute), "cost_usd"),
        tokens_in_total=tokens_in_total,
        tokens_out_total=tokens_out_total,
        quality_avg=round(mean(quality_values), 4) if quality_values else 0.0,
        quality_series=_series(quality_minute_means, "quality_score"),
    )
