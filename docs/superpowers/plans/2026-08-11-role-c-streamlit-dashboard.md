# Role C Streamlit Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a Streamlit runtime dashboard that reads `data/logs.jsonl`, renders the six required observability panels, and produces screenshot evidence for CP2.

**Architecture:** Keep log parsing and metric aggregation in a Streamlit-independent `app/dashboard_data.py` module. Render the resulting immutable snapshot in a single-page `dashboard.py` using Streamlit, Pandas, and Altair; tests exercise real JSONL fixtures and a Streamlit smoke run.

**Tech Stack:** Python 3.11+, Streamlit 1.61.1, Pandas 3.0.5, Altair 6.2.2, pytest 8.3.5.

## Global Constraints

- Source of truth is `data/logs.jsonl`.
- Default time range is 60 minutes, ending at the newest valid log timestamp.
- Auto-refresh interval is 30 seconds.
- Render exactly six panel groups with English titles matching `config/dashboard.yaml`.
- Vietnamese is used for explanations and threshold status.
- Do not modify chat API, PII, tracing, prompt versioning, SLO config, alerts, or runbooks.
- Evidence must contain no secret or raw PII.

---

### Task 1: Dependencies and JSONL loading boundary

**Files:**
- Modify: `requirements.txt`
- Create: `app/dashboard_data.py`
- Create: `tests/test_dashboard_data.py`

**Interfaces:**
- Produces: `JsonlLoadResult(records: list[dict[str, Any]], skipped_lines: int)`.
- Produces: `load_jsonl(path: Path) -> JsonlLoadResult`.
- Produces: `parse_timestamp(value: Any) -> datetime | None`.

- [ ] **Step 1: Add a failing JSONL loading test**

```python
def test_load_jsonl_keeps_objects_and_counts_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "logs.jsonl"
    path.write_text(
        '{"event":"request_received","ts":"2026-08-11T00:00:00Z"}\n'
        'not-json\n'
        '[1,2,3]\n'
        '\n',
        encoding="utf-8",
    )

    result = load_jsonl(path)

    assert result.records == [
        {"event": "request_received", "ts": "2026-08-11T00:00:00Z"}
    ]
    assert result.skipped_lines == 2
```

- [ ] **Step 2: Run the loading test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_data.py::test_load_jsonl_keeps_objects_and_counts_malformed_lines -q --basetemp .venv\.pytest_streamlit`

Expected: collection fails because `app.dashboard_data` does not exist.

- [ ] **Step 3: Implement minimal JSONL loading**

```python
@dataclass(frozen=True)
class JsonlLoadResult:
    records: list[dict[str, Any]]
    skipped_lines: int


def load_jsonl(path: Path) -> JsonlLoadResult:
    records: list[dict[str, Any]] = []
    skipped = 0
    if not path.exists():
        return JsonlLoadResult(records=[], skipped_lines=0)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if not isinstance(value, dict):
            skipped += 1
            continue
        records.append(value)
    return JsonlLoadResult(records=records, skipped_lines=skipped)
```

- [ ] **Step 4: Run the loading test and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_data.py::test_load_jsonl_keeps_objects_and_counts_malformed_lines -q --basetemp .venv\.pytest_streamlit`

Expected: PASS.

- [ ] **Step 5: Add timestamp parsing tests**

```python
def test_parse_timestamp_normalizes_zulu_time_to_utc() -> None:
    parsed = parse_timestamp("2026-08-11T00:00:00Z")
    assert parsed == datetime(2026, 8, 11, tzinfo=timezone.utc)


def test_parse_timestamp_rejects_missing_or_invalid_values() -> None:
    assert parse_timestamp(None) is None
    assert parse_timestamp("invalid") is None
```

- [ ] **Step 6: Run timestamp tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_data.py -q --basetemp .venv\.pytest_streamlit`

Expected: FAIL because `parse_timestamp` is missing.

- [ ] **Step 7: Implement timestamp parsing and install pinned dependencies**

```python
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
```

Append to `requirements.txt`:

```text
streamlit==1.61.1
pandas==3.0.5
altair==6.2.2
```

Install: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

- [ ] **Step 8: Run Task 1 tests and commit**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_data.py -q --basetemp .venv\.pytest_streamlit`

Expected: all Task 1 tests PASS.

Commit:

```powershell
git add requirements.txt app/dashboard_data.py tests/test_dashboard_data.py
git commit -m "feat: add dashboard log data loader"
```

### Task 2: Six-panel aggregation snapshot

**Files:**
- Modify: `app/dashboard_data.py`
- Modify: `tests/test_dashboard_data.py`

**Interfaces:**
- Produces: `DashboardSnapshot` containing window metadata and the six panel datasets.
- Produces: `percentile(values: list[float], p: int) -> float`.
- Produces: `build_dashboard_snapshot(path: Path, window_minutes: int = 60) -> DashboardSnapshot`.

- [ ] **Step 1: Add a failing percentile test**

```python
def test_percentile_uses_nearest_rank_and_handles_empty_values() -> None:
    assert percentile([], 95) == 0.0
    assert percentile([100, 200, 300, 400], 50) == 200.0
    assert percentile([100, 200, 300, 400], 95) == 400.0
```

- [ ] **Step 2: Run percentile test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_data.py::test_percentile_uses_nearest_rank_and_handles_empty_values -q --basetemp .venv\.pytest_streamlit`

Expected: FAIL because `percentile` is missing.

- [ ] **Step 3: Implement nearest-rank percentile**

```python
def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    index = max(0, min(len(items) - 1, math.ceil((p / 100) * len(items)) - 1))
    return float(items[index])
```

- [ ] **Step 4: Add a failing full snapshot test**

Create a fixture with records at `00:00`, `00:30`, `00:45`, and one record outside the 60-minute window. Assert literal results:

```python
snapshot = build_dashboard_snapshot(path, window_minutes=60)
assert snapshot.traffic_total == 3
assert snapshot.failed_requests == 1
assert snapshot.error_rate_pct == 33.33
assert snapshot.error_breakdown == {"RuntimeError": 1}
assert snapshot.latency_p50_ms == 200.0
assert snapshot.latency_p95_ms == 2600.0
assert snapshot.latency_p99_ms == 2600.0
assert snapshot.total_cost_usd == 0.03
assert snapshot.tokens_in_total == 30
assert snapshot.tokens_out_total == 50
assert snapshot.quality_avg == 0.8
assert snapshot.window_minutes == 60
```

- [ ] **Step 5: Run snapshot test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_data.py::test_build_dashboard_snapshot_aggregates_six_panels -q --basetemp .venv\.pytest_streamlit`

Expected: FAIL because `DashboardSnapshot` and `build_dashboard_snapshot` are missing.

- [ ] **Step 6: Implement immutable snapshot aggregation**

`DashboardSnapshot` stores scalar metrics plus JSON-compatible series:

```python
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
```

Implement `build_dashboard_snapshot` in this order:

```python
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
```

Then derive each field only from `windowed`: `request_received` drives traffic,
`request_failed` drives errors and the denominator is traffic, and
`response_sent` drives latency/cost/token/quality. Group chart points by minute,
ignore non-numeric values, use nearest-rank percentiles, and round rates/cost/
quality to the same precision as `/metrics`.

- [ ] **Step 7: Run all aggregation tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_data.py -q --basetemp .venv\.pytest_streamlit`

Expected: all dashboard-data tests PASS.

- [ ] **Step 8: Commit Task 2**

```powershell
git add app/dashboard_data.py tests/test_dashboard_data.py
git commit -m "feat: aggregate six dashboard panels"
```

### Task 3: Streamlit runtime UI

**Files:**
- Create: `dashboard.py`
- Create: `tests/test_dashboard_app.py`

**Interfaces:**
- Consumes: `build_dashboard_snapshot(path, window_minutes)`.
- Produces: Streamlit page at port 8501 with six named panels and threshold visualizations.

- [ ] **Step 1: Add a failing Streamlit AppTest smoke test**

```python
def test_dashboard_renders_six_required_panel_titles(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(FIXTURE_JSONL, encoding="utf-8")
    monkeypatch.setenv("LOG_PATH", str(log_path))

    app = AppTest.from_file(str(REPO_ROOT / "dashboard.py"))
    app.run(timeout=10)

    assert not app.exception
    titles = [item.value for item in app.subheader]
    assert titles == [
        "Latency percentiles",
        "Request traffic",
        "Error rate and breakdown",
        "Cost over time",
        "Input and output tokens",
        "Quality proxy",
    ]
```

- [ ] **Step 2: Run smoke test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_app.py -q --basetemp .venv\.pytest_streamlit`

Expected: FAIL because `dashboard.py` does not exist.

- [ ] **Step 3: Implement the single-page Streamlit app**

The implementation must:

- call `st.set_page_config(page_title="Day 13 AI Observability", layout="wide")`;
- choose `[15, 30, 60, 180]` minutes in the sidebar with default 60;
- read `LOG_PATH` or default to `data/logs.jsonl`;
- wrap rendering in `@st.fragment(run_every="30s")`;
- render exactly six `st.subheader` titles in YAML order;
- create Altair threshold rules for latency, cost, and quality;
- show units and SLO values in visible captions/cards;
- show a warning and load-test commands when the file is missing or empty.

- [ ] **Step 4: Run UI smoke test and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_app.py -q --basetemp .venv\.pytest_streamlit`

Expected: PASS with no Streamlit exception.

- [ ] **Step 5: Run the complete Role C tests and commit**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_data.py tests/test_dashboard_app.py tests/test_metrics.py tests/test_dashboard_validator.py -q --basetemp .venv\.pytest_streamlit`

Expected: all Role C tests PASS.

Commit:

```powershell
git add dashboard.py tests/test_dashboard_app.py
git commit -m "feat: add streamlit observability dashboard"
```

### Task 4: Runtime verification, screenshot, and report

**Files:**
- Create: `submission/evidence/role-c-dashboard-runtime.png`
- Modify: `docs/dashboard-spec.md`
- Modify: `submission/evidence/role-c-dashboard-spec.md`
- Modify: `submission/REPORT.md`

**Interfaces:**
- Consumes: running Streamlit dashboard and real `data/logs.jsonl`.
- Produces: runtime screenshot and final report references.

- [ ] **Step 1: Start Streamlit headlessly on port 8501**

Run Streamlit from the virtual environment with `--server.headless true`, `--server.port 8501`, and a hidden PowerShell process. Record the process ID for cleanup.

- [ ] **Step 2: Verify runtime health**

Run: `Invoke-WebRequest http://127.0.0.1:8501/_stcore/health -UseBasicParsing`

Expected: HTTP 200 with body `ok`.

- [ ] **Step 3: Inspect the rendered dashboard and capture evidence**

Open `http://127.0.0.1:8501` in the in-app browser, verify six titles/time range/units/thresholds, then save a full-page screenshot as `submission/evidence/role-c-dashboard-runtime.png`.

- [ ] **Step 4: Stop only the recorded Streamlit process**

Stop the exact process ID started in Step 1. Do not stop the FastAPI server on port 8000.

- [ ] **Step 5: Update dashboard docs and report**

Replace “spec-based only” wording with:

- Tool: Streamlit runtime at local port 8501.
- Source: `data/logs.jsonl`.
- Evidence: `submission/evidence/role-c-dashboard-runtime.png`.
- Run command: `streamlit run dashboard.py`.

- [ ] **Step 6: Run final verification**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\validate_dashboard.py
$env:LOG_PATH='.venv/final-test-logs.jsonl'
.\.venv\Scripts\python.exe -m pytest -q --basetemp .venv\.pytest_streamlit_final
.\.venv\Scripts\python.exe -m compileall -q app dashboard.py scripts tests
git diff --check
```

Expected: dashboard 6/6, all tests pass, compilation succeeds, and no whitespace errors.

- [ ] **Step 7: Scan evidence/diff for secrets and commit**

Verify no `LANGFUSE_*` value or `pk-lf-`/`sk-lf-` token exists in changed source/evidence.

Commit:

```powershell
git add requirements.txt app/dashboard_data.py dashboard.py tests/test_dashboard_data.py tests/test_dashboard_app.py docs/dashboard-spec.md submission/REPORT.md submission/evidence/role-c-dashboard-spec.md submission/evidence/role-c-dashboard-runtime.png
git commit -m "docs: add streamlit dashboard runtime evidence"
```

- [ ] **Step 8: Push the current feature branch**

Run: `git push origin 2A202601705_NguyenDucChung`

Expected: remote branch points to the final verified commit; `main` remains unchanged.
