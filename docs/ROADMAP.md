# Roadmap AI Desktop Assistant

## Phase 1 - Refactor

Hoàn thành

* Chia module
* Chuẩn hóa import
* Tool Tester

---

## Phase 2 - Safety Hardening

**thay đổi** Các mục chính đã hoàn thành.

**thay đổi** Kế hoạch chuẩn sau khi rà lại tool tổng được ghi tại `D:\tool\docs\TOOL_MASTER_PLAN.md`.

Đã xong:

* risk_classifier
* safe_executor
* duplicate_finder
* temp_cleaner
* junk_file_cleaner
* browser_cache_cleaner
* **thay đổi** recycle_bin_cleaner
* **thay đổi** media_organizer
* **thay đổi** empty_folder_finder
* **thay đổi** download_organizer
* **thay đổi** download_watcher
* **thay đổi** main CLI menu expose đầy đủ hơn
* **thay đổi** behavior_tester sandbox
* **thay đổi** bỏ tracking gitlink AI_Desktop_Assistant bị thiếu .gitmodules
* **thay đổi** move snapshot cũ vào D:\tool\backups để tránh nhầm bản
* **thay đổi** startup_launcher audit/report
* **thay đổi** disk_checker và process_monitor audit/report
* **thay đổi** config system với `config/user_settings.json`
* **thay đổi** Config Manager trong main CLI
* **thay đổi** Audit Center và report index nền tảng
* **thay đổi** Undo Manager nền tảng
* **thay đổi** Full System Tester siêu tổng hợp
* **thay đổi** WizTree Adapter read-only để scan dung lượng nhanh qua CSV
* **thay đổi** External Apps Integration cho Everything, smartctl, Sysinternals, ExifTool, FFmpeg, rclone
* **thay đổi** Capability Registry cho toàn bộ tool
* **thay đổi** Natural Command v3 route lệnh qua Capability Registry, confirmation theo risk và điều khiển recommendation queue theo index
* **thay đổi** System Advisor v2 read-only snapshot + structured recommendations
* **thay đổi** Recommendation Center read-only gom gợi ý từ Advisor/Audit thành queue
* **thay đổi** Recommendation Workflow v1 có trạng thái pending/deferred/handled/ignored
* **thay đổi** Guided Action Runner mở tool từ recommendation qua xác nhận `OPEN`, không bypass confirmation
* **thay đổi** Advisor real run calibration lượt đầu trên `D:\`, đã lọc report test khỏi queue thật
* **thay đổi** External App Health path drift detection với baseline local và structured drift recommendations
* **thay đổi** Feed Assistant Readiness report/checklist trước feed/train
* **thay đổi** Review Recommendation Queue thật và scan storage pending bằng read-only report
* **thay đổi** Scenario Tester fake-file sandbox cho các case xóa/move dễ gây nhầm
* **thay đổi** Action Policy Manager để ghi nhớ quyết định keep/move/delete/manual/ignore theo path/context/recommendation
* **thay đổi** Policy Enforcement Gate trong Guided Action Runner
* **thay đổi** Candidate Review Report cho deferred archive/video
* **thay đổi** Dry-run Action Planner trước khi chạy thật
* **thay đổi** Pre-feed Bundle để đóng gói context sạch trước feed assistant

Cần rà soát tiếp:

* **thay đổi** Không test cleanup trên file thật khi chưa cần; nếu gặp case mới thì tái hiện trước trong Scenario Tester bằng file giả.
* **thay đổi** User quyết định chính sách cụ thể cho archive/bộ cài/video thật nếu muốn giải phóng dung lượng; `Riot Games` hiện được policy `ignore_forever`.

---

## Phase 3 - Audit System

**thay đổi** Basic Done.

Mục tiêu:

Lưu lịch sử thao tác/report theo một chuẩn dễ đọc cho tool tổng và assistant sau này.

Dự kiến:

logs/

├── assistant_actions.jsonl

reports/

└── report_index.jsonl

Đã có:

* `create_report()` tự append report index
* **thay đổi** Report schema v2
* **thay đổi** Report schema validation trong Full System Tester
* Audit Center xem log/report gần đây
* Audit Center export snapshot report

---

## Phase 4 - Undo System

**thay đổi** Basic Done.

Mục tiêu:

Khôi phục thao tác gần nhất.

Ví dụ:

Undo Cleanup

Restore From Report

Đã có:

* Undo Manager đọc manifest trong backups
* Preview manifest
* Restore manifest có report/log
* Behavior test roundtrip

---

## Phase 4.5 - Full System Test

**thay đổi** Basic Done.

Mục tiêu:

Một lệnh test tổng hợp trước khi refactor lớn hoặc feed assistant.

Đã có:

* Compile/import/config/safety/report/audit/undo/behavior/dependency/git checks
* **thay đổi** Report schema validation
* **thay đổi** WizTree Adapter sample CSV test
* **thay đổi** External Apps Registry test
* **thay đổi** Capability Registry coverage/risk sync test
* **thay đổi** Natural Command Router test nằm trong Behavior Tester
* **thay đổi** System Advisor v2 Contract test
* **thay đổi** Recommendation Center Contract test
* **thay đổi** Guided Action Runner Contract test
* **thay đổi** Natural Command v3 Queue Contract test
* **thay đổi** Feed Readiness Contract test
* **thay đổi** Scenario Tester Contract test chạy fake-file sandbox
* **thay đổi** Default queue excludes test-tagged reports
* **thay đổi** Action Policy Contract test
* **thay đổi** Candidate Review, Dry-run Action Planner và Pre-feed Bundle Contract test
* Full System Tester hiện pass 26/26

---

## Phase 5 - AI Decision Engine

Mục tiêu:

Assistant có thể:

* Phân tích file
* Đề xuất dọn dẹp
* **thay đổi** Ghi nhớ chính sách user trước khi đề xuất/xử lý
* **thay đổi** Chưa tự động xử lý SAFE_DELETE ở mốc hiện tại; cần policy gate + candidate review + dry-run plan + confirm rõ trước khi mở rộng

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
