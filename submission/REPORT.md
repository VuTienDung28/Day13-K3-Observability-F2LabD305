# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: F2
- Repository URL: https://github.com/VuTienDung28/Day13-K3-Observability-F2LabD305
- Commit SHA cuối: **CẦN ĐIỀN SAU KHI COMMIT PHẦN ROLE E**.
- Thành viên và vai trò:
  - Chu Nguyễn Tuấn Anh — 2A202601755 — Role A: API & Middleware.
  - Vũ Tiến Dũng — 2A202602009 — Role B: Security Engineer.
  - Đào Thị Trang — 2A202601809 — Role D: SRE & Alerts.
  - Nguyễn Đức Chung — 2A202601705 — Role C: Metrics & Dashboard.
  - Lê Minh Ngọc — 2A202601471 — Role E: QA & Chief Investigator.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — 252 log records, 0 record thiếu trường bắt buộc, 0 record thiếu enrichment và 96 correlation ID duy nhất.
- Tổng số traces: **20 managed-prompt traces do Role E tạo** trên đúng project nộp bài; xem `evidence/role-e-langfuse-traces.md`.
- Số PII leak còn lại: **0**.
- Link/đường dẫn dashboard: `docs/dashboard-spec.md` và `config/dashboard.yaml` (phương án dashboard bằng spec theo CP2).

## 3. Logging và tracing

- Evidence correlation ID: [CP1 correlation ID](evidence/cp1-correlation-id.png).
- Evidence PII redaction: [CP1 PII redaction](evidence/cp1-pii-redaction.png) và [kết quả validate logs](evidence/cp1-validate-logs.png). Email, điện thoại Việt Nam, CCCD, thẻ thanh toán, passport và từ khóa địa chỉ Việt Nam được thay bằng marker `[REDACTED_*]` trước khi ghi JSONL. Kết quả cuối: `Potential PII leaks detected: 0`, `[PASSED] PII scrubbing`, score 100/100.
- Evidence automated tests: [CP1 automated tests](evidence/cp1-automated-tests.png). Test bao phủ regex, container lồng nhau, processor order, JSONL output, validator độc lập và Langfuse correlation metadata.
- Evidence trace waterfall: trace [`9889ad67b5b1f2750c63397b6c5a22f2`](https://cloud.langfuse.com/project/cmsobasut013tad0h767g30xg/traces/9889ad67b5b1f2750c63397b6c5a22f2); chi tiết API tại `evidence/role-e-langfuse-traces.md`. **Cần chụp thêm ảnh UI `evidence/role-e-trace-waterfall.png` trước khi nộp.**
- Giải thích một span đáng chú ý: `rag-retrieve` mất 2501 ms trong tổng trace 2654 ms, trong khi `llm-generate` mất 152 ms. RAG chiếm khoảng 94% thời gian và là điểm chậm chính.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Version/label baseline: version 1 — labels `baseline`, `production` sau rollback.
- Version/label candidate: version 2 — label `candidate`.
- Trace ID của mỗi version: baseline [`44ce0d581caee45a702876ba8673c2c6`](https://cloud.langfuse.com/project/cmsobasut013tad0h767g30xg/traces/44ce0d581caee45a702876ba8673c2c6); candidate [`39ba423525be6bf83520c037cb1052b8`](https://cloud.langfuse.com/project/cmsobasut013tad0h767g30xg/traces/39ba423525be6bf83520c037cb1052b8).
- Bằng chứng đổi label hoặc rollback: production trên v2 dùng trace `a49c7175c36916e91a127df5de850f24`; sau rollback về v1 dùng trace `505d1e5e25f1fa25d08db2cccd1cf1af`. Chi tiết tại `evidence/role-e-prompt-versioning.md`; **cần chụp thêm ảnh UI `evidence/role-e-prompt-rollback.png` trước khi nộp.**

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
- Alert rules và runbook: `config/alert_rules.yaml` định nghĩa ba alert cho latency, error rate và quality/cost; runbook tương ứng nằm tại `docs/alerts.md`.

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

### Phần triển khai Role D — SRE & Alerts

- Người thực hiện: Đào Thị Trang — 2A202601809.
- Mục tiêu chính: thiết lập alert rules dựa trên triệu chứng người dùng và SLO, đồng thời viết runbook rõ ràng cho xử lý sự cố.
- Công việc đã hoàn thành:
  - Hoàn thiện `config/alert_rules.yaml` với ba alert thực tế: latency SLO breach, error budget burn và quality/cost regression.
  - Thiết lập mức độ ưu tiên (critical/warning), điều kiện alert và owner rõ ràng.
  - Viết `docs/alerts.md` với runbook gồm: SLI/SLO liên quan, điều kiện duy trì, tác động người dùng, 3 bước kiểm tra đầu tiên và mitigation tạm thời.
  - Duy trì nguyên tắc: alert không dựa vào tên implementation nội bộ, mà dựa trên triệu chứng hoặc SLO.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`.
- Triệu chứng từ metrics: P95 tăng từ 1124 ms lên 2651 ms khi bật `rag_slow`, vượt ngưỡng challenge 2000 ms; error rate vẫn bằng 0%.
- Trace ID liên quan: [`9889ad67b5b1f2750c63397b6c5a22f2`](https://cloud.langfuse.com/project/cmsobasut013tad0h767g30xg/traces/9889ad67b5b1f2750c63397b6c5a22f2); waterfall `run=2654 ms`, `rag-retrieve=2501 ms`, `llm-generate=152 ms`.
- Log line/correlation ID liên quan: `rolee-new-challenge-01`, event `response_sent`, `latency_ms=2652`; xem `submission/evidence/role-e-local-investigation.md`.
- Root cause: scenario `rag_slow` làm bước RAG retrieval chạy `time.sleep(2.5)` trong `app/mock_rag.py`; error rate vẫn 0%, vì vậy đây là latency regression chứ không phải request failure.
- Fix action: tắt incident sau khi điều tra; với production cần timeout vector store, cache kết quả và tối ưu truy vấn retrieval.
- Preventive measure: thêm span riêng `rag-retrieve`/`llm-generate`, theo dõi retrieval latency và giữ alert API latency P95.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Chu Nguyễn Tuấn Anh (2A202601755) | Role A — correlation ID middleware, request context và exception handler | `bb07f6d` | Correlation ID nối response, log và trace của cùng một request |
| Vũ Tiến Dũng (2A202602009) | Role B — PII scrubbing đệ quy, processor log và liên kết correlation ID vào trace | `cf98b72`, `c680ce3`, `88730f3`, `291cf64` | Phải scrub dữ liệu trước khi render JSON và phải kiểm tra cả cấu trúc lồng nhau |
| Đào Thị Trang (2A202601809) | Role D — hoàn thiện alert rules và runbook theo SLO; định nghĩa severity, owner và điều kiện alert; kiểm tra tính hợp lý của alert dựa trên triệu chứng người dùng | `3651ba6` — Add alert rules and SRE runbook; nhánh `2A202601809_DaoThiTrang` | Alert phải dựa trên SLI/SLO; điều kiện duy trì cần có thời gian cụ thể; runbook phải cho phép incident triage nhanh bằng 3 bước kiểm tra đầu tiên |
| Nguyễn Đức Chung (2A202601705) | Role C — bổ sung request counters và `error_rate_pct`; tăng cường semantic validation cho dashboard contract 6 panel; viết test metrics/dashboard; đồng bộ `origin/main` vào nhánh cá nhân | `5ceb708` — request error-rate metrics; `3f08503` — dashboard semantic validation; nhánh `2A202601705_NguyenDucChung` | Cách tính error rate không chia cho 0; ý nghĩa P50/P95/P99; cách ánh xạ log event/field sang dashboard; vai trò của threshold/SLO trong phát hiện bất thường |
| Lê Minh Ngọc (2A202601471) | Role E — thêm trace con cho RAG/LLM, cho phép load/challenge test dùng cổng tùy chỉnh, chạy challenge và viết evidence/hướng dẫn | **CẦN ĐIỀN COMMIT/PR ROLE E** | Cách nối Metrics → Trace → Log; phân biệt latency regression với error; dùng correlation ID tìm log của trace |
