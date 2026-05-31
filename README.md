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
- **thay đổi** Natural Command v2: route lenh tu nhien qua Capability Registry, tu hoi xac nhan voi tool co risk

### Core
- Config Manager
- Audit Center
- Undo Manager
- Full System Tester
- **thay đổi** External Apps Manager
- **thay đổi** Capability Registry
- **thay đổi** Recommendation Center

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
    └── system/
```

## Tiến độ hiện tại

Module	Status
Main CLI Menu	Done
System Tools	Done
Storage Tools	Done
Automation Tools	Done
Search Tools	Done
Core Utilities	Done
Tool Tester	Passed 29/29
Behavior Tester	Passed 14/14
Full System Tester	Passed 18/18
WizTree Adapter	Done
External Apps Integration	Done
Capability Registry	Done
Natural Command v2	Done
System Advisor v2	Done
Recommendation Center	Done
Refactor Tools Folder	Done
Config System	Done
Audit System	Basic Done
Undo System	Basic Done
UI Desktop	Later
