# Dashboard spec — Day 13 AI Observability

## Phương án triển khai

- Công cụ sử dụng: **mô tả bằng spec**, là một phương án được CP2 chấp nhận khi nhóm không dùng Langfuse/Grafana để hiển thị dashboard.
- Nguồn live để kiểm tra nhanh: `GET /metrics`.
- Nguồn chuẩn dùng cho contract và chấm điểm: `data/logs.jsonl`.
- Contract có thể kiểm tra bằng máy: `config/dashboard.yaml`.
- Khoảng thời gian mặc định: 60 phút.
- Chu kỳ refresh đề xuất: 30 giây nếu chuyển spec sang công cụ trực quan.

`/metrics` cung cấp snapshot tích lũy từ lúc API khởi động. `data/logs.jsonl` giữ event theo thời gian và được dùng khi cần tính theo cửa sổ, vẽ xu hướng hoặc điều tra bằng correlation ID.

## Thiết kế sáu panel

| # | Panel | Nguồn live `/metrics` | Event/field trong log | Hiển thị đề xuất | Đơn vị | Threshold/SLO line |
|---|---|---|---|---|---|---|
| 1 | Latency percentiles | `latency_p50`, `latency_p95`, `latency_p99` | `response_sent.latency_ms` | Ba single values hoặc line P50/P95/P99 | ms | P95 ≤ 3000 ms |
| 2 | Request traffic | `traffic`, `successful_requests`, `failed_requests` | `request_received` | Counter và request/phút | requests/min | ≥ 1 request/phút trong lúc load test |
| 3 | Error rate and breakdown | `error_rate_pct`, `error_breakdown` | `request_received`, `request_failed.error_type` | Tỷ lệ lỗi và bảng theo loại lỗi | % | Error rate ≤ 2% |
| 4 | Cost over time | `total_cost_usd`, `avg_cost_usd` | `response_sent.cost_usd` | Tổng cost và cost theo phút | USD | Tổng cost ≤ 2.5 USD |
| 5 | Input/output tokens | `tokens_in_total`, `tokens_out_total` | `response_sent.tokens_in`, `response_sent.tokens_out` | Hai counters input/output | tokens | Tổng theo từng field ≤ 50000 tokens |
| 6 | Quality proxy | `quality_avg` | `response_sent.quality_score` | Single value hoặc line trung bình | score 0–1 | Quality trung bình ≥ 0.75 |

## Snapshot đã kiểm chứng

Snapshot từ `GET /metrics` sau load test và practice incident:

| Chỉ số | Giá trị |
|---|---:|
| Traffic | 20 requests |
| Successful requests | 20 |
| Failed requests | 0 |
| Error rate | 0.0% |
| Latency P50 | 1124 ms |
| Latency P95 | 2651 ms |
| Latency P99 | 2651 ms |
| Average cost | 0.002 USD |
| Total cost | 0.0391 USD |
| Input tokens | 660 |
| Output tokens | 2473 |
| Quality average | 0.88 |

Phân tích `data/logs.jsonl` cho thấy 10 response bình thường có P95 1124 ms, còn 10 response khi thực hành `rag_slow` có P95 2651 ms. Incident làm P95 tăng rõ ràng và vượt ngưỡng challenge 2000 ms, nhưng vẫn thấp hơn SLO tổng quát 3000 ms.

## Tự kiểm và evidence

```bash
python scripts/validate_dashboard.py
```

Kết quả đã kiểm chứng: `HỢP LỆ: 6/6 panel có trong dashboard contract.`

Evidence Role C:

- `submission/evidence/role-c-validate-dashboard.txt`
- `submission/evidence/role-c-metrics-snapshot.json`
- `submission/evidence/role-c-incident-comparison.md`
- `submission/evidence/role-c-dashboard-spec.md`
