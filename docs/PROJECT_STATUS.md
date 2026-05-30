# Trạng thái dự án AI Desktop Assistant

## Giai đoạn hiện tại

Giai đoạn 2 - Safety Hardening

---

## Mục tiêu dự án

Xây dựng một trợ lý desktop hỗ trợ:

* Quản lý dung lượng ổ đĩa
* Dọn dẹp hệ thống
* Tìm kiếm file
* Tự động hóa tác vụ
* Hướng tới khả năng hỗ trợ ra quyết định bằng AI

Ưu tiên hàng đầu:

An toàn dữ liệu trước khi tối ưu hiệu năng.

---

## Đã hoàn thành

### Refactor kiến trúc

Đã chia hệ thống thành:

* automation
* core
* search
* storage
* system

---

### Safety Layer

Đã bổ sung:

* tools/core/risk_classifier.py
* tools/core/safe_executor.py

Mức rủi ro:

* SAFE_DELETE
* REVIEW_REQUIRED
* PROTECTED

---

### Duplicate Finder

Hoàn thành.

Chức năng:

* Phát hiện file trùng bằng SHA256
* Phân loại rủi ro
* Chặn file protected
* Xóa chọn lọc
* Backup report

---

### Temp Cleaner

Hoàn thành.

Chức năng:

* Quét file temp
* Phân loại rủi ro
* Chọn file trước khi xóa
* Tạo report
* Safe delete

---

### Junk File Cleaner

Hoàn thành.

Chức năng:

* Phân loại file rác
* Risk Classification
* Safe Executor
* Report

---

### Browser Cache Cleaner

Hoàn thành safety hardening.

Chức năng:

* Phát hiện cache Chrome, Edge, Brave, Cốc Cốc, Firefox
* Phân loại rủi ro
* Chặn folder protected
* Đưa cache item vào Recycle Bin qua Safe Executor
* Tạo report
* Ghi audit log

---

### Recycle Bin Cleaner

**thay đổi** Hoàn thành safety hardening.

Chức năng:

* Scan Recycle Bin trước khi empty
* Hiển thị số lượng item và tổng dung lượng
* Tạo preview report trước thao tác nguy hiểm
* Confirmation flow nhiều bước, yêu cầu nhập EMPTY
* Tạo final report sau khi empty thành công
* Ghi audit log cho trạng thái success, cancelled, empty, error

---

### Media Organizer

**thay đổi** Hoàn thành safety hardening.

Chức năng:

* Scan media trước khi move
* Phân loại rủi ro
* Chặn file/folder protected
* Preview và chọn file trước khi gom
* Move bằng safe_move, có manifest để restore
* Tạo report sau khi move
* Restore từ manifest có report và audit log

---

### Empty Folder Finder

**thay đổi** Hoàn thành safety hardening bổ sung.

Chức năng:

* Scan folder rỗng
* Phân loại rủi ro
* Chặn protected path
* Preview và chọn folder trước khi xóa
* Đưa folder rỗng vào Recycle Bin qua Safe Executor
* Tạo report
* Ghi audit log

---

### Download Organizer

**thay đổi** Hoàn thành safety hardening bổ sung.

Chức năng:

* Scan file ở root Downloads trước khi move
* Bỏ qua file đang tải dở như .crdownload, .part, .tmp
* Phân loại file theo ngày và loại file
* Phân loại rủi ro
* Preview và chọn file trước khi sắp xếp
* Move bằng safe_move, có manifest để restore
* Tạo report sau khi move
* Restore từ manifest có report và audit log

---

### Download Watcher

**thay đổi** Hoàn thành audit hardening nhẹ, giữ nguyên flow chạy nền.

Chức năng:

* Giữ nguyên watchdog event handler và logic chờ file ổn định dung lượng
* Bỏ qua file đang tải dở như .crdownload, .part, .tmp
* Move bằng safe_move
* Ghi audit log cho file được move, blocked, error
* Tạo startup scan report khi có file được move/blocked/error
* Trả về kết quả có cấu trúc để test helper mà không cần chạy watcher vô hạn

---

### Tool Tester

**thay đổi** Kết quả hiện tại:

Passed: 28
Failed: 0

---

### WizTree Adapter

**thay đổi** Đã tích hợp WizTree theo hướng read-only adapter.

Chức năng:

* Đọc cấu hình từ `config/user_settings.json`
* Tự nhận `D:\WizTree\WizTree\WizTree64.exe` nếu còn đúng đường dẫn
* Export CSV vào `D:\tool\data\wiztree_exports`
* Parse CSV thành top folders và large files dùng chung với System Advisor
* Không xóa, không move, không thay đổi dữ liệu người dùng
* System Advisor có thể hỏi để dùng WizTree, nếu lỗi thì fallback về Python scanner

---

### External Apps Integration

**thay đổi** Đã thêm lớp tích hợp app ngoài read-only qua `tools/core/external_apps.py`.

Đã móc vào tool:

* Everything CLI dùng cho File Indexer và Natural Command `find ...`, fallback về local index nếu lỗi
* smartctl dùng trong Disk Checker để đọc SMART health nếu có quyền và thiết bị hỗ trợ
* ExifTool và FFprobe dùng trong Media Organizer chế độ đọc metadata riêng, không move file
* Sysinternals được nhận diện trong Process Monitor để report biết có Process Explorer/Handle/RAMMap sẵn
* External Apps Manager hiển thị trạng thái/version và xuất report app ngoài

Nguyên tắc:

* Không app ngoài nào được tự xóa/move dữ liệu
* App ngoài chỉ tăng tốc scan, đọc metadata hoặc bổ sung health snapshot
* Path app ngoài nằm trong `config/user_settings.json`

---

### Capability Registry

**thay đổi** Đã thêm Capability Registry làm bản đồ chính thức cho toàn bộ tool.

Chức năng:

* Thêm `tools/core/capability_registry.py`
* Mỗi tool có metadata: category, module, function, risk, mutates_files, confirmation, undo_strategy, report/log, external_apps, tags, summary
* Main CLI expose `Capability Registry`
* Tool Tester kiểm tra import menu registry
* Full System Tester kiểm tra mọi tool trong Tool Tester đều có capability entry và risk không lệch
* Có thể xuất report capability để assistant đọc sau này

Kết quả hiện tại:

* Capability count: 28
* Categories: automation, core, search, storage, system
* Risk levels: safe, medium, dangerous

---

### Behavior Tester

**thay đổi** Đã bổ sung test hành vi trong sandbox.

Các case đã kiểm tra:

* Protected project file bị safe_delete chặn
* Missing path không gây lỗi
* Download Organizer skip file đang tải dở và restore được manifest
* Download Watcher skip file đang tải dở và move file sẵn sàng
* Media Organizer scan đúng media và restore được manifest
* Empty Folder Finder không chọn folder có file, fake delete không đụng Recycle Bin
* Missing manifest trả về trạng thái missing
* Startup Launcher ghi profile vào sandbox config và tạo audit report
* Disk Checker và Process Monitor trả về snapshot có cấu trúc
* Config System đọc `config/user_settings.json` và validate snapshot
* Audit Center đọc assistant logs và report index
* Undo Manager restore manifest trong sandbox
* **thay đổi** Sandbox test dùng timestamp microsecond để tránh trùng khi chạy song song

Kết quả hiện tại:

Passed: 11
Failed: 0

---

### Startup Launcher Audit

**thay đổi** Đã bổ sung audit/report cho Startup Launcher.

Chức năng:

* Ghi log khi xem profiles
* Ghi log/report khi thêm app vào profile
* Ghi log/report khi mở profile
* Ghi rõ app mở thành công, lỗi mở app, PID nếu có
* Behavior test dùng sandbox config, không mở app thật

---

### Read-only System Tool Audit

**thay đổi** Đã bổ sung audit/report cho Disk Checker và Process Monitor.

Disk Checker:

* Thêm snapshot có cấu trúc qua `get_disk_info`
* Tạo report khi kiểm tra ổ đĩa
* Ghi audit log với số ổ đĩa, warning, critical

Process Monitor:

* Giữ nguyên `get_top_processes`
* Tạo report khi xem top process
* Ghi audit log với limit, sort_by, số process

---

### Main CLI Menu

**thay đổi** Đã expose đầy đủ hơn các tool hiện có.

Đã thêm vào menu chính:

* Temp Cleaner
* Empty Folder Finder
* Download Organizer
* Download Watcher
* Assistant Logs
* Behavior Tester
* Config Manager
* Audit Center
* Undo Manager
* Full System Tester
* **thay đổi** WizTree Adapter
* **thay đổi** External Apps Manager
* **thay đổi** Capability Registry

---

### Config System

**thay đổi** Đã bổ sung config tập trung có file người dùng dễ chỉnh:

* File chỉnh chính: `D:\tool\config\user_settings.json`
* `config/settings.py` tự merge default an toàn với user override
* Gom Downloads path, default scan folder, thresholds, protected folders
* Gom browser cache templates, watcher timing, file categories, media extensions
* **thay đổi** Gom cấu hình WizTree: enabled, exe_path, export_dir, timeout, use_admin, prefer_for_system_advisor
* **thay đổi** Gom cấu hình external_apps: Everything, smartctl, Sysinternals, 7-Zip, ExifTool, FFmpeg, rclone
* Risk Classifier, Browser Cache Cleaner, Download Organizer, Download Watcher, Media Organizer, Disk Checker, Process Monitor, File Indexer dùng config tập trung
* Thêm Config Manager để xem summary, validate và xuất report config

---

### Audit System

**thay đổi** Đã bổ sung nền tảng audit tổng:

* `create_report()` tự ghi index vào `D:\tool\reports\report_index.jsonl`
* **thay đổi** Mỗi report mới dùng schema v2 với `schema_version`, `action`, `risk_level`, `summary`, `manifest`, `undo_available`, `tags`
* Report path tự thêm suffix khi trùng timestamp để tránh ghi đè
* **thay đổi** Report index cũng ghi `action`, `risk_level`, `summary`, `manifest`, `undo_available`
* **thay đổi** `create_report()` tự suy luận manifest từ results để bật `undo_available`
* **thay đổi** Thêm validator `validate_report_file()`
* Tool Tester cũng dùng `create_report()` nên report được đưa vào index chung
* Thêm `tools/core/audit_center.py`
* Audit Center đọc `assistant_actions.jsonl` và `report_index.jsonl`
* Audit Center có thể xuất snapshot report để feed assistant sau này
* Main CLI expose Audit Center

---

### Undo System

**thay đổi** Đã bổ sung nền tảng Undo/Restore tổng:

* Thêm `tools/core/undo_manager.py`
* Scan manifest trong `D:\tool\backups`
* Preview manifest trước khi restore
* Chỉ restore mặc định từ manifest nằm trong backups
* Restore qua manifest có report và audit log
* Behavior Tester kiểm tra Undo Manager Roundtrip trong sandbox
* Main CLI expose Undo Manager

---

### Full System Tester

**thay đổi** Đã bổ sung test siêu tổng hợp:

* Thêm `tools/core/full_system_tester.py`
* Compile toàn bộ `main.py`, `config`, `tools`
* Kiểm tra import/function matrix của mọi tool
* Kiểm tra main menu coverage
* Validate config
* Static safety audit cho active source, bỏ qua backups
* Kiểm tra risk classifier guardrails
* Kiểm tra report manager và audit index
* **thay đổi** Kiểm tra report schema validation
* Kiểm tra Audit Center
* Kiểm tra Undo Manager roundtrip
* Chạy Behavior Tester như subprocess
* Kiểm tra dependency chính
* Kiểm tra `git submodule status`
* **thay đổi** Kiểm tra WizTree Adapter bằng CSV mẫu trong sandbox, không chạy scan thật
* **thay đổi** Kiểm tra External Apps Registry đủ path cấu hình
* **thay đổi** Kiểm tra Capability Registry coverage/risk sync với Tool Tester

Kết quả hiện tại:

Passed: 16
Failed: 0

---

## Công nghệ sử dụng

Python 3.11

Thư viện chính:

* psutil
* send2trash
* watchdog

---

## Repository Layout

**thay đổi** Root project active hiện tại là:

* D:\tool

**thay đổi** Snapshot local cũ đã được chuyển vào backup để root không còn hai bản song song:

* D:\tool\backups\AI_Desktop_Assistant_old_20260530_144926

Lý do:

* Root repo từng track `AI_Desktop_Assistant` như gitlink/submodule
* Không có `.gitmodules`
* `git submodule status` bị lỗi
* Code root mới hơn và có đầy đủ safety hardening
* Người dùng dễ chỉnh/chạy nhầm bản cũ nếu folder lồng còn nằm ở root

---

## Những gì cần làm tiếp

**thay đổi** Các mục chính của Phase 2 Safety Hardening đã hoàn thành cho:

* Duplicate Finder
* Temp Cleaner
* Junk File Cleaner
* Browser Cache Cleaner
* Recycle Bin Cleaner
* Media Organizer
* Download Organizer
* Download Watcher
* Config System
* Audit System nền tảng
* Undo System nền tảng
* Full System Tester
* **thay đổi** WizTree Adapter read-only
* **thay đổi** External Apps Integration
* **thay đổi** Capability Registry

Cần làm tiếp để ổn định tool tổng:

* **thay đổi** Mở rộng Undo System cho các thao tác không có manifest nếu cần
* **thay đổi** Dùng Capability Registry để nâng Natural Command v2
* Bổ sung thêm case vào Full System Tester khi phát hiện lỗi thực tế mới

---

## Các nguyên tắc phát triển

Không được:

* Xóa file trực tiếp
* Bỏ qua safe_executor
* Bỏ qua risk_classifier

Luôn phải:

* Phân loại rủi ro
* Tạo report
* Ghi log
* Hỗ trợ khôi phục khi có thể

---

## Ghi chú cho AI

Trước khi sửa bất kỳ tool cleanup nào:

Luôn đọc:

* ARCHITECTURE.md
* PROJECT_STATUS.md

Mọi thao tác xóa phải đi qua:

safe_executor.py
