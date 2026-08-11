# Role C Metrics and Dashboard Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện `error_rate_pct`, request counters và semantic validation cho dashboard contract sáu panel của Role C.

**Architecture:** Giữ nguyên API ghi metrics hiện tại để tránh sửa phần Role A. `snapshot()` tổng hợp success counter và error counter thành tổng traffic/error rate; dashboard validator dùng một contract tĩnh để đối chiếu source, events, fields, aggregations và unit của từng panel.

**Tech Stack:** Python 3.11+, pytest, PyYAML, FastAPI metrics module hiện có.

## Global Constraints

- Không thêm Streamlit, Grafana, notebook hoặc dependency mới.
- Không sửa PII, middleware, tracing, SLO, alerts, challenge hoặc submission evidence.
- Không thay đổi signature của `record_request()` và `record_error()`.
- `traffic` là tổng request đã kết thúc, gồm thành công và thất bại.
- `error_rate_pct` bằng `0.0` khi chưa có request và được làm tròn hai chữ số.

---

### Task 1: Request totals and error-rate metrics

**Files:**
- Modify: `tests/test_metrics.py`
- Modify: `app/metrics.py:40`

**Interfaces:**
- Consumes: `record_request(latency_ms: int, cost_usd: float, tokens_in: int, tokens_out: int, quality_score: float) -> None`; `record_error(error_type: str) -> None`.
- Produces: `snapshot() -> dict` với các key `traffic`, `successful_requests`, `failed_requests`, `error_rate_pct`, `error_breakdown`.

- [ ] **Step 1: Add isolated metrics-state fixture and empty snapshot test**

```python
import pytest
from app import metrics


@pytest.fixture(autouse=True)
def reset_metrics_state():
    metrics.TRAFFIC = 0
    metrics.REQUEST_LATENCIES.clear()
    metrics.REQUEST_COSTS.clear()
    metrics.REQUEST_TOKENS_IN.clear()
    metrics.REQUEST_TOKENS_OUT.clear()
    metrics.ERRORS.clear()
    metrics.QUALITY_SCORES.clear()
    yield
    metrics.TRAFFIC = 0
    metrics.ERRORS.clear()


def test_snapshot_has_zero_request_counters() -> None:
    result = metrics.snapshot()
    assert result["traffic"] == 0
    assert result["successful_requests"] == 0
    assert result["failed_requests"] == 0
    assert result["error_rate_pct"] == 0.0
```

- [ ] **Step 2: Run the empty snapshot test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py::test_snapshot_has_zero_request_counters -q --basetemp .pytest_role_c`

Expected: FAIL with `KeyError: 'successful_requests'`.

- [ ] **Step 3: Implement request totals and zero-safe error rate in `snapshot()`**

```python
def snapshot() -> dict:
    successful_requests = TRAFFIC
    failed_requests = sum(ERRORS.values())
    total_requests = successful_requests + failed_requests
    error_rate_pct = (
        round((failed_requests / total_requests) * 100, 2)
        if total_requests
        else 0.0
    )
    return {
        "traffic": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "error_rate_pct": error_rate_pct,
        "latency_p50": percentile(REQUEST_LATENCIES, 50),
        "latency_p95": percentile(REQUEST_LATENCIES, 95),
        "latency_p99": percentile(REQUEST_LATENCIES, 99),
        "avg_cost_usd": round(mean(REQUEST_COSTS), 4) if REQUEST_COSTS else 0.0,
        "total_cost_usd": round(sum(REQUEST_COSTS), 4),
        "tokens_in_total": sum(REQUEST_TOKENS_IN),
        "tokens_out_total": sum(REQUEST_TOKENS_OUT),
        "error_breakdown": dict(ERRORS),
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
    }
```

- [ ] **Step 4: Run the empty snapshot test and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py::test_snapshot_has_zero_request_counters -q --basetemp .pytest_role_c`

Expected: PASS.

- [ ] **Step 5: Add mixed success/failure behavior test**

```python
def test_snapshot_calculates_error_rate_from_all_completed_requests() -> None:
    for _ in range(3):
        metrics.record_request(100, 0.01, 10, 5, 0.8)
    metrics.record_error("RuntimeError")

    result = metrics.snapshot()
    assert result["traffic"] == 4
    assert result["successful_requests"] == 3
    assert result["failed_requests"] == 1
    assert result["error_rate_pct"] == 25.0
    assert result["error_breakdown"] == {"RuntimeError": 1}
```

- [ ] **Step 6: Run the mixed test and verify it passes with the intended implementation**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py -q --basetemp .pytest_role_c`

Expected: all metrics tests PASS.

- [ ] **Step 7: Commit Task 1**

```powershell
git add app/metrics.py tests/test_metrics.py
git commit -m "feat: add request error rate metrics"
```

### Task 2: Semantic dashboard contract validation

**Files:**
- Modify: `tests/test_dashboard_validator.py`
- Modify: `scripts/validate_dashboard.py:14`

**Interfaces:**
- Consumes: YAML dashboard object with six panels.
- Produces: `load_dashboard_config(path: Path) -> dict` that rejects semantic drift using `DashboardConfigError`.

- [ ] **Step 1: Add failing source-contract test**

```python
def test_validator_rejects_panel_with_wrong_source(tmp_path: Path) -> None:
    payload = yaml.safe_load(
        (REPO_ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8")
    )
    payload["dashboard"]["panels"][0]["source"] = "other.jsonl"
    invalid_config = tmp_path / "dashboard.yaml"
    invalid_config.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    result = run_validator(invalid_config)
    assert result.returncode == 1
    assert "latency.source" in result.stdout
```

- [ ] **Step 2: Run the source test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_validator.py::test_validator_rejects_panel_with_wrong_source -q --basetemp .pytest_role_c`

Expected: FAIL because the current validator accepts any non-empty source.

- [ ] **Step 3: Add the exact panel contract mapping and source validation**

```python
PANEL_CONTRACTS = {
    "latency": {
        "events": ["response_sent"],
        "fields": ["latency_ms"],
        "aggregations": ["p50", "p95", "p99"],
        "unit": "ms",
    },
    "traffic": {
        "events": ["request_received"],
        "fields": ["event"],
        "aggregations": ["count", "rate_per_minute"],
        "unit": "requests_per_minute",
    },
    "errors": {
        "events": ["request_received", "request_failed"],
        "fields": ["error_type"],
        "aggregations": ["error_rate_pct", "count_by_value"],
        "unit": "percent",
    },
    "cost": {
        "events": ["response_sent"],
        "fields": ["cost_usd"],
        "aggregations": ["sum_by_minute", "total"],
        "unit": "usd",
    },
    "tokens": {
        "events": ["response_sent"],
        "fields": ["tokens_in", "tokens_out"],
        "aggregations": ["sum_by_field"],
        "unit": "tokens",
    },
    "quality": {
        "events": ["response_sent"],
        "fields": ["quality_score"],
        "aggregations": ["mean"],
        "unit": "score_0_to_1",
    },
}

if panel["source"] != "data/logs.jsonl":
    raise DashboardConfigError(
        f"'{panel_id}.source' phải bằng 'data/logs.jsonl'"
    )
```

- [ ] **Step 4: Run the source test and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_validator.py::test_validator_rejects_panel_with_wrong_source -q --basetemp .pytest_role_c`

Expected: PASS.

- [ ] **Step 5: Add failing events/fields/aggregations/unit semantic test**

```python
@pytest.mark.parametrize("field,bad_value", [
    ("events", ["request_failed"]),
    ("fields", ["event"]),
    ("aggregations", ["count"]),
    ("unit", "requests"),
])
def test_validator_rejects_error_panel_semantic_drift(
    tmp_path: Path, field: str, bad_value
) -> None:
    payload = yaml.safe_load(
        (REPO_ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8")
    )
    error_panel = next(
        panel for panel in payload["dashboard"]["panels"] if panel["id"] == "errors"
    )
    error_panel[field] = bad_value
    invalid_config = tmp_path / f"dashboard-{field}.yaml"
    invalid_config.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    result = run_validator(invalid_config)
    assert result.returncode == 1
    assert f"errors.{field}" in result.stdout
```

- [ ] **Step 6: Run the semantic test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_validator.py::test_validator_rejects_error_panel_semantic_drift -q --basetemp .pytest_role_c`

Expected: at least the events, fields or unit cases FAIL because the current validator accepts semantic drift.

- [ ] **Step 7: Validate all semantic fields against `PANEL_CONTRACTS`**

```python
expected = PANEL_CONTRACTS[panel_id]
for field in ("events", "fields", "aggregations", "unit"):
    if panel[field] != expected[field]:
        raise DashboardConfigError(
            f"'{panel_id}.{field}' không khớp dashboard contract"
        )
```

- [ ] **Step 8: Run all dashboard validator tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_validator.py -q --basetemp .pytest_role_c`

Expected: all dashboard validator tests PASS.

- [ ] **Step 9: Commit Task 2**

```powershell
git add scripts/validate_dashboard.py tests/test_dashboard_validator.py
git commit -m "test: enforce dashboard panel semantics"
```

### Task 3: Full Role C verification

**Files:**
- Verify: `app/metrics.py`
- Verify: `scripts/validate_dashboard.py`
- Verify: `config/dashboard.yaml`
- Verify: `tests/test_metrics.py`
- Verify: `tests/test_dashboard_validator.py`

**Interfaces:**
- Consumes: completed Task 1 and Task 2 changes.
- Produces: verification evidence for the Role C implementation.

- [ ] **Step 1: Run Role C focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py tests/test_dashboard_validator.py -q --basetemp .pytest_role_c`

Expected: all focused tests PASS.

- [ ] **Step 2: Run the dashboard contract validator**

Run: `.\.venv\Scripts\python.exe scripts/validate_dashboard.py`

Expected: `HỢP LỆ: 6/6 panel có trong dashboard contract.`

- [ ] **Step 3: Run the full public test suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest_role_c`

Expected: all tests PASS. Existing FastAPI deprecation warnings are allowed; no failures or errors are allowed.

- [ ] **Step 4: Inspect formatting and scope**

Run: `git diff --check` and `git status --short`

Expected: no whitespace errors; only Role C implementation files and plan bookkeeping are changed.

- [ ] **Step 5: Record final commit if verification updates were required**

```powershell
git add app/metrics.py scripts/validate_dashboard.py tests/test_metrics.py tests/test_dashboard_validator.py docs/superpowers/plans/2026-08-11-role-c-metrics-dashboard-contract.md
git commit -m "feat: complete role c observability metrics"
```
