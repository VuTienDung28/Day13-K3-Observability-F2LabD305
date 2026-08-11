from __future__ import annotations

import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from app.dashboard_data import DashboardSnapshot, build_dashboard_snapshot


LATENCY_SLO_MS = 3000
TRAFFIC_THRESHOLD_RPM = 1
ERROR_SLO_PCT = 2
COST_BUDGET_USD = 2.5
TOKEN_BUDGET = 50_000
QUALITY_SLO = 0.75


st.set_page_config(page_title="Day 13 AI Observability", layout="wide")
st.title("Day 13 AI Observability")
st.caption(
    "Dashboard runtime cho CP2 · Nguồn dữ liệu: data/logs.jsonl · "
    "Tự động làm mới mỗi 30 giây"
)

window_minutes = st.sidebar.selectbox(
    "Khoảng thời gian",
    options=[15, 30, 60, 180],
    index=2,
    format_func=lambda value: f"{value} phút",
)
log_path = Path(os.environ.get("LOG_PATH", "data/logs.jsonl"))
st.sidebar.caption(f"Log source: {log_path}")


def _status(value: float, threshold: float, operator: str, unit: str) -> str:
    passed = value <= threshold if operator == "lte" else value >= threshold
    symbol = "✅" if passed else "⚠️"
    comparison = "≤" if operator == "lte" else "≥"
    state = "đạt" if passed else "chưa đạt"
    return f"{symbol} {state}: {value:g} {unit} (ngưỡng {comparison} {threshold:g} {unit})"


def _time_frame(series: list[dict], value_column: str) -> pd.DataFrame:
    frame = pd.DataFrame(series)
    if frame.empty:
        return frame
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    return frame.dropna(subset=["timestamp", value_column])


def _line_with_threshold(
    frame: pd.DataFrame,
    value_column: str,
    y_title: str,
    threshold: float,
    color: str,
) -> alt.Chart:
    line = (
        alt.Chart(frame)
        .mark_line(point=True, color=color)
        .encode(
            x=alt.X("timestamp:T", title="Time (UTC)"),
            y=alt.Y(f"{value_column}:Q", title=y_title),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time"),
                alt.Tooltip(f"{value_column}:Q", title=y_title),
            ],
        )
    )
    rule = (
        alt.Chart(pd.DataFrame({value_column: [threshold]}))
        .mark_rule(color="#ef4444", strokeDash=[6, 4], strokeWidth=2)
        .encode(y=f"{value_column}:Q")
    )
    return (line + rule).properties(height=240)


def _render_latency(snapshot: DashboardSnapshot) -> None:
    st.subheader("Latency percentiles")
    p50, p95, p99 = st.columns(3)
    p50.metric("P50", f"{snapshot.latency_p50_ms:.0f} ms")
    p95.metric("P95", f"{snapshot.latency_p95_ms:.0f} ms")
    p99.metric("P99", f"{snapshot.latency_p99_ms:.0f} ms")
    st.caption(_status(snapshot.latency_p95_ms, LATENCY_SLO_MS, "lte", "ms"))
    frame = _time_frame(snapshot.latency_series, "latency_ms")
    if frame.empty:
        st.info("Chưa có event response_sent chứa latency_ms trong cửa sổ đã chọn.")
    else:
        st.altair_chart(
            _line_with_threshold(
                frame, "latency_ms", "Latency (ms)", LATENCY_SLO_MS, "#2563eb"
            ),
            width="stretch",
        )


def _render_traffic(snapshot: DashboardSnapshot) -> None:
    st.subheader("Request traffic")
    peak_rpm = max(
        (int(point["requests"]) for point in snapshot.traffic_by_minute),
        default=0,
    )
    total, peak = st.columns(2)
    total.metric("Requests", snapshot.traffic_total)
    peak.metric("Peak requests/min", peak_rpm)
    st.caption(_status(peak_rpm, TRAFFIC_THRESHOLD_RPM, "gte", "requests/min"))
    frame = _time_frame(snapshot.traffic_by_minute, "requests")
    if frame.empty:
        st.info("Chưa có event request_received trong cửa sổ đã chọn.")
    else:
        st.altair_chart(
            _line_with_threshold(
                frame,
                "requests",
                "Requests per minute",
                TRAFFIC_THRESHOLD_RPM,
                "#0891b2",
            ),
            width="stretch",
        )


def _render_errors(snapshot: DashboardSnapshot) -> None:
    st.subheader("Error rate and breakdown")
    rate, failed = st.columns(2)
    rate.metric("Error rate", f"{snapshot.error_rate_pct:.2f}%")
    failed.metric("Failed requests", snapshot.failed_requests)
    st.caption(_status(snapshot.error_rate_pct, ERROR_SLO_PCT, "lte", "%"))
    if snapshot.error_breakdown:
        breakdown = pd.DataFrame(
            [
                {"Error type": error_type, "Count": count}
                for error_type, count in sorted(snapshot.error_breakdown.items())
            ]
        )
        st.dataframe(breakdown, hide_index=True, width="stretch")
    else:
        st.success("Không có request_failed trong cửa sổ đã chọn.")


def _render_cost(snapshot: DashboardSnapshot) -> None:
    st.subheader("Cost over time")
    total, average = st.columns(2)
    total.metric("Total cost", f"${snapshot.total_cost_usd:.4f}")
    average.metric("Average/request", f"${snapshot.avg_cost_usd:.4f}")
    st.caption(_status(snapshot.total_cost_usd, COST_BUDGET_USD, "lte", "USD"))
    frame = _time_frame(snapshot.cost_series, "cost_usd")
    if frame.empty:
        st.info("Chưa có event response_sent chứa cost_usd trong cửa sổ đã chọn.")
    else:
        frame["total_cost_usd"] = frame["cost_usd"].cumsum()
        st.altair_chart(
            _line_with_threshold(
                frame,
                "total_cost_usd",
                "Cumulative cost (USD)",
                COST_BUDGET_USD,
                "#7c3aed",
            ),
            width="stretch",
        )


def _render_tokens(snapshot: DashboardSnapshot) -> None:
    st.subheader("Input and output tokens")
    token_in, token_out = st.columns(2)
    token_in.metric("Input tokens", snapshot.tokens_in_total)
    token_out.metric("Output tokens", snapshot.tokens_out_total)
    largest = max(snapshot.tokens_in_total, snapshot.tokens_out_total)
    st.caption(_status(largest, TOKEN_BUDGET, "lte", "tokens/field"))
    frame = pd.DataFrame(
        {
            "Direction": ["Input", "Output"],
            "Tokens": [snapshot.tokens_in_total, snapshot.tokens_out_total],
        }
    )
    bars = (
        alt.Chart(frame)
        .mark_bar(color="#ea580c")
        .encode(
            x=alt.X("Direction:N", title=None),
            y=alt.Y("Tokens:Q", title="Tokens"),
            tooltip=["Direction:N", "Tokens:Q"],
        )
    )
    rule = (
        alt.Chart(pd.DataFrame({"Tokens": [TOKEN_BUDGET]}))
        .mark_rule(color="#ef4444", strokeDash=[6, 4], strokeWidth=2)
        .encode(y="Tokens:Q")
    )
    st.altair_chart((bars + rule).properties(height=240), width="stretch")


def _render_quality(snapshot: DashboardSnapshot) -> None:
    st.subheader("Quality proxy")
    st.metric("Average quality", f"{snapshot.quality_avg:.2f}")
    st.caption(_status(snapshot.quality_avg, QUALITY_SLO, "gte", "score"))
    frame = _time_frame(snapshot.quality_series, "quality_score")
    if frame.empty:
        st.info("Chưa có event response_sent chứa quality_score trong cửa sổ đã chọn.")
    else:
        st.altair_chart(
            _line_with_threshold(
                frame,
                "quality_score",
                "Quality score (0–1)",
                QUALITY_SLO,
                "#16a34a",
            ),
            width="stretch",
        )


@st.fragment(run_every="30s")
def render_dashboard() -> None:
    snapshot = build_dashboard_snapshot(log_path, window_minutes=window_minutes)

    if not log_path.exists():
        st.warning(
            f"Không tìm thấy {log_path}. Hãy chạy API và `python scripts/load_test.py`."
        )
    elif snapshot.records_total == 0:
        st.warning("Log chưa có event hợp lệ trong cửa sổ đã chọn.")

    if snapshot.window_start and snapshot.window_end:
        st.caption(
            "Cửa sổ dữ liệu UTC: "
            f"{snapshot.window_start:%Y-%m-%d %H:%M:%S} → "
            f"{snapshot.window_end:%Y-%m-%d %H:%M:%S} · "
            f"{snapshot.records_total} events"
        )
    if snapshot.skipped_lines:
        st.warning(f"Đã bỏ qua {snapshot.skipped_lines} dòng JSONL không hợp lệ.")

    _render_latency(snapshot)
    _render_traffic(snapshot)
    _render_errors(snapshot)
    _render_cost(snapshot)
    _render_tokens(snapshot)
    _render_quality(snapshot)


render_dashboard()
