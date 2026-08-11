# Role E — Prompt versioning and rollback evidence

Prompt name: `day13-chat`

## Hai version

| Version | Labels cuối cùng | Nội dung chính |
|---:|---|---|
| 1 | `baseline`, `production` | Contract gốc gồm Feature, Docs, Question |
| 2 | `candidate` | Tách phần docs và yêu cầu câu trả lời ngắn |

## Trình tự deployment

1. Trạng thái ban đầu sau khi tạo candidate: `baseline=v1`, `candidate=v2`, `production=v1`.
2. Promote candidate: `production=v2`.
3. Trace xác minh promote: `a49c7175c36916e91a127df5de850f24`, metadata `production`, version `2`.
4. Rollback: chuyển `production` về version 1.
5. Trạng thái cuối: `baseline=v1`, `candidate=v2`, `production=v1`.
6. Trace xác minh rollback: `505d1e5e25f1fa25d08db2cccd1cf1af`, metadata `production`, version `1`.

Prompt labels đã được đọc lại từ Langfuse API sau mỗi lần chuyển. Không có secret key nào được ghi vào evidence.
