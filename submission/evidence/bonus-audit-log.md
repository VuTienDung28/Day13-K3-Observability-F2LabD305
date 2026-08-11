# Bonus audit log evidence

Nguồn runtime: `data/audit.jsonl` với `AUDIT_LOG_PATH=data/audit.jsonl`.

Kịch bản cost demo sinh đúng bốn control-plane events; request/response thông thường không được ghi vào file audit:

```jsonl
{"event":"config_changed","actor":"control_api","action":"update","resource":"cost_optimization","details":{"before":{"enabled":true,"max_output_tokens":160},"after":{"enabled":false,"max_output_tokens":160}}}
{"event":"incident_changed","actor":"control_api","action":"enable","resource":"incident/cost_spike","details":{"before":false,"after":true}}
{"event":"config_changed","actor":"control_api","action":"update","resource":"cost_optimization","details":{"before":{"enabled":false,"max_output_tokens":160},"after":{"enabled":true,"max_output_tokens":160}}}
{"event":"incident_changed","actor":"control_api","action":"disable","resource":"incident/cost_spike","details":{"before":true,"after":false}}
```

Mỗi record thật còn có `ts` UTC và `correlation_id`; hai trường biến đổi theo từng lần chạy nên được lược khỏi đoạn đối chiếu ổn định ở trên. Test `test_audit_log_contains_only_explicit_control_events` xác minh file riêng chỉ nhận các event điều khiển được gọi rõ ràng.
