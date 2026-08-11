from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_QUERIES = REPO_ROOT / "data" / "sample_queries.jsonl"
DEFAULT_REPORT = REPO_ROOT / "submission" / "evidence" / "bonus-cost-before-after.json"


def _post_chat(base_url: str, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{base_url}/chat",
            headers={"x-request-id": request_id},
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def _run_phase(
    base_url: str,
    payloads: list[dict[str, Any]],
    *,
    label: str,
    concurrency: int,
) -> dict[str, Any]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_post_chat, base_url, payload, f"bonus-{label}-{index:02d}")
            for index, payload in enumerate(payloads, start=1)
        ]
        responses = [future.result() for future in futures]

    costs = [float(item["cost_usd"]) for item in responses]
    tokens_out = [int(item["tokens_out"]) for item in responses]
    return {
        "requests": len(responses),
        "total_cost_usd": round(sum(costs), 6),
        "average_cost_usd": round(sum(costs) / len(costs), 6),
        "tokens_out_total": sum(tokens_out),
        "tokens_out_max": max(tokens_out),
        "correlation_ids": [item["correlation_id"] for item in responses],
    }


def _control_request(
    client: httpx.Client, method: str, path: str, **kwargs: Any
) -> dict[str, Any]:
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Run the cost_spike workload before and after output-token limiting."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("DAY13_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--max-output-tokens", type=int, default=160)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    if not 1 <= args.max_output_tokens <= 4096:
        parser.error("--max-output-tokens must be between 1 and 4096")

    base_url = args.base_url.rstrip("/")
    payloads = [
        json.loads(line)
        for line in DEFAULT_QUERIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        _control_request(
            client,
            "PUT",
            "/config/cost-optimization",
            json={"enabled": False, "max_output_tokens": args.max_output_tokens},
        )
        _control_request(client, "POST", "/incidents/cost_spike/enable")

    try:
        before = _run_phase(
            base_url, payloads, label="before", concurrency=args.concurrency
        )
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            _control_request(
                client,
                "PUT",
                "/config/cost-optimization",
                json={"enabled": True, "max_output_tokens": args.max_output_tokens},
            )
        after = _run_phase(
            base_url, payloads, label="after", concurrency=args.concurrency
        )
    finally:
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            _control_request(client, "POST", "/incidents/cost_spike/disable")

    saved = before["total_cost_usd"] - after["total_cost_usd"]
    saving_pct = (saved / before["total_cost_usd"] * 100) if before["total_cost_usd"] else 0
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scenario": "cost_spike",
        "optimization": {
            "strategy": "output_token_limit",
            "max_output_tokens": args.max_output_tokens,
        },
        "before": before,
        "after": after,
        "savings": {
            "total_cost_usd": round(saved, 6),
            "percent": round(saving_pct, 2),
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("--- Cost Optimization Before/After ---")
    print(f"Before total_cost_usd: ${before['total_cost_usd']:.6f}")
    print(f"After  total_cost_usd: ${after['total_cost_usd']:.6f}")
    print(f"Savings: ${saved:.6f} ({saving_pct:.2f}%)")
    print(f"Evidence: {args.report}")


if __name__ == "__main__":
    main()
