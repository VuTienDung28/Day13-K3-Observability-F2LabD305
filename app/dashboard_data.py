from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class JsonlLoadResult:
    records: list[dict[str, Any]]
    skipped_lines: int


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
