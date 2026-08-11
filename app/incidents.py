from __future__ import annotations

from .audit import write_audit_event

STATE = {
    "rag_slow": False,
    "tool_fail": False,
    "cost_spike": False,
}


def enable(name: str, *, actor: str = "system") -> None:
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    previous = STATE[name]
    STATE[name] = True
    write_audit_event(
        "incident_changed",
        action="enable",
        resource=f"incident/{name}",
        actor=actor,
        details={"before": previous, "after": True},
    )



def disable(name: str, *, actor: str = "system") -> None:
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    previous = STATE[name]
    STATE[name] = False
    write_audit_event(
        "incident_changed",
        action="disable",
        resource=f"incident/{name}",
        actor=actor,
        details={"before": previous, "after": False},
    )



def status() -> dict[str, bool]:
    return dict(STATE)
