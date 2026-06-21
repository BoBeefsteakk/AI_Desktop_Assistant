# AI Desktop Assistant

AI Desktop Assistant là bộ công cụ local hỗ trợ quản lý file, phân tích hệ thống, tự động hóa tác vụ và đưa ra gợi ý dọn dẹp/tối ưu máy tính.

Active workspace hiện tại là `D:\tool`. Snapshot cũ đã được chuyển vào `D:\tool\backups\AI_Desktop_Assistant_old_20260530_144926` để tránh nhầm lẫn.

## Tính năng hiện có

### System
- Kiểm tra ổ cứng
- Theo dõi process ăn RAM/CPU
- Game Booster an toàn
- System Advisor phân tích tổng quan hệ thống
- **thay đổi** System Advisor v2: snapshot read-only + recommendation có severity và suggested tool
- **thay đổi** Advisor real-run calibration: queue thật lọc report test/contract và giữ snapshot mới nhất

### Storage
- Tìm folder nặng nhất
- Tìm file dung lượng lớn
- Tìm file trùng lặp
- Dọn file rác
- Dọn TEMP
- Dọn Recycle Bin
- Tìm folder rỗng
- **thay đổi** WizTree Adapter: scan dung lượng nhanh qua CSV read-only, không xóa/move

### Automation
- Download Watcher: tự phân loại file tải về theo ngày và loại file
- Media Organizer
- Startup Launcher

### Search
- File Indexer
- **thay đổi** Everything-backed fast search
- Natural Command
- **thay đổi** Natural Command v3: route lệnh qua Capability Registry và điều khiển recommendation queue theo index

### Core
- Config Manager
- Audit Center
- Undo Manager
- Full System Tester
- **thay đổi** External Apps Manager
- **thay đổi** External App Drift Detection: cảnh báo nếu path/app/version helper đổi so với baseline lần trước
- **thay đổi** Capability Registry
- **thay đổi** Recommendation Center
- **thay đổi** Guided Action Runner: mở tool từ recommendation với cổng xác nhận risk, không bypass confirmation của tool thật
- **thay đổi** Action Policy Manager: lưu quyết định keep/move/delete/manual/ignore theo path/context/recommendation trước khi automation đụng file thật
- **thay đổi** Policy Enforcement Gate: Guided Action Runner chặn `ignore_forever` và bắt token mạnh cho `manual_only`/`needs_backup`/`move_later`/`delete_candidate`
- **thay đổi** Candidate Review: review deferred archive/video với policy coverage trước khi lập plan
- **thay đổi** Dry-run Action Planner: lập kế hoạch giữ/review/backup/move sau, không execute cleanup
- **thay đổi** Pre-feed Bundle: đóng gói docs/report summary/policy/queue/readiness thành bundle local để chuẩn bị feed assistant
- **thay đổi** Feed Assistant Readiness
- **thay đổi** AI Bot Controller v2: một entrypoint auto-check tổng, gom recommendation/policy/candidate/plan/readiness thành màn OK/lựa chọn/hủy, có Selection UI/Decision Report read-only và chưa execute file thật
- **thay đổi** Bot Move-later Flow v1: trong Bot Controller, chọn item `move_later`, nhập destination, dry-run rồi apply bằng token `MOVE_SELECTION_V1`
- **thay đổi** Auto Scan Session v1: gom snapshot read-only cho disk/storage/process/external apps/audit để bot có đầu vào tự động.
- **thay đổi** Issue Classifier v1: phân loại snapshot thành issue/action group `manual_review`, `move_later`, `backup_first`, `delete_candidate`, `keep`.
- **thay đổi** Safe Delete Adapter v1: chỉ xử lý selection `delete_candidate`, chỉ cho risk `safe_delete`, dry-run trước và apply bằng token `DELETE_SELECTION_V1` qua Recycle Bin.
- **thay doi** Backup Adapter v1: chi xu ly selection `needs_backup`, copy-only vao `D:\tool\backups\selection_backups\...`, giu nguyen source va apply bang token `BACKUP_SELECTION_V1`.
- **thay doi** Bot Panel UI v2: desktop UI Tkinter theo huong assistant-first, co tab `Assistant` cho issue cards, one-click AI plan, activity log/run history, nut `Chay full demo` bang file gia va tab `Advanced` cho bang decision/report ky thuat.
- **thay đổi** Recommendation Center test-report hygiene: contract/full-system report không làm bẩn queue thật hoặc Feed Readiness
- **thay đổi** Obsidian Exporter v1 Graph Mode: xuất vault Markdown/Canvas tại `D:\tool\obsidian_vault`, có `60_Graph_Nodes` để Obsidian Graph hiện mạng tool/app/report/policy/path
- **thay đổi** Execution Adapter v1: đọc Selection Decision Report hợp lệ, ghi nhận quyết định an toàn dạng record-only, chặn xóa/move/backup thật ở bản v1
- **thay đổi** File Operation Adapter v1: chỉ xử lý `move_later` có destination rõ ràng, token `MOVE_SELECTION_V1`, `safe_move` và manifest restore; delete đi qua Safe Delete Adapter riêng
- **thay đổi** Scenario Tester: chạy fake-file sandbox cho Downloads, media, game data, archive, temp/junk và manifest restore

## Project Structure

```txt
D:\tool/
├── main.py
├── requirements.txt
├── README.md
├── config/
│   ├── settings.py
│   └── user_settings.json
├── reports/
├── logs/
└── tools/
    ├── automation/
    ├── core/
    ├── search/
    ├── storage/
    ├── system/
    └── ui/        # **thay doi** Bot Panel UI
```

## **thay doi** Chay UI de nghiem thu

```powershell
cd /d D:\tool
python -m tools.ui.bot_panel
```

**thay doi** Cach test an toan nhat: mo tab `Assistant`, bam `Chay full demo` de xem tron luong bang file gia. UI se tu tao sandbox, scan, chon de xuat, dry-run/apply backup, dry-run/apply move va dry-run/apply safe cleanup; log tung buoc hien trong tab `Advanced`.

**thay doi** Luong user that sau khi quet: bam `Dung de xuat AI`, bam `Xem ke hoach AI`, doc preview trong `Advanced`, tick `Toi da xem ke hoach`, roi bam `Ap dung ke hoach` neu hop ly.

## Tiến độ hiện tại

**thay đổi** Kế hoạch chuẩn hiện được ghi ở `D:\tool\docs\TOOL_MASTER_PLAN.md`.

Module	Status
Main CLI Menu	Done
System Tools	Done
Storage Tools	Done
Automation Tools	Done
Search Tools	Done
Core Utilities	Done
Tool Tester	**thay doi** Passed 45/45
Scenario Tester	Passed 6/6
Behavior Tester	Passed 18/18
Full System Tester	**thay doi** Passed 37/37
WizTree Adapter	Done
External Apps Integration	Done
External App Drift Detection	Done
Capability Registry	Done
Natural Command v3	Done
System Advisor v2	Done
Recommendation Center	Done
Guided Action Runner	Done
Feed Assistant Readiness	Done
Scenario Tester	Done
Recommendation Queue Review	Done
Pending Storage Review	Done
Action Policy Manager	Done
Policy Enforcement Gate	Done
Candidate Review	Done
Dry-run Action Planner	Done
Pre-feed Bundle	Done
AI Bot Controller	Done
Selection UI / Decision Report	Done
Bot Move-later Flow	**thay đổi** Done
Auto Scan Session	**thay đổi** Done
Issue Classifier	**thay đổi** Done
Safe Delete Adapter	**thay đổi** Done
Backup Adapter	**thay doi** Done
Bot Panel UI	**thay doi** Assistant Dashboard v2 + issue cards + one-click AI plan + readable result/history panels Done
Obsidian Exporter	**thay đổi** Done
Execution Adapter	**thay đổi** Done
File Operation Adapter	**thay đổi** Done
Refactor Tools Folder	Done
Config System	Done
Audit System	Basic Done
Undo System	Basic Done
UI Desktop	**thay doi** Bot Panel UI v2 Done: assistant dashboard + issue cards + one-click plan + full demo
