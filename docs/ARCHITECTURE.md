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
* report_manager.py
* risk_classifier.py
* safe_executor.py
* safety_utils.py
* tool_tester.py

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
