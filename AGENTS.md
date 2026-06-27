# AGENTS.md — Quy tắc chung cho mọi AI agent (Codex, Claude Code, …)

> File này dành cho **Codex** và bất kỳ agent nào không tự đọc `CLAUDE.md`.
> Nội dung quy tắc dự án là **một nguồn duy nhất**: đọc `CLAUDE.md`. File này chỉ
> nhắc lại những điều BẮT BUỘC và trỏ sang quy trình hợp tác.

## Trước khi làm bất cứ việc gì

1. Đọc `CLAUDE.md` — kiến trúc, tech stack, safety invariants, coding conventions.
2. Đọc `docs/PROJECT_STATUS.md` và `docs/ROADMAP.md` — đã làm gì, dự kiến gì.
3. Đọc `docs/COLLAB.md` — cách hai agent làm song song KHÔNG xung đột. **Bắt buộc.**

## Safety invariants — KHÔNG ĐƯỢC VI PHẠM (trích từ CLAUDE.md)

- Mọi lệnh xóa phải đi qua `tools/core/safe_executor.safe_delete()`.
- Mọi lệnh move phải có manifest restore, qua `safe_move()` + File Operation Adapter.
- Không thêm bypass confirmation vào bất kỳ adapter nào.
- Token mạnh (`MOVE_SELECTION_V1`, `DELETE_SELECTION_V1`, `BACKUP_SELECTION_V1`,
  `EXECUTE_SELECTION_V1`) phải do user nhập rõ ràng trước khi apply.
- Không xóa/move file thật trong test/dry-run mode.
- Backup Adapter chỉ copy-only vào `D:\tool\backups/`, không xóa source.
- Máy chỉ có Python 3.12 — không dùng `py -3.11`.
- Không tự deploy/push production; chỉ commit/push khi user yêu cầu.

## Trước khi kết thúc phiên

- Cập nhật `docs/PROJECT_STATUS.md` (đã làm gì) và `docs/COLLAB.md` mục Worklog.
- Chạy test: Tool Tester + Full System Tester phải pass.
- Commit với message rõ ràng. Không push trừ khi user yêu cầu.
