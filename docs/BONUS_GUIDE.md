# Bonus: Cost Optimization, Audit Log, và Custom Automation

## 1. Đo chi phí trước/sau

Khởi động API:

```bash
uvicorn app.main:app --reload --env-file .env
```

Chạy kịch bản tự động. Script bật `cost_spike`, chạy cùng 10 query khi giới hạn token đang tắt, bật giới hạn output token, chạy lại, ghi evidence rồi tắt incident:

```bash
python scripts/cost_optimization_demo.py
```

Kết quả có `before.total_cost_usd`, `after.total_cost_usd`, tổng tiền và phần trăm tiết kiệm tại `submission/evidence/bonus-cost-before-after.json`. Giới hạn mặc định là 160 output tokens và có thể đổi bằng `--max-output-tokens`.

Có thể thao tác từng bước qua API `PUT /config/cost-optimization` với JSON `{"enabled": true, "max_output_tokens": 160}`. Mọi thay đổi cấu hình này đều được audit.

## 2. Audit log

`data/audit.jsonl` chỉ nhận sự kiện control-plane quan trọng:

- `incident_changed`: bật/tắt incident;
- `config_changed`: thay đổi trạng thái hoặc giới hạn token của cost optimization.

Đường dẫn lấy từ `AUDIT_LOG_PATH`. Dữ liệu chi tiết được scrub PII trước khi ghi và mỗi record có timestamp, actor, action, resource, correlation ID, trạng thái trước/sau.

## 3. Phát hiện anomaly tự động

```bash
python scripts/detect_anomalies.py \
  --output submission/evidence/bonus-anomaly-report.json
```

Script đọc trực tiếp `data/logs.jsonl` và `config/slo.yaml`, phát hiện:

- PII chưa được che;
- từng request vượt latency SLO;
- request thất bại;
- tổng chi phí theo ngày vượt budget.

Dùng `--fail-on-anomaly` trong CI để trả exit code `2` khi có anomaly.
