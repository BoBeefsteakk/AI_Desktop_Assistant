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
* **thay đổi** capability_registry.py
* report_manager.py
* risk_classifier.py
* safe_executor.py
* safety_utils.py
* **thay đổi** external_apps.py
* tool_tester.py
* **thay đổi** behavior_tester.py
* **thay đổi** config_manager.py
* **thay đổi** undo_manager.py
* **thay đổi** full_system_tester.py
* **thay đổi** recommendation_center.py

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
* **thay đổi** wiztree_adapter
* **thay đổi** system_advisor v2

---

### search

Tìm kiếm và xử lý truy vấn.

Ví dụ:

* file_indexer
* natural_command

**thay đổi** `natural_command.py` hiện là router v2:

* Chuẩn hóa lệnh có dấu/không dấu
* Giữ `find <từ khóa>`/`tim <từ khóa>` cho search nhanh qua File Indexer
* Dùng Capability Registry để tìm tool phù hợp
* Hỏi xác nhận trước khi mở capability có risk medium/dangerous hoặc có thể thay đổi file

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

Report schema v2:

* `schema_version`
* `tool`
* `action`
* `risk_level`
* `status`
* `summary`
* `input`
* `results`
* `manifest`
* `undo_available`
* `recommendations`
* `tags`

---

## Capability Layer

**thay đổi** Capability Registry là bản đồ chính thức để mô tả mọi tool.

Nguồn dữ liệu:

* `tools/core/capability_registry.py`

Mỗi capability ghi:

* `id`
* `name`
* `category`
* `module`
* `function`
* `risk_level`
* `mutates_files`
* `needs_confirmation`
* `undo_strategy`
* `creates_report`
* `logs_action`
* `external_apps`
* `tags`
* `summary`

Full System Tester kiểm tra:

* Mọi tool trong Tool Tester đều có capability entry
* Risk trong capability không lệch với Tool Tester
* Không trùng id/entrypoint
* Field bắt buộc không thiếu

**thay đổi** Natural Command v2 dùng metadata này để quyết định route và mức xác nhận trước khi chạy tool.

**thay đổi** System Advisor v2 dùng metadata này để gắn suggested tool/risk/confirmation vào recommendation, nhưng chỉ gợi ý và không tự chạy tool.

**thay đổi** Recommendation Center dùng metadata này để enrich suggested tool trong queue và giữ nguyên trạng thái suggestion-only.

---

## Advisor Layer

**thay đổi** System Advisor v2 là lớp phân tích read-only trước AI Decision Engine.

Nguồn dữ liệu:

* Storage snapshot: top folders và large files từ Python scanner hoặc WizTree adapter
* Disk snapshot: dung lượng ổ đĩa và SMART health khi `smartctl` sẵn sàng
* Process snapshot: top RAM/CPU process
* External apps snapshot: tool ngoài còn thiếu hay đã sẵn sàng
* Audit snapshot: report/log gần đây

Output:

* Snapshot tổng hợp
* Structured recommendations có `severity`, `suggested_tool_id`, `suggested_tool_risk`
* Report schema v2 với action `analyze_system_v2`

Nguyên tắc:

* Chỉ đọc dữ liệu
* Không xóa/move file
* Không tự chạy cleanup tool
* Tool có risk chỉ được đề xuất để người dùng tự quyết định

---

## Recommendation Layer

**thay đổi** Recommendation Center là hàng đợi đọc-only nằm sau Advisor/Audit.

Nguồn dữ liệu:

* Report index: `reports/report_index.jsonl`
* Report chi tiết của System Advisor v2
* Report warning/error từ các tool khác
* Capability Registry để enrich suggested tool

Output:

* Queue recommendation đã sort theo severity
* Summary theo critical/warning/info
* Report schema v2 với action `export_queue`

Nguyên tắc:

* Không tự chạy tool được đề xuất
* Không xóa/move/sửa file
* Chỉ gom, lọc, xuất report và giúp người dùng chọn bước tiếp theo

## Guided Action Layer

**thay đổi** Guided Action Runner là lớp nối giữa Recommendation Center và tool thật.

Nguồn dữ liệu:

* Queue pending/deferred từ Recommendation Center
* `suggested_tool_id` trong recommendation
* Metadata từ Capability Registry

Output:

* Màn xác nhận risk trước khi mở target tool
* Report `guided_action_runner` cho dry-run hoặc lần mở tool
* Log action để Audit Center đọc lại

Nguyên tắc:

* **thay đổi** Runner không tự cleanup, không tự xóa/move file
* **thay đổi** Runner chỉ mở target tool sau khi user nhập đúng `OPEN`
* **thay đổi** Target tool vẫn giữ confirmation/safety/manifest/report riêng
* **thay đổi** Recommendation không tự thành `handled`; user phải xác nhận sau

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
* Report schema validation
* Undo roundtrip
* Behavior suite
* Dependencies
* Git submodule health
* **thay đổi** External adapter sample parsers như WizTree CSV
* **thay đổi** Guided Action Runner dry-run contract

---

## External Adapter Layer

**thay đổi** Adapter bên ngoài chỉ được dùng để tăng tốc scan/đọc dữ liệu, không được tự xóa hoặc move file.

WizTree Adapter:

* Gọi WizTree CLI để export CSV khi người dùng xác nhận
* Lưu CSV vào `data/wiztree_exports`
* Parse CSV thành dữ liệu top folders và large files
* Có thể cấp dữ liệu cho System Advisor
* Nếu adapter lỗi, tool phải fallback hoặc dừng an toàn

**thay đổi** External Apps Registry:

* `tools/core/external_apps.py` quản lý path, status, version và lệnh gọi app ngoài
* Everything CLI dùng cho search nhanh
* smartctl dùng cho disk health
* ExifTool/FFprobe dùng cho media metadata
* Sysinternals được nhận diện cho process/startup diagnostics
* 7-Zip/rclone sẵn trong registry cho archive/backup flow sau này

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
* **thay đổi** WizTree executable path, export folder, timeout và tùy chọn System Advisor
* **thay đổi** External app paths và default timeout

---

## Nguyên tắc thiết kế

An toàn hơn tốc độ.

Nếu không chắc:

* Không xóa
* Chuyển sang REVIEW_REQUIRED

---

## Hướng phát triển

**thay đổi** Kế hoạch chuẩn sau khi rà lại tool tổng được ghi tại `D:\tool\docs\TOOL_MASTER_PLAN.md`.

Hiện tại:

Tool Collection

Mục tiêu:

AI Desktop Assistant

Có khả năng:

* Đánh giá rủi ro
* Đề xuất hành động
* Học từ lịch sử thao tác
