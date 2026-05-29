# Roadmap AI Desktop Assistant

## Phase 1 - Refactor

Hoàn thành

* Chia module
* Chuẩn hóa import
* Tool Tester

---

## Phase 2 - Safety Hardening

Đang thực hiện

Đã xong:

* risk_classifier
* safe_executor
* duplicate_finder
* temp_cleaner
* junk_file_cleaner

Cần làm:

* browser_cache_cleaner
* recycle_bin_cleaner
* media_organizer

---

## Phase 3 - Audit System

Mục tiêu:

Lưu lịch sử thao tác.

Dự kiến:

logs/

├── actions.log

└── errors.log

---

## Phase 4 - Undo System

Mục tiêu:

Khôi phục thao tác gần nhất.

Ví dụ:

Undo Cleanup

Restore From Report

---

## Phase 5 - AI Decision Engine

Mục tiêu:

Assistant có thể:

* Phân tích file
* Đề xuất dọn dẹp
* Tự động xử lý SAFE_DELETE

---

## Phase 6 - Desktop UI

Mục tiêu:

Giao diện trực quan.

Bao gồm:

* Dashboard
* Storage View
* Cleanup View
* Reports
* History

---

## Phase 7 - AI Assistant

Mục tiêu cuối cùng.

Ví dụ:

"Dọn cache trình duyệt"

"Tìm file chiếm nhiều dung lượng"

"Cho tôi biết vì sao ổ D đầy"

Assistant tự chọn tool phù hợp và giải thích kết quả.
