# Role C — Dashboard configuration evidence

- Người thực hiện: Nguyễn Đức Chung — 2A202601705.
- Phương án CP2: mô tả dashboard bằng spec.
- Spec đầy đủ: `docs/dashboard-spec.md`.
- Machine-readable contract: `config/dashboard.yaml`.
- Nguồn live: `GET /metrics`.
- Nguồn chuẩn: `data/logs.jsonl`.
- Time range: 60 phút.
- Refresh đề xuất: 30 giây.
- Validator: `HỢP LỆ: 6/6 panel có trong dashboard contract.`

Sáu nhóm panel đã cấu hình:

1. Latency P50/P95/P99 — ms — P95 ≤ 3000 ms.
2. Traffic — requests/phút — theo dõi request count/rate.
3. Error rate và breakdown — % — error rate ≤ 2%.
4. Cost — USD — tổng cost ≤ 2.5 USD.
5. Input/output tokens — tokens — theo dõi tổng từng loại.
6. Quality proxy — score 0–1 — trung bình ≥ 0.75.
