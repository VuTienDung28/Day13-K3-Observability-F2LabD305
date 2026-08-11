# Role E — Local challenge investigation

Ngày chạy: 2026-08-11
Challenge: `day13-k3-observability-v1`
Incident: `rag_slow`

## Kết quả kiểm thử

```text
python -m pytest -q
67 passed, 2 warnings
```

Hai warning là cảnh báo deprecation cho FastAPI `on_event`, không phải test failure.

## Metrics

| Giai đoạn | Traffic | P95 | P99 | Error rate |
|---|---:|---:|---:|---:|
| Baseline | 10 | 151 ms | 151 ms | 0.0% |
| Challenge có Langfuse tracing | 5 | 2652 ms | 2652 ms | 0.0% |

P95 khi challenge vượt ngưỡng chính thức 2000 ms. Error rate không tăng, nên triệu chứng là latency regression.

## Log evidence

Correlation ID: `rolee-new-challenge-01`

```json
{"service":"api","latency_ms":2652,"event":"response_sent","session_id":"k3-challenge-s01","feature":"refund","correlation_id":"rolee-new-challenge-01","level":"info"}
```

Incident control evidence:

```text
2026-08-11T05:31:49.691653Z incident_enabled  rag_slow
2026-08-11T05:32:03.913330Z incident_disabled rag_slow
```

## Kết luận

- Root cause: `rag_slow` chạy `time.sleep(2.5)` trong bước retrieval tại `app/mock_rag.py`.
- Fix action trong lab: tắt incident sau khi thu thập evidence.
- Fix production đề xuất: đặt timeout cho vector store, dùng cache và tối ưu truy vấn retrieval.
- Preventive measure: giữ span `rag-retrieve`, cảnh báo latency P95 và theo dõi riêng thời gian retrieval.

## Trace evidence

- Trace ID: `9889ad67b5b1f2750c63397b6c5a22f2`.
- `run`: 2654 ms.
- `rag-retrieve`: 2501 ms.
- `llm-generate`: 152 ms.
- Chi tiết: `submission/evidence/role-e-langfuse-traces.md`.
