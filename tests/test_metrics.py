import pytest

from app import metrics
from app.metrics import percentile


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
    metrics.REQUEST_LATENCIES.clear()
    metrics.REQUEST_COSTS.clear()
    metrics.REQUEST_TOKENS_IN.clear()
    metrics.REQUEST_TOKENS_OUT.clear()
    metrics.ERRORS.clear()
    metrics.QUALITY_SCORES.clear()


def test_percentile_basic() -> None:
    assert percentile([100, 200, 300, 400], 50) >= 100


def test_snapshot_has_zero_request_counters() -> None:
    result = metrics.snapshot()

    assert result["traffic"] == 0
    assert result["successful_requests"] == 0
    assert result["failed_requests"] == 0
    assert result["error_rate_pct"] == 0.0


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
