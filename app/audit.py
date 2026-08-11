from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from structlog.contextvars import get_contextvars

from .pii import scrub_value


AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))
_WRITE_LOCK = threading.Lock()


def write_audit_event(
    event: str,
    *,
    action: str,
    resource: str,
    actor: str = "system",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one security-relevant control-plane event to the audit JSONL file."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event,
        "actor": actor,
        "action": action,
        "resource": resource,
        "correlation_id": get_contextvars().get("correlation_id", "system"),
        "details": details or {},
    }
    safe_record = scrub_value(record)
    path = AUDIT_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(safe_record, ensure_ascii=False, separators=(",", ":"))
    with _WRITE_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    return safe_record
