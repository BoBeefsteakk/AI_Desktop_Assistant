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

Passed: 31
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

* Capability count: 30
* Categories: automation, core, search, storage, system
* Risk levels: safe, medium, dangerous

---

### Natural Command v3

**thay đổi** Da nang Natural Command tu keyword hard-code sang router dua tren Capability Registry va them dieu khien recommendation queue theo index.

Chuc nang:

* **thay đổi** Chuan hoa lenh co dau/khong dau bang Unicode normalization
* **thay đổi** Giu nguyen flow `find <tu khoa>` va `tim <tu khoa>` qua File Indexer/Everything fallback
* **thay đổi** Route lenh nhu `check disk`, `don cache`, `folder size`, `test tong`, `capability` sang capability tuong ung
* **thay đổi** Tool risk medium/dangerous hoac co the thay doi file se hoi xac nhan truoc khi mo tool
* **thay đổi** Them lenh `xem goi y`, `lam goi y so N`, `hoan muc N`, `danh dau muc N da xu ly`, `bo qua muc N`
* **thay đổi** Lenh mo recommendation theo index di qua Guided Action Runner, khong bypass confirmation
* **thay đổi** Lenh state update chi ghi queue state, khong xoa/move/cleanup
* **thay đổi** Behavior Tester co case rieng de test router ma khong chay thao tac nguy hiem

---

### System Advisor v2

**thay đổi** Đã nâng System Advisor thành bộ phân tích read-only có snapshot tổng hợp và recommendation có cấu trúc.

Chức năng:

* **thay đổi** Gom snapshot từ storage, disk/SMART, process, external apps và audit reports
* **thay đổi** Recommendation có `severity`: critical, warning, info
* **thay đổi** Mỗi recommendation có `suggested_tool_id`, tên tool, risk và trạng thái cần confirmation lấy từ Capability Registry
* **thay đổi** Advisor chỉ gợi ý, không tự chạy cleanup, không xóa, không move
* **thay đổi** Report dùng action `analyze_system_v2`, risk `safe`, tags `system_advisor`, `read_only`, `v2`
* **thay đổi** Behavior Tester và Full System Tester có case riêng kiểm tra contract Advisor v2 bằng dữ liệu giả

---

### Recommendation Center

**thay đổi** Đã thêm Recommendation Center read-only để gom gợi ý từ System Advisor/Audit thành hàng đợi xử lý.

Chức năng:

* **thay đổi** Thêm `tools/core/recommendation_center.py`
* **thay đổi** Đọc report gần đây từ `reports/report_index.jsonl`
* **thay đổi** Lấy structured recommendations từ System Advisor v2
* **thay đổi** Chuyển report `warning/error` thành recommendation cần xem lại qua Audit Center
* **thay đổi** Enrich suggested tool bằng Capability Registry: tên tool, risk, confirmation
* **thay đổi** Chỉ đọc và xuất queue report, không tự chạy cleanup, không xóa/move file
* **thay đổi** Main CLI expose `Recommendation Center`
* **thay đổi** Natural Command route được lệnh gợi ý/queue sang Recommendation Center

* **thay đổi** Recommendation Workflow v1 them queue state persistent tai `data/recommendation_queue.jsonl`
* **thay đổi** Ho tro state `pending`, `deferred`, `handled`, `ignored`
* **thay đổi** Queue mac dinh hien `pending/deferred`, an `handled/ignored`
* **thay đổi** Co the sync queue, loc theo severity/state, doi state va export report queue
* **thay đổi** Van read-only voi du lieu user; chi ghi queue state va report

### Guided Action Runner

**thay đổi** Đã thêm Guided Action Runner để mở tool từ recommendation nhưng vẫn giữ confirmation an toàn.

Chức năng:

* **thay đổi** Thêm `tools/core/guided_action_runner.py`
* **thay đổi** Sync queue `pending/deferred` từ Recommendation Center
* **thay đổi** Resolve `suggested_tool_id` qua Capability Registry
* **thay đổi** Hiển thị target tool, risk, `mutates_files`, `needs_confirmation`, `undo_strategy`, external apps và report gốc
* **thay đổi** Bắt user nhập đúng `OPEN` trước khi mở tool thật
* **thay đổi** Không tự cleanup, không tự xóa/move, không bypass confirmation của tool đích
* **thay đổi** Dry-run tạo report nhưng không execute target tool
* **thay đổi** Recommendation không tự chuyển `handled`; user phải xác nhận sau khi chạy tool đích
* **thay đổi** Main CLI expose `Guided Action Runner` ở mục 30
* **thay đổi** Natural Command route được lệnh `lam goi y`/`mo goi y` sang Guided Action Runner

---

### Advisor Real Run Calibration

**thay đổi** Đã chạy System Advisor thật trên `D:\` theo chế độ read-only.

Kết quả:

* **thay đổi** Sửa lỗi System Advisor crash khi console Windows gặp đường dẫn Unicode/tiếng Việt.
* **thay đổi** Recommendation Center mặc định loại report test/contract khỏi queue thật.
* **thay đổi** Queue mặc định chỉ lấy snapshot mới nhất của `system_advisor`/`external_apps`, tránh duplicate từ report cũ.
* **thay đổi** Queue thật sau calibration có 5 recommendation pending: Downloads nặng, archive lớn, process RAM, video lớn, folder lớn nhất.
* **thay đổi** Behavior Tester và Full System Tester có assertion chống lọt test-tagged reports vào default queue.

---

### External App Path Drift Detection

**thay đổi** Đã hoàn thành drift detection cho External Apps Health v2.

Kết quả:

* **thay đổi** Baseline local nằm ở `D:\tool\data\external_apps_health_state.json` và không commit vào git.
* **thay đổi** Health report phát hiện `path_changed`, `availability_changed`, `version_changed`, `binary_changed`.
* **thay đổi** Drift sinh structured recommendation `source=external_apps_drift` để queue/guided runner đọc được.
* **thay đổi** Health report vẫn read-only: không tự tải app, không tự sửa config, không chạy installer.
* **thay đổi** Real export hiện tại: 16/16 external apps available, drift 0, recommendation 0.
* **thay đổi** Recommendation Center đã đọc buffer lớn hơn trước khi lọc test reports, nên queue thật vẫn giữ 5 recommendation Advisor dù test suite sinh nhiều report.

---

### Feed Assistant Readiness

**thay đổi** Đã hoàn thành tool pre-feed readiness.

Chức năng:

* **thay đổi** Thêm `tools/core/feed_readiness.py`.
* **thay đổi** Main CLI expose `Feed Assistant Readiness` ở mục 31.
* **thay đổi** Kiểm tra config, Capability Registry, External Apps/drift, Recommendation Queue, latest Full System report, recent report schema, audit snapshot và feed source docs.
* **thay đổi** Xuất report `feed_readiness` với schema `feed_readiness_v1`.
* **thay đổi** Chỉ read-only: không feed/train thật, không cleanup, không sửa config/path.
* **thay đổi** Natural Command có thể route các lệnh như `feed assistant`, `feed readiness`, `san sang feed`.

Kết quả mới nhất:

* **thay đổi** Readiness status: ready.
* **thay đổi** Checks: 7 pass, 1 warn, 0 fail.
* **thay đổi** Warning duy nhất: còn 5 pending recommendation thật cần review trước khi automation.
* **thay đổi** Tool Tester pass 31/31.
* **thay đổi** Behavior Tester pass 18/18.
* **thay đổi** Full System Tester pass 21/21.

---

### Recommendation Queue Review

**thay đổi** Đã review queue thật sau khi có Feed Readiness report.

Trạng thái mới:

* **thay đổi** `downloads-folder-heavy`: giữ `pending`; đây là action chính cho `D:\Downloads` nặng 44.02 GB.
* **thay đổi** `large-archive-files`: giữ `pending`; cần mở Large File Finder để review 6 archive/bộ cài lớn khoảng 8.99 GB.
* **thay đổi** `large-video-files`: chuyển `deferred`; chưa tự gom/move video vì cần user chọn nơi lưu.
* **thay đổi** `largest-folder-review`: chuyển `handled`; duplicate ngữ cảnh với Downloads nặng.
* **thay đổi** `heavy-processes`: chuyển `ignored`; `MemCompression` là process hệ thống bình thường, không nên kill/cleanup.

Kết quả:

* **thay đổi** Queue mới nhất: 2 pending, 1 deferred, 1 handled, 1 ignored.
* **thay đổi** Recommendation report: `D:\tool\reports\recommendation_center_20260601_183718.json`.
* **thay đổi** Feed Readiness report: `D:\tool\reports\feed_readiness_20260601_183718.json`.

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
* **thay đổi** Natural Command Router test: route disk/cache/full-test/search/unknown va check confirmation
* **thay đổi** System Advisor v2 Recommendations test: kiểm tra severity, suggested tool và suggestion-only contract
* **thay đổi** Recommendation Center Queue test: kiểm tra collect queue, enrich suggested tool và suggestion-only contract
* **thay đổi** Recommendation Workflow State Transitions test: kiểm tra pending/deferred/handled/ignored trên state file sandbox
* **thay đổi** Guided Action Runner Contract test: kiểm tra resolve suggested tool, target confirmation metadata, dry-run không execute và không auto handled
* **thay đổi** Natural Command v3 Queue Actions test: kiểm tra preview/open/state update theo index, dry-run không execute target tool
* **thay đổi** Recommendation Center default queue test: kiểm tra report test/contract không lọt vào queue thật
* **thay đổi** Sandbox test dùng timestamp microsecond để tránh trùng khi chạy song song

Kết quả hiện tại:

Passed: 18
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
* **thay đổi** Recommendation Center
* **thay đổi** Guided Action Runner

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
* **thay đổi** Kiểm tra System Advisor v2 contract bằng dữ liệu giả
* **thay đổi** Kiểm tra Recommendation Center contract bằng report giả
* **thay đổi** Kiểm tra Guided Action Runner contract bằng report giả và dry-run
* **thay đổi** Kiểm tra Natural Command v3 queue contract bằng report giả và dry-run
* **thay đổi** Kiểm tra Feed Readiness contract
* **thay đổi** Kiểm tra default queue loại test-tagged reports

Kết quả hiện tại:

Passed: 21
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

**thay đổi** Kế hoạch chuẩn sau khi rà lại tool tổng được ghi riêng tại `D:\tool\docs\TOOL_MASTER_PLAN.md`.

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
* **thay đổi** Natural Command v3
* **thay đổi** System Advisor v2
* **thay đổi** Recommendation Center
* **thay đổi** Guided Action Runner
* **thay đổi** Advisor Real Run Calibration
* **thay đổi** External App Path Drift Detection
* **thay đổi** Feed Assistant Readiness

Cần làm tiếp để ổn định tool tổng:

* **thay đổi** Ưu tiên 1: Xử lý 2 pending recommendations còn lại: Downloads nặng và archive/bộ cài lớn
* **thay đổi** Ưu tiên 2: Mở rộng Undo System cho các thao tác không có manifest nếu cần
* **thay đổi** Mở rộng Natural Command v3 thành intent engine sau khi có thêm lịch sử/report để feed assistant
* **thay đổi** Chuẩn hóa Recommendation Center thành queue có trạng thái handled/deferred nếu cần workflow dài hơn
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
