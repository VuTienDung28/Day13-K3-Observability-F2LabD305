# Role C Streamlit Dashboard Design

## Goal

Tạo dashboard runtime bằng Streamlit từ `data/logs.jsonl`, hiển thị đúng sáu nhóm chỉ số của `config/dashboard.yaml`, có time range, đơn vị, threshold/SLO và ảnh evidence dùng khi chấm CP2.

## Scope

Phần triển khai gồm:

- Module thuần Python để đọc, lọc và tổng hợp structured logs.
- Một trang Streamlit hiển thị sáu panel.
- Auto-refresh mỗi 30 giây.
- Test cho toàn bộ phép tính dashboard.
- Ảnh dashboard runtime từ dữ liệu load test thật.
- Cập nhật dashboard spec, report và evidence Role C.

Không thay đổi API chat, PII, tracing, prompt versioning, SLO config, alert rules hoặc runbook của role khác.

## Architecture

### `app/dashboard_data.py`

Module này không import Streamlit. Nó cung cấp các hàm có thể test độc lập:

- Đọc từng JSON object hợp lệ từ file JSONL; bỏ qua dòng trống hoặc malformed.
- Chuẩn hóa timestamp ISO 8601 về UTC.
- Chọn cửa sổ mặc định 60 phút kết thúc tại timestamp mới nhất trong file để evidence có thể tái tạo ngay cả khi log được tạo trước thời điểm demo.
- Tính percentile nearest-rank cho latency.
- Tổng hợp traffic theo phút, error rate/breakdown, cost theo thời gian, tổng tokens và quality trung bình.
- Trả một dashboard snapshot có cấu trúc ổn định cho lớp UI.

### `dashboard.py`

Trang Streamlit đọc `data/logs.jsonl` qua module aggregation và render UI. Không tính lại business logic trong giao diện.

Bố cục:

```text
Header, data window, refresh status
Latency percentiles      | Request traffic
Error rate & breakdown   | Cost over time
Input/output tokens      | Quality proxy
```

Tên panel giữ nguyên tiếng Anh theo `config/dashboard.yaml`. Chú thích, trạng thái threshold và hướng dẫn lỗi dùng tiếng Việt.

## Data Flow

```text
FastAPI /chat
    -> structured JSON events
    -> data/logs.jsonl
    -> app/dashboard_data.py
    -> dashboard snapshot
    -> dashboard.py / Streamlit
    -> runtime screenshot evidence
```

`GET /metrics` vẫn dùng để đối chiếu snapshot hiện tại, nhưng dashboard runtime lấy `data/logs.jsonl` làm nguồn chuẩn theo contract.

## Six Panels

### 1. Latency percentiles

- Event: `response_sent`.
- Field: `latency_ms`.
- Values: P50, P95, P99.
- Unit: ms.
- Threshold: P95 ≤ 3000 ms.
- UI: ba metric cards và biểu đồ latency theo thời gian với SLO line 3000 ms.

### 2. Request traffic

- Event: `request_received`.
- Aggregation: count theo phút và tổng request.
- Unit: requests/minute.
- Threshold: ít nhất 1 request/phút trong lúc load test.
- UI: total metric và bar chart theo phút.

### 3. Error rate and breakdown

- Events: `request_received`, `request_failed`.
- Field: `error_type`.
- Formula: failed/received × 100; bằng 0 khi không có request.
- Unit: percent.
- Threshold: ≤ 2%.
- UI: error-rate metric, trạng thái threshold và breakdown table/bar.

### 4. Cost over time

- Event: `response_sent`.
- Field: `cost_usd`.
- Values: total và cost theo phút.
- Unit: USD.
- Threshold: total ≤ 2.5 USD.
- UI: total metric và cumulative cost line với budget line.

### 5. Input and output tokens

- Event: `response_sent`.
- Fields: `tokens_in`, `tokens_out`.
- Unit: tokens.
- Threshold: tổng theo từng field ≤ 50000.
- UI: hai metric cards và bar chart so sánh input/output.

### 6. Quality proxy

- Event: `response_sent`.
- Field: `quality_score`.
- Aggregation: mean.
- Unit: score 0–1.
- Threshold: ≥ 0.75.
- UI: average metric và quality line với minimum-quality line.

## Time Range and Refresh

- Default window: 60 phút.
- Window end: timestamp mới nhất có trong file log.
- Sidebar cho phép chọn 15, 30, 60 hoặc 180 phút để demo.
- Streamlit fragment refresh mỗi 30 giây và đọc lại file.
- Dashboard hiển thị rõ thời điểm bắt đầu/kết thúc của cửa sổ và thời điểm render.

## Error Handling

- Nếu `data/logs.jsonl` chưa tồn tại: hiển thị cảnh báo và lệnh chạy API/load test.
- Nếu file không có JSON record hợp lệ: hiển thị cảnh báo, không crash.
- Nếu cửa sổ không có response: các metric trả 0 và panel giải thích chưa có dữ liệu.
- Malformed JSON lines bị bỏ qua và số dòng bị bỏ qua được hiển thị trong caption.
- Giá trị thiếu hoặc sai kiểu không tham gia phép tổng hợp tương ứng.

## Dependencies

- Streamlit: runtime và layout.
- Pandas: dataframe/time-series dùng cho chart.
- Altair: biểu đồ có threshold/SLO rule.

Các dependency được pin trong `requirements.txt` sau khi kiểm tra phiên bản tương thích với Python đang dùng.

## Testing

TDD áp dụng cho module aggregation trước khi viết Streamlit UI. Test dùng temporary JSONL fixtures và kiểm tra:

- Malformed lines được bỏ qua.
- Cửa sổ thời gian lọc đúng boundary.
- Percentile rỗng và nearest-rank.
- Traffic count/rate theo phút.
- Error rate zero-safe và breakdown.
- Cost total/time series.
- Token totals.
- Quality average/time series.
- Snapshot đúng với một fixture chứa cả baseline và `rag_slow`.

Sau unit tests, dashboard được chạy local và kiểm tra trực quan ở viewport đủ rộng để nhìn cả tên panel, time range, đơn vị và threshold. Ảnh evidence được lưu tại:

`submission/evidence/role-c-dashboard-runtime.png`

## Acceptance Criteria

- `streamlit run dashboard.py` khởi động thành công.
- Dashboard đọc đúng `data/logs.jsonl`.
- Đủ sáu panel đúng contract.
- Time range mặc định 60 phút và refresh 30 giây.
- Threshold/SLO hiển thị rõ.
- Dashboard validator vẫn báo `HỢP LỆ: 6/6 panel`.
- Role C tests và full public test suite pass.
- Runtime screenshot tồn tại và được dẫn trong `submission/REPORT.md`.
- Không có secret hoặc PII trong source/evidence.
