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

## Cấu trúc project

```text
AI_Desktop_Assistant_Optimized/
├── main.py
├── tools/
│   ├── system_advisor.py
│   ├── folder_size_analyzer.py
│   ├── large_file_finder.py
│   ├── process_monitor.py
│   ├── download_watcher.py
│   └── ...
├── reports/
├── backups/
├── logs/
├── data/
├── requirements.txt
└── README.md

## Tiến độ hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Cấu trúc project | Done |
| Tool hệ thống cơ bản | Done |
| Download Watcher | Done |
| Storage Analyzer | Done |
| System Advisor | Done |
| README.md | Done |
| Open file location | Next |
| Update main.py | Next |
| Test toàn bộ tool | Next |
| Refactor tools | Later |