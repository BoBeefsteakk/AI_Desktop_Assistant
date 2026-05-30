# Changelog

## 2026-05-30

### Refactor

* Chuẩn hóa cấu trúc thư mục
* Chia module system/storage/search/automation/core

### Core

Thêm:

* risk_classifier.py
* safe_executor.py

### Duplicate Finder

Nâng cấp:

* Risk Classification
* Safe Delete
* Backup Report
* Protected Zone

### Temp Cleaner

Nâng cấp:

* Risk Classification
* Safe Delete
* Report
* Selective Cleanup

### Junk File Cleaner

Nâng cấp:

* Risk Classification
* Safe Executor
* Report

### Browser Cache Cleaner

Nâng cấp:

* Risk Classification cho browser cache
* Safe Executor
* Report
* Audit Log
* Không còn xóa trực tiếp bằng rmtree

### Recycle Bin Cleaner

**thay đổi** Nâng cấp:

* Scan Recycle Bin trước khi empty
* Preview report
* Confirmation flow nhiều bước
* Final report
* Audit Log

### Media Organizer

**thay đổi** Nâng cấp:

* Risk Classification
* Preview và chọn file trước khi move
* Chặn protected path
* Backup manifest
* Report
* Restore report
* Audit Log

### Empty Folder Finder

**thay đổi** Nâng cấp:

* Risk Classification
* Preview và chọn folder trước khi xóa
* Safe Executor
* Report
* Audit Log
* Không còn gọi send2trash trực tiếp

### Download Organizer

**thay đổi** Nâng cấp:

* Risk Classification
* Preview và chọn file trước khi move
* Bỏ qua file đang tải dở
* Backup manifest
* Report
* Restore report
* Audit Log

### Download Watcher

**thay đổi** Nâng cấp nhẹ:

* Giữ nguyên flow watcher hiện có
* Move bằng safe_move
* Audit Log cho từng file tự động move
* Startup scan report khi có thay đổi
* Helper trả về kết quả có cấu trúc để test

### Requirements

**thay đổi** Thêm:

* watchdog

### Main CLI Menu

**thay đổi** Nâng cấp:

* Thêm Temp Cleaner
* Thêm Empty Folder Finder
* Thêm Download Organizer
* Thêm Download Watcher
* Thêm Assistant Logs
* Thêm Behavior Tester
* **thay đổi** Thêm Config Manager
* **thay đổi** Thêm Audit Center
* **thay đổi** Thêm Undo Manager
* **thay đổi** Thêm Full System Tester
* **thay đổi** Thêm WizTree Adapter
* **thay đổi** Thêm External Apps Manager
* **thay đổi** Thêm Capability Registry
* Chuyển Tool Tester sang mục 21

### Tool Tester

**thay đổi** Mở rộng:

* Kiểm tra 28 tool
* Passed: 28
* Failed: 0

### Behavior Tester

**thay đổi** Thêm:

* Sandbox behavior tests
* Risk Classifier và Safe Delete bad cases
* Download Organizer roundtrip
* Download Watcher startup scan
* Media Organizer roundtrip
* Empty Folder Finder fake delete
* Missing manifest restore
* Startup Launcher config audit
* Read-only system snapshots
* Config System snapshot
* Audit Center snapshot
* Undo Manager roundtrip
* **thay đổi** Sandbox name dùng microsecond để tránh collision khi chạy song song
* Passed: 11
* Failed: 0

### Startup Launcher

**thay đổi** Nâng cấp audit:

* Ghi log khi xem profiles
* Report khi thêm app vào profile
* Report khi mở profile
* Lưu trạng thái từng app khi launch
* Behavior test không mở app thật

### Read-only System Tools

**thay đổi** Nâng cấp audit:

* Disk Checker có `get_disk_info`
* Disk Checker tạo report và audit log
* Process Monitor tạo report và audit log khi `show_top_process`
* Behavior Tester kiểm tra snapshot của Disk Checker và Process Monitor

### Config System

**thay đổi** Thêm config tập trung:

* Thêm `config/user_settings.json`
* `config/settings.py` đọc user settings và merge với default an toàn
* Gom Downloads path, default scan folder, thresholds, protected folders
* Gom browser cache path templates, watcher timing, file categories, media extensions
* Risk Classifier dùng protected/safe zone từ config
* Browser Cache Cleaner dùng browser cache templates từ config
* Download Organizer, Download Watcher, Media Organizer dùng category/extension từ config
* Disk Checker và Process Monitor dùng warning/critical threshold từ config
* Thêm `tools/core/config_manager.py`
* **thay đổi** Thêm nhóm `wiztree` cho exe_path, export_dir, timeout, use_admin và tùy chọn dùng trong System Advisor
* **thay đổi** Thêm nhóm `external_apps` cho Everything, smartctl, Sysinternals, 7-Zip, ExifTool, FFmpeg, rclone

### WizTree Adapter

**thay đổi** Thêm adapter WizTree read-only:

* Thêm `tools/storage/wiztree_adapter.py`
* Tự đọc executable từ config, mặc định `D:\WizTree\WizTree\WizTree64.exe`
* Export CSV vào `data/wiztree_exports`
* Parse CSV thành top folders và large files
* System Advisor có thể dùng WizTree để scan nhanh và fallback về Python scanner nếu lỗi
* Full System Tester kiểm tra parser bằng CSV mẫu trong sandbox, không chạy scan thật

### External Apps Integration

**thay đổi** Móc app ngoài vào tool theo hướng read-only:

* Thêm `tools/core/external_apps.py`
* File Indexer và Natural Command dùng Everything CLI để search nhanh, fallback về local index
* Disk Checker đọc thêm SMART health qua smartctl nếu khả dụng
* Media Organizer có chế độ đọc metadata bằng ExifTool/FFprobe, không move file
* Process Monitor ghi nhận Sysinternals helpers sẵn có
* External Apps Manager xem status/version và xuất report

### Capability Registry

**thay đổi** Thêm bản đồ capability chính thức:

* Thêm `tools/core/capability_registry.py`
* Mỗi tool có metadata về category, risk, confirmation, mutates_files, undo_strategy, report/log, external_apps
* Main CLI expose Capability Registry
* Full System Tester kiểm tra Tool Tester entry nào cũng có capability tương ứng
* Full System Tester kiểm tra risk trong registry không lệch với Tool Tester

### Audit System

**thay đổi** Thêm audit nền tảng:

* `create_report()` tự append vào `reports/report_index.jsonl`
* **thay đổi** Report schema v2 có `schema_version`, `action`, `risk_level`, `summary`, `manifest`, `undo_available`, `tags`
* **thay đổi** Report index có thêm `action`, `risk_level`, `summary`, `manifest`, `undo_available`
* **thay đổi** `create_report()` tự suy luận manifest từ results
* **thay đổi** Thêm `validate_report_file()` và `validate_report_data()`
* Report path tự thêm suffix khi trùng timestamp để tránh ghi đè
* Tool Tester chuyển sang dùng `create_report()`
* Thêm `tools/core/audit_center.py`
* Audit Center gom assistant logs và report index thành snapshot
* Main CLI expose Audit Center
* Behavior Tester kiểm tra Audit Center snapshot

### Undo System

**thay đổi** Thêm Undo Manager:

* Thêm `tools/core/undo_manager.py`
* Liệt kê manifest gần đây trong backups
* Preview manifest trước restore
* Restore manifest mặc định chỉ cho file trong backups
* Tạo report và audit log khi restore
* Main CLI expose Undo Manager
* Behavior Tester kiểm tra Undo Manager roundtrip

### Full System Tester

**thay đổi** Thêm test siêu tổng hợp:

* Compile all
* Tool import matrix
* Main menu coverage
* Config health
* Safety static audit
* Risk classifier guardrails
* Report manager và audit index
* **thay đổi** Report schema validation
* Audit Center health
* Undo Manager roundtrip
* Behavior suite subprocess
* **thay đổi** WizTree Adapter sample CSV
* **thay đổi** External Apps Registry
* **thay đổi** Capability Registry coverage
* Dependency health
* Git submodule health
* Passed: 16
* Failed: 0

### Repository Layout

**thay đổi** Dọn vấn đề repo lồng:

* Gỡ gitlink `AI_Desktop_Assistant` khỏi root index
* Move snapshot cũ từ `D:\tool\AI_Desktop_Assistant` vào `D:\tool\backups\AI_Desktop_Assistant_old_20260530_144926`
* Thêm `AI_Desktop_Assistant/` vào `.gitignore`
* Root project active là `D:\tool`

### Testing

Tool Tester:

Passed: 28

Failed: 0

Behavior Tester:

Passed: 11

Failed: 0

Full System Tester:

Passed: 16

Failed: 0

### GitHub

Đã khôi phục project sau khi cài lại Windows.

Toàn bộ thay đổi đã được push lên GitHub.
