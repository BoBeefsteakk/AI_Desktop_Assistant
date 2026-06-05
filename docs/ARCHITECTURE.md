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
* **thay đổi** action_policy.py
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
* **thay đổi** scenario_tester.py
* **thay đổi** candidate_review.py
* **thay đổi** action_planner.py
* **thay đổi** pre_feed_bundle.py
* **thay đổi** bot_controller.py
* **thay đổi** execution_adapter.py
* **thay đổi** file_operation_adapter.py

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

**thay đổi** `natural_command.py` hiện là router v3:

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

**thay đổi** Natural Command v3 dùng metadata này để quyết định route, mức xác nhận trước khi chạy tool và điều khiển recommendation queue theo index.

**thay đổi** System Advisor v2 dùng metadata này để gắn suggested tool/risk/confirmation vào recommendation, nhưng chỉ gợi ý và không tự chạy tool.

**thay đổi** Recommendation Center dùng metadata này để enrich suggested tool trong queue và giữ nguyên trạng thái suggestion-only.

---

## Action Policy Layer

**thay đổi** Action Policy Manager là lớp ghi nhớ quyết định của user trước khi recommendation được mở thành action thật.

Nguồn dữ liệu:

* **thay đổi** `tools/core/action_policy.py`
* **thay đổi** State local `data/action_policy.jsonl`
* **thay đổi** Report `action_policy` trong `reports/`

Policy ghi:

* **thay đổi** `target_type`: path_exact, path_prefix, path_contains, context, recommendation, file_extension
* **thay đổi** `target`: path/pattern/context/recommendation id
* **thay đổi** `decision`: keep, move_later, delete_candidate, ignore_forever, needs_backup, manual_only
* **thay đổi** `reason`, `source`, `tags`, `active`, `updated_at`

Nguyên tắc:

* **thay đổi** Policy chỉ hướng dẫn quyết định, không tự xóa/move file.
* **thay đổi** `delete_candidate` chỉ là nhãn cần user xác nhận từng file; không đồng nghĩa auto-delete.
* **thay đổi** Game/app-managed/backup context được ưu tiên giữ hoặc review thủ công.
* **thay đổi** Recommendation Center và Feed Readiness đọc policy để giảm đề xuất sai hoặc lặp lại.

---

## Policy Enforcement Gate

**thay đổi** Guided Action Runner đọc `policy_gate` trước khi mở target tool.

Nguyên tắc:

* **thay đổi** `ignore_forever` và `keep` chặn mở action tool từ recommendation.
* **thay đổi** `manual_only` cần token `OPEN_MANUAL`.
* **thay đổi** `needs_backup` cần token `OPEN_BACKUP`.
* **thay đổi** `move_later` cần token `OPEN_MOVE_LATER`.
* **thay đổi** `delete_candidate` cần token `OPEN_DELETE_CANDIDATE`.
* **thay đổi** Dry-run vẫn không execute target tool.

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
* **thay đổi** Action Policy để hiển thị quyết định giữ/hoãn/manual/backup cho recommendation đã biết

Output:

* Queue recommendation đã sort theo severity
* Summary theo critical/warning/info
* Report schema v2 với action `export_queue`

Nguyên tắc:

* Không tự chạy tool được đề xuất
* Không xóa/move/sửa file
* Chỉ gom, lọc, xuất report và giúp người dùng chọn bước tiếp theo
* **thay đổi** Queue mặc định bỏ qua report test/contract và chỉ giữ snapshot mới nhất của các report dạng `system_advisor`/`external_apps`
* **thay đổi** Queue có thể kèm `action_policy_decision`, nhưng vẫn không tự thực thi action.

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

---

## Candidate Review / Action Planner Layer

**thay đổi** Candidate Review và Dry-run Action Planner nằm giữa Action Policy và action thật.

Candidate Review:

* **thay đổi** Đọc Step 3 deferred storage report.
* **thay đổi** Phủ Action Policy lên từng archive/video candidate.
* **thay đổi** Xuất report read-only, không xóa/move file.

Dry-run Action Planner:

* **thay đổi** Chuyển candidate thành kế hoạch keep/manual_review/backup_first/move_later/delete_candidate.
* **thay đổi** `can_execute_now` mặc định là false.
* **thay đổi** Không bật auto delete/move; chỉ tạo plan để user review.

---

## Bot Controller Layer

**thay đổi** AI Bot Controller là lớp orchestrator nằm trên Advisor, Recommendation, Policy, Candidate Review và Action Planner.

Nguồn dữ liệu:

* **thay đổi** Recommendation Queue và Guided Action contexts.
* **thay đổi** Action Policy health.
* **thay đổi** Candidate Review.
* **thay đổi** Dry-run Action Planner.
* **thay đổi** Feed Readiness.
* **thay đổi** Latest reports.

Output:

* **thay đổi** Report `bot_controller` với schema `bot_controller_v2`.
* **thay đổi** Summary tổng: recommendation, candidate, policy, readiness, safe-to-execute, needs-selection, do-not-touch.
* **thay đổi** Decision screen gồm `ok`, `select`, `move_later`, `cancel`, `details`.
* **thay đổi** Selection UI schema `bot_selection_ui_v2`.
* **thay đổi** Selection Decision schema `bot_selection_decision_v2`.
* **thay đổi** Bot Move-later Flow schema `bot_move_later_flow_v1`.

Nguyên tắc:

* **thay đổi** Bot Controller v2 chỉ scan, lập kế hoạch và ghi decision report.
* **thay đổi** `executes_file_operations=false`.
* **thay đổi** `ok` không chạy gì nếu không có item `can_execute_now`.
* **thay đổi** `select` trả Selection UI có mã item và allowed decisions.
* **thay đổi** `move_later` yêu cầu user chọn item, destination, dry-run và token `MOVE_SELECTION_V1` trước khi gọi File Operation Adapter.
* **thay đổi** Selection Decision chỉ ghi ý định; `delete_candidate` không phải lệnh xóa.
* **thay đổi** Nhóm `do_not_touch` bị locked và chỉ được `keep`.
* **thay đổi** Không đụng policy `ignore_forever` hoặc `keep`.
* **thay đổi** Không bypass confirmation/manifest/undo của tool thật.

---

## Execution Adapter Layer

**thay đổi** Execution Adapter là lớp kiểm soát sau Bot Controller, dùng để đọc Selection Decision Report trước khi có bất kỳ action thật nào.

Nguồn dữ liệu:

* **thay đổi** Report `bot_controller` action `export_selection_decision`.
* **thay đổi** Schema input bắt buộc: `bot_selection_decision_v2`.
* **thay đổi** Capability Registry metadata cho tool `execution_adapter`.

Output:

* **thay đổi** Report `execution_adapter` với schema `execution_adapter_v1`.
* **thay đổi** Summary record-only, blocked, invalid, missing path và trạng thái execution.
* **thay đổi** Dry-run report và apply report đều ghi rõ `file_operations_executed=false` ở v1.

Nguyên tắc:

* **thay đổi** `dry_run` chỉ preview, không cần token.
* **thay đổi** `apply` cần token `EXECUTE_SELECTION_V1`.
* **thay đổi** `keep`, `manual_review`, `skip` chỉ được ghi nhận record-only.
* **thay đổi** `needs_backup`, `move_later`, `delete_candidate` bị blocked ở Execution Adapter v1.
* **thay đổi** Execution Adapter không sinh manifest/undo mới vì không trực tiếp chạy file operation.
* **thay đổi** `move_later` phải đi qua File Operation Adapter v1 bên dưới.

---

## File Operation Adapter Layer

**thay đổi** File Operation Adapter là lớp file-operation đầu tiên, nằm dưới Execution Adapter và chỉ xử lý `move_later`.

Nguồn dữ liệu:

* **thay đổi** Report `bot_controller` action `export_selection_decision`.
* **thay đổi** Schema input bắt buộc: `bot_selection_decision_v2`.
* **thay đổi** Destination folder do user/UI chỉ định rõ.

Output:

* **thay đổi** Report `file_operation_adapter` với schema `file_operation_adapter_v1`.
* **thay đổi** Manifest `file_operation_adapter_move_*.json` trong `backups/` khi apply move thành công.
* **thay đổi** Summary moved/blocked/error/not-in-scope để user biết item nào thật sự được move.

Nguyên tắc:

* **thay đổi** Chỉ decision `move_later` được xử lý.
* **thay đổi** Destination phải tồn tại sẵn, là directory, không phải root ổ và không thuộc vùng `PROTECTED`.
* **thay đổi** Source phải là file tồn tại và không thuộc vùng `PROTECTED`.
* **thay đổi** Apply cần token `MOVE_SELECTION_V1`.
* **thay đổi** Move dùng `safe_move()`; restore dùng Undo Manager/manifest.
* **thay đổi** `delete_candidate` và `needs_backup` chưa được execute ở layer này.

---

## Pre-feed Bundle Layer

**thay đổi** Pre-feed Bundle đóng gói context sạch trước feed assistant.

Nguồn bundle:

* **thay đổi** Docs chính.
* **thay đổi** Capability Registry summary/validation.
* **thay đổi** Recommendation Queue.
* **thay đổi** Action Policy health.
* **thay đổi** Candidate Review summary.
* **thay đổi** Dry-run Action Planner summary.
* **thay đổi** Feed Readiness checks.
* **thay đổi** Latest report summaries.

Nguyên tắc:

* **thay đổi** Không đưa raw backups.
* **thay đổi** Không đưa raw logs.
* **thay đổi** Không đọc nội dung file user.
* **thay đổi** Bundle nằm trong `data/feed_bundles/` và không commit vào git.

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
* **thay đổi** Natural Command v3 queue dry-run contract
* **thay đổi** Default recommendation queue không lấy test-tagged reports
* **thay đổi** Scenario Tester contract chạy fake-file sandbox và cleanup guard
* **thay đổi** Action Policy Contract kiểm tra baseline policy, path/context matching và Step 3 coverage
* **thay đổi** Candidate Review, Dry-run Action Planner và Pre-feed Bundle contract
* **thay đổi** AI Bot Controller contract kiểm tra decision screen, Selection UI v2, Selection Decision v2, locked item bị block và OK không execute file trong v2
* **thay đổi** Execution Adapter contract kiểm tra dry-run/apply record-only, block `delete_candidate` và không xóa file sandbox
* **thay đổi** File Operation Adapter contract kiểm tra move file giả trong sandbox, tạo manifest và restore bằng Undo Manager
* **thay đổi** Bot Move-later Flow contract kiểm tra bot tạo decision report, gọi adapter, move file giả và restore manifest
* **thay đổi** Obsidian Exporter contract kiểm tra vault sandbox, index, Mermaid flow, Canvas và safety contract

---

## Scenario Test Layer

**thay đổi** Scenario Tester là lớp test tình huống bằng file giả, dùng trước khi đụng dữ liệu thật.

Nguồn dữ liệu:

* **thay đổi** Sandbox `D:\_ai_desktop_assistant_scenario_tests\run_<timestamp>`
* **thay đổi** Fake Downloads, media, Riot Games, archive/bộ cài, temp/junk và empty folders

Nguyên tắc:

* **thay đổi** Không dùng file thật của user để test xóa/move.
* **thay đổi** Chỉ move/restore trong sandbox và luôn kiểm tra manifest restore.
* **thay đổi** Cleanup sandbox bị khóa bằng path guard, chỉ cho phép trong prefix test.

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

**thay đổi** External App Path Drift Detection:

* **thay đổi** `tools/core/external_apps.py` lưu baseline local tại `data/external_apps_health_state.json`.
* **thay đổi** Baseline được cập nhật khi export External Apps Health report, không commit vào git.
* **thay đổi** Health v2 so sánh baseline với trạng thái hiện tại để phát hiện `path_changed`, `availability_changed`, `version_changed`, `binary_changed`.
* **thay đổi** Drift chỉ tạo report/recommendation read-only; không tự sửa config, không tải app, không chạy installer.
* **thay đổi** Recommendation Center đọc buffer report lớn hơn rồi mới lọc test reports, tránh test report che mất Advisor/External Apps report thật.
* **thay đổi** Recommendation Center lọc test report bằng tag `contract_test`/`full_system`, marker trong `note`/`context`, và linked `source_report` để warning guardrail từ Full System Tester không vào queue thật.

---

## Feed Readiness Layer

**thay đổi** `tools/core/feed_readiness.py` là bước đóng gói pre-feed trước khi tính feed/train assistant.

**thay đổi** Layer này chỉ đọc dữ liệu và xuất report:

* **thay đổi** Validate config và Capability Registry.
* **thay đổi** Đọc External Apps Health + drift baseline.
* **thay đổi** Đọc Recommendation Queue thật.
* **thay đổi** Đọc Action Policy và kiểm tra coverage cho Step 3 deferred items.
* **thay đổi** Đọc latest Candidate Review, Action Planner và Pre-feed Bundle report nếu có.
* **thay đổi** Đọc latest Bot Controller report nếu có.
* **thay đổi** Đọc latest Execution Adapter report nếu có.
* **thay đổi** Đọc latest File Operation Adapter report nếu có.
* **thay đổi** Kiểm tra latest Full System Tester report.
* **thay đổi** Validate schema report gần đây.
* **thay đổi** Liệt kê docs/config/report source nên feed.

**thay đổi** Feed Readiness không tự feed dữ liệu, không train, không chạy cleanup và không sửa file người dùng.

---

## Obsidian Review Layer

**thay đổi** `tools/core/obsidian_exporter.py` nằm sau Feed Readiness/Report Manager như một lớp nhìn tổng thể.

Input:

* **thay đổi** Capability Registry.
* **thay đổi** Recommendation Queue.
* **thay đổi** Action Policy.
* **thay đổi** External Apps Health.
* **thay đổi** Feed Readiness.
* **thay đổi** Recent report index.

Output:

* **thay đổi** Vault Markdown/Canvas tại `D:\tool\obsidian_vault`.
* **thay đổi** Report `obsidian_exporter` schema `obsidian_export_v1`.

Nguyên tắc:

* **thay đổi** Chỉ ghi file trong vault, không scan sâu từng file.
* **thay đổi** Không xóa, không move, không approve action.
* **thay đổi** Mọi thao tác thật vẫn đi qua Bot Controller, File Operation Adapter, Safe Executor, manifest và Undo Manager.

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
