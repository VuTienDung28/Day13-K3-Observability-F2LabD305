# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: API latency SLO breach
- Severity: Critical
- SLI/SLO liên quan: latency_p95_ms, objective 3000 ms, target 99.5%
- Điều kiện và thời gian duy trì: p95 latency > 3000 ms trong 5 phút liên tục
- Ảnh hưởng tới người dùng: phản hồi chậm, tỷ lệ bỏ qua request tăng, trải nghiệm chatbot kém hơn đáng kể
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra `GET /metrics` hoặc dashboard để xác nhận latency_p95/p99 và traffic đang tăng hay không.
  2. Dùng correlation ID hoặc log `response_sent` để so sánh request chậm với request bình thường và tìm xem có span retrieval/LLM nào kéo dài.
  3. Kiểm tra sự kiện mới gần đây như deploy, tăng concurrency, hoặc active incident scenario (ví dụ `rag_slow`).
- Mitigation tạm thời: giảm concurrency, tắt hoặc giảm workload của model/circuit yếu, kích hoạt cache hoặc downgrade sang prompt nhẹ hơn.
- Owner: SRE on-call

## Alert 2

- Tên: API error budget burn
- Severity: Critical
- SLI/SLO liên quan: error_rate_pct, objective 2%, target 99.0%
- Điều kiện và thời gian duy trì: error_rate_pct > 2% trong 10 phút liên tục
- Ảnh hưởng tới người dùng: request thất bại, câu trả lời không trả về hoặc không tin cậy, mất niềm tin vào sản phẩm
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra tỷ lệ lỗi theo `error_type` trong `/metrics` hoặc log `request_failed` để thấy lỗi phổ biến nhất.
  2. Xác minh xem có deployment mới, config sai hoặc dependency upstream gây lỗi.
  3. So sánh trace và log theo correlation ID trong thời gian alert để xác định điểm lỗi chính xác.
- Mitigation tạm thời: rollback phiên bản mới, tắt tính năng đang gây lỗi, hoặc chặn request ở layer gateway cho đến khi stabil lại.
- Owner: Platform backend team

## Alert 3

- Tên: Quality-cost regression
- Severity: Warning
- SLI/SLO liên quan: quality_score_avg, objective 0.75; daily_cost_usd, objective 2.5 USD
- Điều kiện và thời gian duy trì: quality_score_avg < 0.75 trong 15 phút liên tục hoặc total cost vượt 2.5 USD trong 1 ngày
- Ảnh hưởng tới người dùng: câu trả lời kém chất lượng, chi phí vận hành tăng bất thường và có thể đẩy hệ thống tới nguy cơ tài chính
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra `quality_avg` và tổng `cost_usd` trên dashboard để xác nhận xu hướng xấu.
  2. So sánh prompt version, prompt label hoặc cấu hình model mới với baseline trước đó.
  3. Xem log `response_sent` để kiểm tra token đầu vào/đầu ra và các request có quá nhiều prompt/augmentation.
- Mitigation tạm thời: quay lại prompt version cũ, giới hạn output token hay kích hoạt guardrail chi phí, tạm khóa flow quá tốn tài nguyên.
- Owner: AI platform team
