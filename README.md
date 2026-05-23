# AI Desktop Assistant

AI Desktop Assistant là bộ công cụ local hỗ trợ quản lý file, phân tích hệ thống, tự động hóa tác vụ và đưa ra gợi ý dọn dẹp/tối ưu máy tính.

## Tính năng hiện có

### System
- Kiểm tra ổ cứng
- Theo dõi process ăn RAM/CPU
- Game Booster an toàn
- System Advisor phân tích tổng quan hệ thống

### Storage
- Tìm folder nặng nhất
- Tìm file dung lượng lớn
- Tìm file trùng lặp
- Dọn file rác
- Dọn TEMP
- Dọn Recycle Bin
- Tìm folder rỗng

### Automation
- Download Watcher: tự phân loại file tải về theo ngày và loại file
- Media Organizer
- Startup Launcher

### Search
- File Indexer
- Natural Command

## Project Structure

```txt
AI_Desktop_Assistant/
├── main.py
├── requirements.txt
├── README.md
├── config/
│   └── settings.py
├── reports/
├── logs/
└── tools/
    ├── automation/
    ├── core/
    ├── search/
    ├── storage/
    └── system/

## Tiến độ hiện tại

Module	Status
Main CLI Menu	Done
System Tools	Done
Storage Tools	Done
Automation Tools	Done
Search Tools	Done
Core Utilities	Done
Tool Tester	Passed 15/15
Refactor Tools Folder	Done
Config System	Next
UI Desktop	Later