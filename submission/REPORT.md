# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: F2
- Repository URL: https://github.com/VuTienDung28/Day13-K3-Observability-F2LabD305
- Commit SHA Role E trước merge: `2a2ef7d`.
- Thành viên và vai trò:
  - Chu Nguyễn Tuấn Anh — 2A202601755 — Role A: API & Middleware.
  - Vũ Tiến Dũng — 2A202602009 — Role B: Security Engineer.
  - Nguyễn Đức Chung — 2A202601705 — Role C: Metrics & Dashboard.
  - Đào Thị Trang — 2A202601809 — Role D: SRE & Alerts Engineer.
  - Lê Minh Ngọc — 2A202601471 — Role E: QA & Chief Investigator.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** — 266 log records, 0 record thiếu trường bắt buộc, 0 record thiếu enrichment và 99 correlation ID duy nhất.
- Tổng số traces: **20 managed-prompt traces do Role E tạo** trên đúng project nộp bài; xem [danh sách traces](evidence/role-e-trace-list.png) và [đối chiếu trace IDs](evidence/role-e-langfuse-traces.md).
- Số PII leak còn lại: **0**.
- Link/đường dẫn dashboard: `dashboard.py` (Streamlit tại `http://localhost:8501`), `docs/dashboard-spec.md` và `config/dashboard.yaml`.

## 3. Logging và tracing

- Evidence correlation ID: [CP1 correlation ID](evidence/cp1-correlation-id.png).
- Evidence PII redaction: [CP1 PII redaction](evidence/cp1-pii-redaction.png) và [kết quả validate logs](evidence/cp1-validate-logs.png). Email, điện thoại Việt Nam, CCCD, thẻ thanh toán, passport và từ khóa địa chỉ Việt Nam được thay bằng marker `[REDACTED_*]` trước khi ghi JSONL. Kết quả cuối: `Potential PII leaks detected: 0`, `[PASSED] PII scrubbing`, score 100/100.
- Evidence automated tests: [CP1 automated tests](evidence/cp1-automated-tests.png). Test bao phủ regex, container lồng nhau, processor order, JSONL output, validator độc lập và Langfuse correlation metadata.
- Evidence trace waterfall: [ảnh waterfall](evidence/role-e-trace-waterfall.png), trace [`9889ad67b5b1f2750c63397b6c5a22f2`](https://cloud.langfuse.com/project/cmsobasut013tad0h767g30xg/traces/9889ad67b5b1f2750c63397b6c5a22f2) và [đối chiếu API](evidence/role-e-langfuse-traces.md).
- Giải thích một span đáng chú ý: `rag-retrieve` mất 2501 ms trong tổng trace 2654 ms, trong khi `llm-generate` mất 152 ms. RAG chiếm khoảng 94% thời gian và là điểm chậm chính.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Version/label baseline: version 1 — labels `baseline`, `production` sau rollback; [ảnh metadata baseline](evidence/role-e-prompt-baseline-trace.png).
- Version/label candidate: version 2 — label `candidate`; [ảnh metadata candidate](evidence/role-e-prompt-candidate-trace.png) và [danh sách hai versions](evidence/role-e-prompt-versions.png).
- Trace ID của mỗi version: baseline [`44ce0d581caee45a702876ba8673c2c6`](https://cloud.langfuse.com/project/cmsobasut013tad0h767g30xg/traces/44ce0d581caee45a702876ba8673c2c6); candidate [`39ba423525be6bf83520c037cb1052b8`](https://cloud.langfuse.com/project/cmsobasut013tad0h767g30xg/traces/39ba423525be6bf83520c037cb1052b8).
- Bằng chứng đổi label hoặc rollback: production trên v2 dùng trace `a49c7175c36916e91a127df5de850f24`; sau rollback về v1 dùng trace `505d1e5e25f1fa25d08db2cccd1cf1af`. Xem [ảnh rollback](evidence/role-e-prompt-rollback.png) và [đối chiếu versioning](evidence/role-e-prompt-versioning.md).

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Evidence dashboard:
  - `submission/evidence/role-c-dashboard-runtime.png`
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
- Dashboard runtime dùng Streamlit, đọc trực tiếp `data/logs.jsonl`, mặc định hiển thị 60 phút và tự refresh mỗi 30 giây; sidebar hỗ trợ 15/30/60/180 phút.
- Mỗi panel hiển thị đơn vị và trạng thái so với threshold/SLO; latency, traffic, cost, tokens và quality có đường threshold trực quan.
- Dashboard validator kiểm tra chặt nguồn `data/logs.jsonl`, events, fields, aggregations, unit, threshold, time range 60 phút và refresh 15–30 giây.
- Kết quả kiểm thử tập trung Role C: `17 passed` cho data aggregation, Streamlit smoke test, metrics và dashboard validator.
- Kết quả thực hành: 20 request, error rate 0%, quality trung bình 0.88; P95 bình thường 1124 ms và P95 khi `rag_slow` 2651 ms.
- Evidence runtime `submission/evidence/role-c-dashboard-runtime.png` hiển thị đủ sáu panel từ dữ liệu log thật.

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

## 7. Bonus — Cost Optimization, Audit Log và Automation

- Kịch bản `cost_spike` được chạy trên cùng 10 query trước và sau khi bật giới hạn 160 output tokens. Tổng cost giảm từ **0.079650 USD** xuống **0.024990 USD**, tiết kiệm **0.054660 USD (68.63%)**; output tokens giảm từ 5,244 xuống 1,600. Evidence: [JSON before/after](evidence/bonus-cost-before-after.json) và [ảnh so sánh](evidence/bonus-cost-before-after.png).
- `data/audit.jsonl` là log riêng cho control-plane, chỉ ghi `incident_changed` và `config_changed`. Mỗi dòng có timestamp, actor, action, resource, correlation ID, trạng thái trước/sau và được scrub PII. Evidence mẫu: [audit log](evidence/bonus-audit-log.md).
- `scripts/detect_anomalies.py` tự động đọc `data/logs.jsonl` và ngưỡng trong `config/slo.yaml` để phát hiện PII leak, latency vượt SLO, request failure và daily cost vượt budget. Lần chạy evidence đã phân tích 353 records, phát hiện 4 latency breach và 1 request failure lịch sử, không phát hiện PII leak. Evidence: [anomaly report](evidence/bonus-anomaly-report.json).
- Hướng dẫn tái hiện: [Bonus guide](../docs/BONUS_GUIDE.md). Automated tests cho bonus nằm trong `tests/test_bonus_features.py`.

## 8. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Chu Nguyễn Tuấn Anh (2A202601755) | Role A — correlation ID middleware, request context và exception handler | `bb07f6d` | Correlation ID nối response, log và trace của cùng một request |
| Vũ Tiến Dũng | Security Engineer — CP1 PII Scrubbing, regex patterns và kiểm chứng log không lộ PII. | PR #1; commits `cf98b72`, `c680ce3`, `88730f3`, `8db554c`, `291cf64` | PII phải được scrub sau bước enrich timestamp nhưng trước mọi renderer/file writer; validator phải độc lập với production scrubber; correlation ID giúp đối chiếu cùng request giữa response, logs và traces. |
| Đào Thị Trang (2A202601809) | Role D — hoàn thiện alert rules và runbook theo SLO; định nghĩa severity, owner và điều kiện alert; kiểm tra tính hợp lý của alert dựa trên triệu chứng người dùng | `3651ba6` — Add alert rules and SRE runbook; nhánh `2A202601809_DaoThiTrang` | Alert phải dựa trên SLI/SLO; điều kiện duy trì cần có thời gian cụ thể; runbook phải cho phép incident triage nhanh bằng 3 bước kiểm tra đầu tiên |
| Nguyễn Đức Chung (2A202601705) | Role C — bổ sung request counters và `error_rate_pct`; semantic validator cho contract 6 panel; bộ tổng hợp JSONL; dashboard Streamlit và test/evidence runtime | `5ceb708` — request error-rate metrics; `3f08503` — dashboard semantic validation; `46cff29` — JSONL loader; `b9e19aa` — six-panel aggregation; `a57d068` — Streamlit dashboard; nhánh `2A202601705_NguyenDucChung` | Cách tính error rate không chia cho 0; ý nghĩa P50/P95/P99; cách ánh xạ log event/field sang dashboard; vai trò của threshold/SLO trong phát hiện bất thường |
| Lê Minh Ngọc (2A202601471) | Role E — thêm trace con cho RAG/LLM, cho phép load/challenge test dùng cổng tùy chỉnh, chạy challenge và viết evidence/hướng dẫn | `2a2ef7d` — nhánh `2A202601471-LeMinhNgoc` | Cách nối Metrics → Trace → Log; phân biệt latency regression với error; dùng correlation ID tìm log của trace |
