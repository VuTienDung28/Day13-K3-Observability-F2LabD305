# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: F2-LabD305
- Repository URL: https://github.com/VuTienDung28/Day13-K3-Observability-F2LabD305
- Commit SHA cuối:
- Thành viên và vai trò:
  - Vũ Tiến Dũng - Security Engineer
  - Chu Nguyễn Tuấn Anh - API & Middleware
  - Nguyễn Văn Chung - Metrics và DashBoard
  - Đào Thị Trang - SRE & Alerts Engineer
  - Lê Minh Ngọc - QA & Chief Investigator

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — 12 log records, 0 record thiếu trường bắt buộc, 0 record thiếu enrichment và 4 correlation ID duy nhất.
- Tổng số traces: 
- Số PII leak còn lại: **0**.
- Link/đường dẫn dashboard:Link/đường dẫn dashboard: `docs/dashboard-spec.md` và `config/dashboard.yaml` (phương án dashboard bằng spec theo CP2).

## 3. Logging và tracing

- Evidence correlation ID: [CP1 correlation ID](evidence/cp1-correlation-id.png).
- Evidence PII redaction: [CP1 PII redaction](evidence/cp1-pii-redaction.png) và [kết quả validate logs](evidence/cp1-validate-logs.png). Email, điện thoại Việt Nam, CCCD, thẻ thanh toán, passport và từ khóa địa chỉ Việt Nam được thay bằng marker `[REDACTED_*]` trước khi ghi JSONL. Kết quả cuối: `Potential PII leaks detected: 0`, `[PASSED] PII scrubbing`, score 100/100.
- Evidence automated tests: [CP1 automated tests](evidence/cp1-automated-tests.png). Test bao phủ regex, container lồng nhau, processor order, JSONL output, validator độc lập và Langfuse correlation metadata.
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Evidence dashboard:
  - `submission/evidence/role-c-dashboard-spec.md`
  - `submission/evidence/role-c-validate-dashboard.txt`
  - `submission/evidence/role-c-metrics-snapshot.json`
  - `submission/evidence/role-c-incident-comparison.md`
- SLO đã chọn và lý do:
  - Latency P95 ≤ 3000 ms để theo dõi trải nghiệm phản hồi của người dùng.
  - Error rate ≤ 2% để phát hiện tỷ lệ request thất bại vượt mức cho phép.
  - Tổng cost trong cửa sổ quan sát ≤ 2.5 USD để kiểm soát chi phí.
  - Quality score trung bình ≥ 0.75 để theo dõi chất lượng câu trả lời.
- Alert rules và runbook:

### Phần triển khai Role C — Metrics & Dashboard

- Người thực hiện: Nguyễn Đức Chung — 2A202601705.
- Nhánh làm việc: `2A202601705_NguyenDucChung`.
- Metrics đã bổ sung:
  - `successful_requests`: tổng request xử lý thành công.
  - `failed_requests`: tổng lỗi từ tất cả `error_type`.
  - `traffic`: tổng request đã hoàn tất, gồm thành công và thất bại.
  - `error_rate_pct = failed_requests / traffic × 100`; trả `0.0` khi chưa có request và làm tròn hai chữ số thập phân.
- Dashboard contract gồm đúng sáu nhóm chỉ số: latency P50/P95/P99, traffic, error rate/breakdown, cost, input/output tokens và quality proxy.
- Dashboard validator kiểm tra chặt nguồn `data/logs.jsonl`, events, fields, aggregations, unit, threshold, time range 60 phút và refresh 15–30 giây.
- Kết quả kiểm thử riêng Role C: `11 passed` cho `tests/test_metrics.py` và `tests/test_dashboard_validator.py`.
- Kết quả thực hành: 20 request, error rate 0%, quality trung bình 0.88; P95 bình thường 1124 ms và P95 khi `rag_slow` 2651 ms.
- Phương án evidence của Role C là dashboard spec, không yêu cầu ảnh dashboard runtime theo lựa chọn được CP2 cho phép.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`.
- Triệu chứng từ metrics: P95 tăng từ 1124 ms lên 2651 ms khi bật `rag_slow`, vượt ngưỡng challenge 2000 ms; error rate vẫn bằng 0%.
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên   | Phần việc                                                                             | Commit/PR                                                            | Điều đã học                                                                                                                                                                                                   |
| ------------ | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vũ Tiến Dũng | Security Engineer — CP1 PII Scrubbing, regex patterns và kiểm chứng log không lộ PII. | PR #1; commits `cf98b72`, `c680ce3`, `88730f3`, `8db554c`, `291cf64` | PII phải được scrub sau bước enrich timestamp nhưng trước mọi renderer/file writer; validator phải độc lập với production scrubber; correlation ID giúp đối chiếu cùng request giữa response, logs và traces. |
| Thành viên | Phần việc | Commit/PR | Điều đã học |
| Nguyễn Đức Chung (2A202601705) | Role C — bổ sung request counters và `error_rate_pct`; tăng cường semantic validation cho dashboard contract 6 panel; viết test metrics/dashboard; đồng bộ `origin/main` vào nhánh cá nhân | `5ceb708` — request error-rate metrics; `3f08503` — dashboard semantic validation; nhánh `2A202601705_NguyenDucChung` | Cách tính error rate không chia cho 0; ý nghĩa P50/P95/P99; cách ánh xạ log event/field sang dashboard; vai trò của threshold/SLO trong phát hiện bất thường |
