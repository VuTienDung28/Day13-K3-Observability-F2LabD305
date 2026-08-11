# Hướng dẫn Role E — QA, Tracing và điều tra incident

Tài liệu này dành cho người mới. Làm lần lượt từ trên xuống và không commit file `.env`.

## 1. Role E phải bàn giao những gì?

- Kết quả chạy toàn bộ test.
- Tối thiểu 10 traces trên Langfuse.
- Một trace waterfall có span cha và hai span con `rag-retrieve`, `llm-generate`.
- Hai prompt version dùng labels `baseline` và `candidate`.
- Bằng chứng chuyển label `production` và rollback.
- Điều tra challenge theo luồng Metrics → Trace → Log → Root cause.
- Hoàn thiện `submission/REPORT.md` và chuẩn bị demo.

## 2. Chuẩn bị môi trường

Mở PowerShell tại thư mục repo:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
```

Kết quả hiện tại phải là `67 passed`. Hai cảnh báo `on_event is deprecated` không làm bài test thất bại.

## 3. Cấu hình Langfuse

Mở `.env` và điền key do Lab Coach cung cấp:

```dotenv
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PROMPT_NAME=day13-chat
LANGFUSE_PROMPT_LABEL=production
```

Không chụp hoặc commit secret key. Khi gọi `/health`, trường `tracing_enabled` phải là `true`.

## 4. Tạo hai prompt version trên Langfuse

Tạo text prompt tên `day13-chat`.

Version 1, gắn labels `baseline` và `production`:

```text
Feature={{feature}}
Docs={{docs}}
Question={{message}}
```

Version 2, gắn label `candidate`; chỉ thay đổi nhỏ về định dạng nhưng phải giữ đủ ba biến:

```text
Feature={{feature}}
Use the following docs:
{{docs}}
Answer briefly: {{message}}
```

Chụp màn hình danh sách hai version và lưu vào `submission/evidence/`.

## 5. Chạy API và tạo traces

Máy kiểm tra hiện có ứng dụng khác dùng cổng 8000, nên ví dụ dưới đây dùng cổng 8001.

Terminal 1:

```powershell
$env:LANGFUSE_PROMPT_LABEL="baseline"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001 --env-file .env
```

Terminal 2:

```powershell
$env:DAY13_BASE_URL="http://127.0.0.1:8001"
.\.venv\Scripts\python.exe scripts\load_test.py
```

Một lần load test thường tạo 10 request. Mở Langfuse và kiểm tra trace có:

```text
run
├── rag-retrieve
└── llm-generate
```

Metadata trace phải có `correlation_id`, `prompt_name`, `prompt_label`, `prompt_version` và `prompt_source=langfuse`.

Để tạo trace cho version 2, dừng API bằng `Ctrl+C`, đổi label rồi chạy lại:

```powershell
$env:LANGFUSE_PROMPT_LABEL="candidate"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001 --env-file .env
```

Gửi lại đúng một input đã dùng với `baseline`. Ghi hai trace ID vào `submission/REPORT.md`.

## 6. Chuyển production và rollback

Trên Langfuse:

1. Chuyển label `production` từ version 1 sang version 2.
2. Chụp màn hình và gửi một request với label `production`.
3. Chuyển `production` trở lại version 1.
4. Chụp màn hình sau rollback.

Điểm nằm ở khả năng truy vết và rollback, không phải prompt nào trả lời hay hơn.

## 7. Chạy challenge chính thức

Đảm bảo API vẫn chạy. Tại Terminal 2:

```powershell
$env:DAY13_BASE_URL="http://127.0.0.1:8001"
.\.venv\Scripts\python.exe scripts\load_test.py --concurrency 5
Invoke-RestMethod "$env:DAY13_BASE_URL/metrics"
.\.venv\Scripts\python.exe scripts\inject_incident.py
.\.venv\Scripts\python.exe scripts\load_test.py --challenge --concurrency 5
Invoke-RestMethod "$env:DAY13_BASE_URL/metrics"
.\.venv\Scripts\python.exe scripts\inject_incident.py --disable
.\.venv\Scripts\python.exe scripts\validate_logs.py
```

Lần chạy có Langfuse tracing ngày 2026-08-11 cho kết quả:

- Challenge P95: 2652 ms.
- Ngưỡng challenge: 2000 ms.
- Error rate: 0%.
- Correlation ID mẫu: `rolee-new-challenge-01`.
- Trace ID: `9889ad67b5b1f2750c63397b6c5a22f2`.
- Span `rag-retrieve`: 2501 ms; span `llm-generate`: 152 ms.
- Root cause: scenario `rag_slow` làm RAG ngủ 2.5 giây trong `app/mock_rag.py`.

Mở trace bằng trace ID hoặc correlation ID trên để chụp waterfall. Span `rag-retrieve` chiếm khoảng 2.5 giây.

## 8. Evidence phải chụp

Lưu trong `submission/evidence/`:

- `role-e-trace-list.png`: danh sách ít nhất 10 traces.
- `role-e-trace-waterfall.png`: trace có RAG và LLM span.
- `role-e-prompt-versions.png`: hai prompt versions.
- `role-e-prompt-baseline-trace.png`: metadata trace baseline.
- `role-e-prompt-candidate-trace.png`: metadata trace candidate.
- `role-e-prompt-rollback.png`: bằng chứng rollback production.
- `role-e-challenge-metrics.png`: metrics khi incident.
- `role-e-challenge-trace.png`: trace RAG chậm.

Cuối cùng điền trace ID, đường dẫn ảnh và commit SHA thật vào `submission/REPORT.md`.
