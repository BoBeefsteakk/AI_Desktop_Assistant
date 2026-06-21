# Roadmap AI Desktop Assistant

**thay doi** Ban handoff tong hop moi nhat nam tai `D:\tool\docs\AI_ASSISTANT_HANDOFF_2026_06_15.md`. Doc file nay truoc khi tiep tuc build AI Assistant.

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
* **thay đổi** AI Bot Controller v2: entrypoint bot tổng cho auto-check, decision screen OK/lựa chọn/hủy/details, Selection UI/Decision Report, hiện vẫn không execute file
* **thay đổi** Execution Adapter v1: đọc Selection Decision Report, record-only quyết định an toàn, chặn xóa/move/backup thật
* **thay đổi** File Operation Adapter v1: move `move_later` với destination rõ ràng, token `MOVE_SELECTION_V1`, `safe_move` và manifest restore
* **thay đổi** Bot Move-later Flow v1: chọn item và destination ngay trong Bot Controller, dry-run rồi apply bằng token
* **thay đổi** Recommendation Center test-report hygiene: lọc contract/full-system report bằng tag, marker và linked source report để queue thật không bị warning giả
* **thay đổi** Obsidian Exporter v1 Graph Mode: xuất vault Markdown/Canvas và graph nodes review-only tại `D:\tool\obsidian_vault`
* **thay đổi** Auto Scan Session v1: gom snapshot read-only cho bot.
* **thay đổi** Issue Classifier v1: phân loại snapshot thành issue/action group.
* **thay đổi** Safe Delete Adapter v1: xóa token-gated chỉ cho `risk=safe_delete` qua Recycle Bin.
* **thay doi** Backup Adapter v1: copy-only cho `needs_backup`, source duoc giu nguyen, apply token-gated bang `BACKUP_SELECTION_V1`.
* **thay doi** Bot Panel UI v2: desktop UI Tkinter theo huong assistant-first, co tab `Assistant` cho status/issue cards/one-click AI plan/activity log/run history/full demo va tab `Advanced` cho raw decision/report/step log.
* **thay doi** Bot Panel UI readability fix: `Ket qua gan nhat` duoc uu tien layout de doc summary, `Lich su gan day` la khung phu, va contract test da bao phu run history panel.

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
* **thay đổi** AI Bot Controller Contract test
* **thay đổi** Selection UI / Decision Report Contract test: validate mã item, locked item và decision report không execute
* **thay đổi** Execution Adapter Contract test: dry-run/apply record-only, block delete_candidate và không xóa file sandbox
* **thay đổi** File Operation Adapter Contract test: move file giả trong sandbox, tạo manifest và restore bằng Undo Manager
* **thay đổi** Bot Move-later Flow Contract test: bot tạo decision report, gọi adapter, move file giả và restore manifest
* **thay đổi** Obsidian Exporter Contract test: tạo vault trong sandbox, kiểm tra index, Mermaid flow, Canvas và safety contract
* **thay đổi** Auto Scan + Issue Classifier Contract test: snapshot giả tạo issue `delete_candidate`, `move_later`, `backup_first`.
* **thay đổi** Safe Delete Adapter Contract test: dry-run không xóa, thiếu token không xóa, token đúng chỉ xóa file giả `safe_delete` và chặn file `review_required`.
* **thay đổi** Bot Safe-delete Flow Contract test: bot tạo decision report, gọi Safe Delete Adapter, dry-run trước và apply bằng token.
* **thay doi** Bot Panel UI Contract test: kiem tra entrypoint, checkbox confirm UI va adapter token safety contract ma khong mo cua so UI.
* **thay doi** Full System Tester hien pass 37/37 tai `D:\tool\reports\full_system_tester_20260611_204703.json`

---

## Phase 5 - AI Decision Engine

**thay doi** Da co AI Bot Controller v2, Selection UI / Decision Report, Execution Adapter v1 record-only, Backup Adapter v1, File Operation Adapter v1, Bot Backup Flow v1, Bot Move-later Flow v1, Auto Scan Session v1, Issue Classifier v1, Safe Delete Adapter v1, Bot Panel UI v2 va Obsidian Exporter v1.

Mục tiêu:

Assistant có thể:

* Phân tích file
* Đề xuất dọn dẹp
* **thay đổi** Ghi nhớ chính sách user trước khi đề xuất/xử lý
* **thay đổi** SAFE_DELETE đã có adapter riêng nhưng vẫn không “OK là xóa luôn”: cần selection rõ, dry-run và token `DELETE_SELECTION_V1`
* **thay đổi** Bot Controller v2 đã gom queue/policy/candidate/plan/readiness thành một màn quyết định và export decision report, nhưng chưa execute file thật
* **thay đổi** Execution Adapter v1 đã có final token và report, nhưng vẫn chưa bật manifest/undo mới vì chưa chạy file operation thật
* **thay đổi** File Operation Adapter v1 đã move được `move_later` trong sandbox với manifest restore
* **thay đổi** Bot Controller đã gọi được File Operation Adapter qua flow riêng, có destination và dry-run trước apply
* **thay đổi** Bot Controller đã gọi được Safe Delete Adapter qua flow riêng, chỉ xóa file giả `risk=safe_delete` sau token.
* **thay doi** Bot Panel UI v2 da co folder picker, demo sandbox, full demo, one-click AI plan, activity log, Assistant Dashboard, issue cards, `needs_backup` backup copy-only, `move_later` destination picker, Undo last move va safe-delete flow. Buoc tiep theo la run history/latest report preview va UI polish de dat moc nghiem thu 90%.

---

## Phase 6 - Desktop UI

**thay doi** Trang thai: Bot Panel UI v2 Done cho nghiem thu flow assistant/issue cards/one-click AI plan/full demo/backup/move_later/safe-delete.

Muc tieu tiep theo:

Giao dien truc quan day du hon.

Bao gồm:

* **thay doi** Dashboard
* **thay doi** Storage View
* **thay doi** Cleanup View
* **thay doi** Reports
* **thay doi** History
* **thay doi** Dashboard tong hop issue + run history + latest reports preview
* **thay doi** Needs-backup flow

---

## Phase 7 - AI Assistant

Mục tiêu cuối cùng.

Ví dụ:

"Dọn cache trình duyệt"

"Tìm file chiếm nhiều dung lượng"

"Cho tôi biết vì sao ổ D đầy"

Assistant tự chọn tool phù hợp và giải thích kết quả.
