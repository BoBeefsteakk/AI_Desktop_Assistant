# Kiến trúc hệ thống AI Desktop Assistant

## Tổng quan

AI Desktop Assistant được thiết kế theo kiến trúc module.

Mục tiêu:

* Dễ mở rộng
* Dễ bảo trì
* Tách biệt nghiệp vụ
* Tăng mức độ an toàn

---

## Cấu trúc thư mục

tools/

├── automation/

├── config/

├── core/

├── search/

├── storage/

└── system/

---

## Vai trò từng nhóm

### core

Chứa các thành phần dùng chung.

Bao gồm:

* assistant_logger.py
* **thay đổi** audit_center.py
* report_manager.py
* risk_classifier.py
* safe_executor.py
* safety_utils.py
* tool_tester.py
* **thay đổi** behavior_tester.py
* **thay đổi** config_manager.py
* **thay đổi** undo_manager.py
* **thay đổi** full_system_tester.py

---

### config

**thay đổi** Chứa cấu hình tập trung.

Bao gồm:

* settings.py: merge default config với user override
* user_settings.json: file người dùng chỉnh Downloads path, threshold, protected folders, browser cache paths, watcher timing

---

### system

Các công cụ hệ thống.

Ví dụ:

* disk_checker
* process_monitor
* recycle_bin_cleaner
* browser_cache_cleaner
* game_booster

---

### storage

Các công cụ liên quan đến dữ liệu.

Ví dụ:

* duplicate_finder
* temp_cleaner
* media_organizer
* folder_size_analyzer
* large_file_finder

---

### search

Tìm kiếm và xử lý truy vấn.

Ví dụ:

* file_indexer
* natural_command

---

### automation

Tự động hóa.

Ví dụ:

* startup_launcher
* download_watcher

---

## Safety Layer

Là thành phần quan trọng nhất.

### Risk Classifier

Chịu trách nhiệm:

* Đánh giá rủi ro
* Phân loại file
* **thay đổi** Đọc protected/safe zones từ config tập trung

Mức độ:

SAFE_DELETE

REVIEW_REQUIRED

PROTECTED

---

### Safe Executor

Mọi thao tác xóa phải đi qua:

safe_delete()

Không được xóa trực tiếp bằng:

* unlink()
* rmtree()
* remove()

---

## Luồng xử lý chuẩn

Scan

↓

Risk Classification

↓

Preview

↓

User Selection

↓

Safe Executor

↓

Recycle Bin

↓

Report

↓

Log

---

## Audit Layer

**thay đổi** Report và log được gom thành nguồn lịch sử chung.

Nguồn dữ liệu:

* `logs/assistant_actions.jsonl`
* `reports/report_index.jsonl`
* Các report chi tiết trong `reports/`

Thành phần chính:

* `report_manager.py`: tạo report và ghi report index
* `assistant_logger.py`: ghi action log dạng JSONL
* `audit_center.py`: đọc log + report index và xuất audit snapshot

---

## Undo Layer

**thay đổi** Undo hiện dựa trên manifest sinh ra khi tool move file.

Nguồn dữ liệu:

* `backups/*_backup_*.json`

Thành phần chính:

* `undo_manager.py`: list, preview, restore manifest
* `safety_utils.restore_from_manifest()`: thực hiện move ngược từ `new_path` về `old_path`
* Report/log: ghi lại kết quả restore

Nguyên tắc:

* Preview trước restore
* Mặc định chỉ nhận manifest nằm trong `backups/`
* Nếu trùng tên tại vị trí cũ, restore tạo hậu tố `_restored_N`

---

## Full Test Layer

**thay đổi** Full System Tester là test tổng hợp cấp hệ thống.

Các lớp kiểm tra:

* Compile/import/menu
* Config
* Safety static audit
* Risk classifier
* Report/audit index
* Undo roundtrip
* Behavior suite
* Dependencies
* Git submodule health

---

## Config Layer

**thay đổi** Các tool không nên hard-code paths/thresholds nếu giá trị đó có thể thay đổi theo máy.

Nguồn cấu hình chính:

* `config/user_settings.json`

Các nhóm đã gom:

* Downloads path
* Default scan folder
* Disk/RAM thresholds
* Protected folders/files
* Browser cache templates
* Download temporary extensions
* File categories
* Media extensions

---

## Nguyên tắc thiết kế

An toàn hơn tốc độ.

Nếu không chắc:

* Không xóa
* Chuyển sang REVIEW_REQUIRED

---

## Hướng phát triển

Hiện tại:

Tool Collection

Mục tiêu:

AI Desktop Assistant

Có khả năng:

* Đánh giá rủi ro
* Đề xuất hành động
* Học từ lịch sử thao tác
