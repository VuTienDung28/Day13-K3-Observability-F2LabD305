# Role C — So sánh metrics trước và trong incident

Nguồn: `data/logs.jsonl`, sinh từ 20 request trong buổi thực hành.

| Giai đoạn | Số response | P95 | Min | Max |
|---|---:|---:|---:|---:|
| Bình thường (`latency_ms < 2000`) | 10 | 1124 ms | 150 ms | 1124 ms |
| `rag_slow` (`latency_ms >= 2000`) | 10 | 2651 ms | 2650 ms | 2651 ms |

- Incident được bật tại `2026-08-11T04:19:34.669205Z`.
- Incident được tắt tại `2026-08-11T04:20:02.616991Z`.
- P95 tăng từ 1124 ms lên 2651 ms.
- P95 khi incident vượt ngưỡng challenge 2000 ms.
- P95 vẫn thấp hơn SLO tổng quát 3000 ms.
- Không có request lỗi; `error_rate_pct = 0.0`.

Kết luận: triệu chứng chính là latency tăng do scenario `rag_slow`; traffic, error rate và quality không cho thấy suy giảm tương ứng trong lần chạy này.
