from __future__ import annotations

import os
import threading
from dataclasses import asdict, dataclass

from .audit import write_audit_event


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CostOptimizationConfig:
    enabled: bool
    max_output_tokens: int


_LOCK = threading.Lock()
_CONFIG = CostOptimizationConfig(
    enabled=_env_bool("COST_OPTIMIZATION_ENABLED", True),
    max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "160")),
)


def get_config() -> CostOptimizationConfig:
    with _LOCK:
        return _CONFIG


def update_config(
    *, enabled: bool, max_output_tokens: int | None = None, actor: str = "system"
) -> CostOptimizationConfig:
    global _CONFIG
    with _LOCK:
        previous = _CONFIG
        limit = previous.max_output_tokens if max_output_tokens is None else max_output_tokens
        if not 1 <= limit <= 4096:
            raise ValueError("max_output_tokens must be between 1 and 4096")
        _CONFIG = CostOptimizationConfig(enabled=enabled, max_output_tokens=limit)
        current = _CONFIG

    write_audit_event(
        "config_changed",
        action="update",
        resource="cost_optimization",
        actor=actor,
        details={"before": asdict(previous), "after": asdict(current)},
    )
    return current


def limit_output_tokens(raw_output_tokens: int) -> int:
    config = get_config()
    if not config.enabled:
        return raw_output_tokens
    return min(raw_output_tokens, config.max_output_tokens)
