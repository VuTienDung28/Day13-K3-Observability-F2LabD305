# Role C — Dashboard configuration evidence

- Người thực hiện: Nguyễn Đức Chung — 2A202601705.
- Phương án CP2: dashboard runtime bằng Streamlit.
- Entrypoint: `dashboard.py`.
- Lệnh chạy: `streamlit run dashboard.py`.
- URL mặc định: `http://localhost:8501`.
- Spec đầy đủ: `docs/dashboard-spec.md`.
- Machine-readable contract: `config/dashboard.yaml`.
- Nguồn live: `GET /metrics`.
- Nguồn dashboard: `data/logs.jsonl`.
- Time range mặc định: 60 phút; có thể chọn 15/30/60/180 phút.
- Refresh runtime: 30 giây.
- Validator: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Ảnh runtime: `submission/evidence/role-c-dashboard-runtime.png`.

Sáu nhóm panel đã cấu hình:

1. Latency P50/P95/P99 — ms — P95 ≤ 3000 ms.
2. Traffic — requests/phút — theo dõi request count/rate.
3. Error rate và breakdown — % — error rate ≤ 2%.
4. Cost — USD — tổng cost ≤ 2.5 USD.
5. Input and output tokens — tokens — theo dõi tổng từng loại.
6. Quality proxy — score 0–1 — trung bình ≥ 0.75.
