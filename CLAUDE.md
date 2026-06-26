# Project: AI Desktop Assistant

Local Python tool suite để quản lý file, phân tích hệ thống, và tự động hóa tác vụ trên Windows.

> **Làm việc đa agent (Claude + Codex):** đọc `docs/COLLAB.md` trước mỗi phiên để
> tránh xung đột. Codex đọc `AGENTS.md`. Tuân thủ ownership map + worklog trong COLLAB.md.

## Tech Stack

- **Language:** Python 3.12 (Windows, `py` launcher)
- **UI:** Tkinter (`tools/ui/bot_panel.py`)
- **Key deps:** psutil, send2trash, winshell, pywin32, watchdog
- **External apps (read-only helpers):** Everything, WizTree, smartctl, ExifTool, FFprobe, Sysinternals

## Project Structure

```
D:\tool/
├── main.py                   ← CLI menu (48 tools)
├── requirements.txt
├── config/
│   ├── settings.py
│   └── user_settings.json    ← paths, thresholds, protected folders
├── tools/
│   ├── automation/           ← download watcher, startup launcher
│   ├── core/                 ← bot controller, policy, adapters, testers
│   ├── search/               ← file indexer, natural command
│   ├── storage/              ← duplicate finder, advisor, wiztree adapter
│   ├── system/               ← disk checker, process monitor, game booster
│   └── ui/                   ← bot_panel (Tkinter), startup_window
├── reports/                  ← JSON output từ testers & readiness checks
├── logs/
├── backups/
├── data/
├── docs/
│   └── TOOL_MASTER_PLAN.md   ← architecture & flow chuẩn
└── obsidian_vault/           ← Markdown export để xem graph
```

## Key Commands

```powershell
# Chạy CLI menu
python main.py

# Chạy Bot Panel UI (Tkinter desktop)
python -m tools.ui.bot_panel

# Chạy full test suite
python main.py   # chọn 25 (Full System Tester)

# Autorun watcher (background)
start_download_watcher.bat
```

## Architecture & Flow Chuẩn

Xem chi tiết tại `docs/TOOL_MASTER_PLAN.md`. Tóm tắt:

1. `main.py` hoặc Natural Command → Capability Registry → route tool
2. System Advisor v2 / Auto Scan Session → snapshot read-only
3. Recommendation Center → queue read-only → user review
4. Action Policy Manager → Policy Enforcement Gate → Guided Action Runner
5. Bot Controller (UI) gom toàn bộ flow: scan → issue cards → plan → apply
6. Execution Adapter / File Operation Adapter / Safe Delete Adapter / Backup Adapter xử lý từng action type

## Safety Invariants — KHÔNG ĐƯỢC VI PHẠM

- **Advisor và Recommendation Center** không tự chạy cleanup tool.
- **Guided Action Runner** chỉ mở tool sau khi user nhập token xác nhận; không bypass confirmation.
- **Mọi lệnh xóa** phải đi qua `safe_executor.safe_delete()`. Bot flow phải qua Safe Delete Adapter với risk `safe_delete`.
- **Mọi lệnh move** phải có manifest restore, đi qua `safe_move()` và File Operation Adapter.
- **Backup Adapter** chỉ copy-only vào `D:\tool\backups/`, không xóa source.
- **Execution Adapter v1** ghi record-only, chặn cleanup thật.
- Không dùng `py -3.11` — máy chỉ có Python 3.12.

## Coding Conventions

- Mỗi tool expose một hàm `run_<tool_name>()` làm entry point.
- Tên file và hàm theo snake_case.
- Không tự execute file thật trong dry-run mode; luôn in preview trước.
- Token mạnh (`MOVE_SELECTION_V1`, `DELETE_SELECTION_V1`, `BACKUP_SELECTION_V1`) phải được user nhập rõ ràng trước khi apply.
- Report/log lưu vào `reports/` và `logs/` dưới dạng JSON với timestamp.

## Test Status (2026-06-14)

| Suite | Result |
|---|---|
| Tool Tester | 45/45 pass |
| Behavior Tester | 18/18 pass |
| Scenario Tester | 6/6 pass |
| Full System Tester | 37/37 pass |
| Feed Readiness | 9 pass, 0 warn, 0 fail |

## Do NOT

- Tự deploy hoặc push lên production.
- Thêm confirmation bypass vào bất kỳ adapter nào.
- Xóa hoặc move file thật trong test/dry-run mode.
- Paste passwords, API keys vào code — dùng `config/user_settings.json`.
- Chạy `py -3.11` (không có trên máy này).
