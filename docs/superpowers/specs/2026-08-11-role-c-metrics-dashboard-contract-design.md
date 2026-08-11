# Role C Metrics and Dashboard Contract Design

## Goal

Hoàn thiện phần việc Role C mà không phụ thuộc vào PII, tracing, alerting hoặc một dashboard framework: cung cấp `error_rate_pct` chính xác trong metrics và kiểm chứng ngữ nghĩa của dashboard contract gồm đúng sáu nhóm chỉ số.

## Scope

Phần triển khai gồm:

- Tính tổng request thành công và thất bại từ state metrics hiện có.
- Trả `traffic`, `successful_requests`, `failed_requests`, `error_rate_pct` và `error_breakdown` trong `snapshot()`.
- Giữ nguyên các metric latency, cost, token và quality hiện có.
- Bổ sung unit test cho trạng thái rỗng, request thành công, request lỗi và nhiều loại lỗi.
- Nâng validator dashboard từ kiểm tra cấu trúc chung lên kiểm tra contract ngữ nghĩa của sáu panel.
- Giữ nguyên `config/dashboard.yaml` nếu nó đã thỏa contract chính thức.

Không thêm Streamlit, Grafana, notebook hoặc dependency mới. Không sửa PII, middleware, tracing, SLO, alerts, challenge hay submission evidence.

## Metrics Design

State hiện tại dùng `TRAFFIC` cho số request thành công và `ERRORS` cho số request thất bại theo loại lỗi. Thiết kế giữ nguyên cách ghi để tránh sửa luồng của Role A:

```text
successful_requests = TRAFFIC
failed_requests = sum(ERRORS.values())
traffic = successful_requests + failed_requests
error_rate_pct = failed_requests / traffic * 100
```

Khi `traffic == 0`, `error_rate_pct` bằng `0.0`. Giá trị phần trăm được làm tròn hai chữ số thập phân. `error_breakdown` tiếp tục trả số lỗi theo exception type.

Các key mới của `snapshot()`:

```text
successful_requests: int
failed_requests: int
error_rate_pct: float
```

Key `traffic` được định nghĩa rõ là tổng số request đã kết thúc, gồm cả thành công và thất bại.

## Dashboard Contract Validation

Dashboard phải có đúng sáu panel `latency`, `traffic`, `errors`, `cost`, `tokens`, `quality`. Ngoài việc kiểm tra key bắt buộc, validator sẽ đối chiếu từng panel với contract chính thức:

| Panel | Events | Fields | Aggregations | Unit |
|---|---|---|---|---|
| latency | `response_sent` | `latency_ms` | `p50`, `p95`, `p99` | `ms` |
| traffic | `request_received` | `event` | `count`, `rate_per_minute` | `requests_per_minute` |
| errors | `request_received`, `request_failed` | `error_type` | `error_rate_pct`, `count_by_value` | `percent` |
| cost | `response_sent` | `cost_usd` | `sum_by_minute`, `total` | `usd` |
| tokens | `response_sent` | `tokens_in`, `tokens_out` | `sum_by_field` | `tokens` |
| quality | `response_sent` | `quality_score` | `mean` | `score_0_to_1` |

Mọi panel phải dùng nguồn `data/logs.jsonl`. Validator tiếp tục kiểm tra time range 60 phút, refresh 15–30 giây, query không rỗng và threshold hợp lệ.

## Error Handling

- Metrics không chia cho 0 khi chưa có request.
- Validator báo chính xác `panel_id.field` khi source, events, fields, aggregations hoặc unit sai.
- Validator từ chối thiếu panel, thừa panel, thiếu threshold hoặc aggregation của threshold không thuộc panel.

## Testing Strategy

Metrics tests sẽ cô lập state toàn cục trước và sau mỗi test, sau đó kiểm tra:

- Snapshot rỗng trả traffic và error rate bằng 0.
- Request thành công được tính vào traffic và successful requests.
- Request lỗi được tính vào traffic, failed requests và error rate.
- Nhiều error type tạo breakdown và phần trăm chính xác.
- Các percentile hiện có không bị regression.

Dashboard validator tests sẽ tạo bản sao YAML tạm rồi thay đổi từng thuộc tính để chứng minh validator từ chối contract sai. Toàn bộ public tests và hai validator được chạy lại trước khi hoàn tất.

## Compatibility

Thiết kế không thay đổi signature của `record_request()` hoặc `record_error()`. Các consumer hiện tại của `/metrics` vẫn nhận toàn bộ key cũ; chỉ ý nghĩa `traffic` được sửa thành tổng request, phù hợp panel traffic và công thức error rate.
