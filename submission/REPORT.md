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
- Tổng số traces: .
- Số PII leak còn lại: **0**.
- Link/đường dẫn dashboard:

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

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
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
