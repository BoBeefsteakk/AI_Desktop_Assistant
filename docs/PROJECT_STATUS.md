# Trạng thái dự án AI Desktop Assistant

## Giai đoạn hiện tại

**thay doi (2026-06-27) Phase 7 backend REQ#6:** Da them public
`tools.core.one_click_cleanup.build_one_click_cleanup_plan(...)`, schema
`one_click_cleanup_plan_v1`. Plan doc selection session hien co, reclassify tung
path qua Risk Classifier + cleanup rule registry, gop duplicate va chi giu file
`safe_delete` dang ton tai. Output co `files`, `count`, `total_size`,
`summary_text`, `severity`, `selection_decisions` va safety contract read-only.
Verify: Behavior 18/18, Tool 48/48, Full System 40/40.

**thay doi (2026-06-27) Phase 7 backend REQ#3 + REQ#4 + REQ#5:** Da co
periodic read-only scan public `run_periodic_scan(...)`, schema
`periodic_scan_notification_v1`, so sanh baseline de bao issue moi va severity
cao nhat. Moi selection item co `reason_text` tieng Viet. Rule risk -> cleanup
decision duoc gom tai `tools/core/cleanup_rules.py`; chi `safe_delete` moi duoc
de xuat `delete_candidate`, `review_required` luon xem tay, `protected` luon
giu. Tai lieu boundary: `docs/FILE_CLEANUP_RULES.md`. Verify: Behavior 18/18,
Tool 48/48, Full System 39/39.

**thay doi (2026-06-27) Phase 7 backend REQ#1 + REQ#2:** System Advisor
them `explanation` cho moi recommendation va `disk_full_reason` o cap ket qua.
Natural Command them public API `answer_user_question(text) -> dict`, schema
`natural_command_answer_v1`, tra loi cau hoi ve o dia day, file/folder lon va
noi dung can don. Toan bo luong moi la read-only, khong xoa/move file va khong
doi chu ky public UI dang goi. Verify: Behavior Tester 18/18, Tool Tester
48/48, Full System Tester 37/37.

**thay doi (2026-06-27) Phase 7 Buoc 1 - Don nhanh inline (branch `claude/ui-inline-delete`):** Them panel "Don nhanh - chon muc roi bam Xoa hoac Giu" tren tab Tro ly cua `tools/ui/bot_panel.py`. Liet ke chi cac file rac AI THUC SU khuyen nghi xoa (`recommended_decision == "delete_candidate"`, tuc risk safe_delete), user chon dong roi bam [Xoa muc da chon] (1 popup xac nhan) hoac [Giu muc da chon]. Nut Xoa chay y het luong safe-delete cu: dry-run -> apply token `DELETE_SELECTION_V1` -> Recycle Bin, sau do tu quet lai. Backend GIU NGUYEN (UI chi goi `export_safe_delete_selection_flow_report`). Da test end-to-end tren file gia: file vao Recycle Bin OK. Tool Tester 48/48, Full System Tester 37/37.

**thay doi (2026-06-27) Codex x Claude collaboration bridge:** Da tao branch
`codex/backend-collab-bridge`, doc lai `AGENTS.md`, `CLAUDE.md`,
`docs/COLLAB.md`, `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, va them mailbox
chung `.agents/AGENT_MAILBOX.md` de Codex/Claude de lai request, handoff, canh
bao doi API. Buoc nay chi ket noi phoi hop agent, khong sua backend logic/UI.

**thay doi (2026-06-25) Advisory Dashboard v1 - huong toi dich cuoi Phase 7:** Bot Panel UI (`tools/ui/bot_panel.py`) gio tu dong kiem tra may khi mo app va tu van suc khoe o cung bang tieng Viet, dung muc tieu user: "AI tu dong chay full tool, tu van file rac/file nang, user chi chon xoa hoac giu".

Da lam duoc:
- **Tu quet khi mo app:** `auto_start_scan()` chay sau khi cua so ve xong (`root.after`), khong can user bam gi. Read-only, khong dung file.
- **Storage mode mac dinh storage-aware:** `default_storage_mode()` uu tien WizTree (fallback Python) thay vi `light`, nen file nang/file rac hien ngay.
- **Panel "Suc khoe o cung & tu van cua AI":** `update_health_panel()` doc snapshot tu auto-scan, hien O DIA (% dung, con trong, trang thai), SMART, FILE NANG, THU MUC LON NHAT, va AI TU VAN theo muc do (NGHIEM TRONG/CANH BAO/Thong tin).
- **Phan biet ro DEMO vs MAY THAT:** nhan mau "Dang xem: MAY THAT" (xanh) / "Dang xem: DU LIEU THU" (vang); nut doi ten "Kiem tra may that" (nut chinh) / "Xem thu (file gia)" / "Chay demo toan bo".
- **UI hien dai bang ttkbootstrap (theme `cosmo`):** header thanh mau, nut co mau theo chuc nang, issue cards vien mau. Da them `ttkbootstrap` vao `requirements.txt`. Fix gotcha `ttk.LabelFrame` -> alias `ttk.Labelframe`.
- **Backend giu nguyen:** moi thao tac van qua Selection Decision Report + token (`BACKUP_SELECTION_V1`/`MOVE_SELECTION_V1`/`DELETE_SELECTION_V1`) + Recycle Bin. UI chi reskin + auto-scan, khong viet logic xoa/move moi.

**thay doi (2026-06-25) Fix marketingskills gitlink:** `marketingskills` truoc day bi track nhu gitlink mo coi (thieu `.gitmodules`) lam `git submodule status` fail va keo Full System Tester con 36/37. Da go `.git` long, chuyen thanh ~381 file thuong duoc track. Gitlink mo coi con lai: 0.

**thay doi Moc verify moi nhat (2026-06-25):** Tool Tester 48/48; Full System Tester 37/37 `D:\tool\reports\full_system_tester_20260625_001228.json`; Feed Readiness 9 pass, 0 warn, 0 fail.

**thay doi Startup/Boot v1:** da co `tools/core/startup_scan.py` (boot scan full o -> issue classifier -> man tu van 3 lua chon: khong xoa / chon file / xoa tat ca an toan, route qua Safe Delete flow), `tools/ui/startup_window.py` (man Decision Inbox do hoa 3 nut, menu 48), `tools/automation/startup_registration.py` (bat/tat tu chay khi khoi dong qua shell:startup launcher, go duoc, menu 47) va `tools/automation/boot_runner.py` (entry chay luc login: scan read-only roi mo startup_window). Scan mode `auto` uu tien WizTree, fallback Python. Menu 46 = Startup Scan CLI. Autorun da duoc BAT (launcher trong shell:startup). Toggle o `config/user_settings.json` muc `startup`. Tool Tester 48/48, Full System Tester 37/37. Luu y: may chi co Python 3.12 (khong phai 3.11) nen launcher dung `py` khong pin version; da sua `start_download_watcher.bat` tuong tu.

**thay doi** Giai doan hien tai: Bot Autonomy v1 da co auto-scan, issue classifier, decision flow, Backup Adapter copy-only, Move-later Adapter va Safe Delete Adapter token-gated.

**thay doi** Bot Panel UI v2 da chuyen sang assistant-first: tab `Assistant` cho status/issue cards/one-click AI plan/full demo, tab `Advanced` cho bang ky thuat va step log. Huong dan nghiem thu nam o `D:\tool\docs\UI_ACCEPTANCE.md`.

**thay doi** Bot Panel UI da sua layout doc ket qua: `Ket qua gan nhat` la panel doc lon ben duoi man Assistant, co scrollbar va toi thieu 520px; `Lich su gan day` nam cung vung doc cao, canh phai result panel, 10 dong co scrollbar; vung doc duoc neo day man hinh de khong bi `De xuat cua AI` day mat, va Full System Tester da co contract cho result panel/run history.

**thay doi** Moc verify moi nhat: Tool Tester 45/45 `D:\tool\reports\tool_tester_20260614_164416.json`; Full System Tester 37/37 `D:\tool\reports\full_system_tester_20260614_164456.json`; Feed Readiness 9 pass, 0 warn, 0 fail `D:\tool\reports\feed_readiness_20260614_164517.json`.

**thay doi** Ban handoff/take-note tong hop cho lan tiep tuc sau nam tai `D:\tool\docs\AI_ASSISTANT_HANDOFF_2026_06_15.md`.

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

Passed: 32
Failed: 0

---

### Scenario Tester

**thay đổi** Đã thêm sandbox scenario tester dùng file giả, không xóa hoặc chỉnh file thật của user.

Chức năng:

* **thay đổi** Tạo sandbox riêng tại `D:\_ai_desktop_assistant_scenario_tests\run_<timestamp>`.
* **thay đổi** Mô phỏng Downloads root, file đang tải dở, archive/bộ cài, game data `Riot Games`, media, temp/junk và empty folders.
* **thay đổi** Test Download Organizer và Media Organizer bằng move + manifest restore trên file giả.
* **thay đổi** Test risk guardrail: game data và archive chỉ `review_required`, file project bị `safe_delete` block.
* **thay đổi** Cleanup sandbox chỉ được phép trong prefix test đã kiểm soát.
* **thay đổi** Main CLI expose `Scenario Tester` ở mục 32.

Kết quả hiện tại:

Passed: 6
Failed: 0

---

### Step 2 Real Workflow Dry Run

**thay đổi** Đã chạy thử workflow tổng trên dữ liệu thật theo chế độ read-only/dry-run.

Kết quả:

* **thay đổi** System Advisor đọc snapshot thật trên `D:\`, không xóa/move file.
* **thay đổi** Advisor report: `D:\tool\reports\system_advisor_20260602_200124.json`.
* **thay đổi** Recommendation Center export: `D:\tool\reports\recommendation_center_20260602_200406.json`.
* **thay đổi** Queue sau review: 0 pending, 2 deferred, 2 handled, 1 ignored.
* **thay đổi** `downloads-folder-heavy` -> handled vì `D:\Downloads` root có 0 file lẻ, Download Organizer không có gì để move.
* **thay đổi** `large-archive-files` -> deferred vì có Premiere/archive/backup assets, cần user quyết định thủ công.
* **thay đổi** `heavy-processes` -> ignored vì `fczf.exe` có vẻ là app/game đang chạy và `MemCompression` là hành vi hệ thống Windows.
* **thay đổi** `large-video-files` -> deferred vì video là media/backup export, cần user chọn nơi lưu hoặc quyết định giữ.
* **thay đổi** `largest-folder-review` -> handled vì trùng ngữ cảnh với Downloads heavy đã kiểm tra.
* **thay đổi** Guided Action Runner dry-run 2 item deferred, không execute target tool.
* **thay đổi** Feed Readiness tại thời điểm Step 2: ready, 8 pass, 0 warn, 0 fail.

---

### Step 3 Deferred Storage Review

**thay đổi** Đã review sâu 2 deferred còn lại bằng report read-only.

Kết quả:

* **thay đổi** Report: `D:\tool\reports\step3_deferred_storage_review_20260602_201152.json`.
* **thay đổi** Archive/bộ cài lớn: 4 file, tổng khoảng 5.48 GB.
* **thay đổi** 2 file thuộc `D:\Downloads\app`/Premiere installer bundle và 2 file thuộc backup/asset; tất cả là `manual_review_only`.
* **thay đổi** Video lớn: 22 file, tổng khoảng 21.34 GB.
* **thay đổi** Video gồm 1 Steam Workshop media nên không nên move/delete bằng assistant, và 21 backup/export videos cần user chọn chính sách giữ/chuyển.
* **thay đổi** Không có auto-delete candidate trong Step 3.
* **thay đổi** Queue giữ nguyên trạng thái sạch: 0 pending, 2 deferred, 2 handled, 1 ignored.
* **thay đổi** Feed Readiness sau Step 3: ready, 8 pass, 0 warn, 0 fail.

---

### Step 4 Action Policy / User Decision Layer

**thay đổi** Đã thêm Action Policy Manager để lưu quyết định xử lý theo path/context/recommendation trước khi automation đụng file thật.

Kết quả:

* **thay đổi** File state local: `D:\tool\data\action_policy.jsonl`, đã ignore khỏi git.
* **thay đổi** Baseline policy hiện có 11 rule: 5 `ignore_forever`, 3 `manual_only`, 2 `needs_backup`, 1 `move_later`, 0 `delete_candidate`.
* **thay đổi** `Riot Games`, `League of Legends` và Steam Workshop được giữ ở `ignore_forever`.
* **thay đổi** `D:\Downloads\app` được giữ ở `manual_only`; archive/bộ cài lớn chưa được auto-delete.
* **thay đổi** `D:\backup` được giữ ở `needs_backup`; video/export/backup cần user chọn chính sách trước.
* **thay đổi** Step 3 coverage: 26/26 item deferred đã có policy phủ, uncovered 0.
* **thay đổi** Action Policy report: `D:\tool\reports\action_policy_20260602_202932.json`.
* **thay đổi** Feed Readiness mới nhất: ready, 9 pass, 0 warn, 0 fail.
* **thay đổi** Tại thời điểm Action Policy baseline: Tool Tester pass 33/33; Full System Tester pass 23/23.

---

### Step 4 Follow-up Batch: Gate, Review, Planner, Bundle

**thay đổi** Đã hoàn thành cả 4 bước tiếp theo sau Action Policy.

Kết quả:

* **thay đổi** Policy Enforcement Gate đã được móc vào Guided Action Runner.
* **thay đổi** `ignore_forever` và `keep` bị chặn trước khi mở cleanup/action tool.
* **thay đổi** `manual_only`, `needs_backup`, `move_later`, `delete_candidate` yêu cầu token mạnh tương ứng: `OPEN_MANUAL`, `OPEN_BACKUP`, `OPEN_MOVE_LATER`, `OPEN_DELETE_CANDIDATE`.
* **thay đổi** Candidate Review report: `D:\tool\reports\candidate_review_20260603_200623.json`.
* **thay đổi** Candidate Review thấy 26 item, 26/26 được policy phủ, auto execute 0.
* **thay đổi** Dry-run Action Planner report: `D:\tool\reports\action_planner_20260603_200623.json`.
* **thay đổi** Action Planner có 26 item, can execute now 0, delete candidate 0.
* **thay đổi** Pre-feed Bundle: `D:\tool\data\feed_bundles\pre_feed_bundle_20260603_200750.json`.
* **thay đổi** Pre-feed Bundle report: `D:\tool\reports\pre_feed_bundle_20260603_200750.json`.
* **thay đổi** Feed Readiness cuối mốc: `D:\tool\reports\feed_readiness_20260603_200751.json`, ready, 9 pass, 0 warn, 0 fail.
* **thay đổi** Tool Tester pass 36/36; Full System Tester pass 26/26.
* **thay đổi** Vẫn chưa có auto cleanup; đây là mốc gate/report/plan/bundle.

---

### AI Bot Controller v1

**thay đổi** Đã thêm lớp bot tổng đầu tiên để user không phải nhớ 37 chức năng riêng lẻ.

Chức năng:

* **thay đổi** Thêm `tools/core/bot_controller.py`.
* **thay đổi** Main CLI expose `AI Bot Controller` ở mục 37.
* **thay đổi** Natural Command route các lệnh `ai bot`, `auto check`, `kiem tra may`, `tu dong check`, `bot tong`.
* **thay đổi** Bot Controller gom Recommendation Queue, Guided Action context, Action Policy, Candidate Review, Dry-run Action Planner, Feed Readiness và latest reports.
* **thay đổi** Màn quyết định chuẩn: `ok`, `select`, `cancel`, `details`.
* **thay đổi** `ok` chỉ chạy khi có item `can_execute_now`; hiện tại chưa có item an toàn để chạy ngay nên `ok` không execute.
* **thay đổi** `select` trả danh sách cần user chọn thủ công; `cancel` không làm gì; `details` chỉ xem report.
* **thay đổi** Safety contract: `executes_file_operations=false`, `bot_autonomy=scan_and_plan_only_v1`, không đụng `ignore_forever`/`keep`.

Kết quả mới nhất:

* **thay đổi** Bot report: `D:\tool\reports\bot_controller_20260603_210546.json`.
* **thay đổi** Bot summary: 2 visible recommendation, 5 total recommendation, 0 safe-to-execute, 25 needs selection, 1 do-not-touch.
* **thay đổi** Tool Tester pass 37/37 tại mốc Bot Controller v1/v2.
* **thay đổi** Full System Tester pass 27/27 tại mốc Bot Controller v1/v2.
* **thay đổi** Feed Readiness ready, 9 pass, 0 warn, 0 fail.

Ý nghĩa:

* **thay đổi** Đây là mốc đầu của app/bot tự động check máy: bot đã biết scan, gom vấn đề, phân loại, đưa lựa chọn.
* **thay đổi** Chưa bật phần tự xóa/move; bước sau cần selection UI và execution adapter có undo/manifest rõ ràng.

---

### Selection UI / Decision Report v2

**thay đổi** Đã thêm lớp chọn item và ghi quyết định vào report để chuẩn bị cho app/bot tự động kiểu `ok / lựa chọn / hủy`.

Chức năng:

* **thay đổi** `bot_controller` hiện dùng schema `bot_controller_v2`.
* **thay đổi** Selection UI dùng schema `bot_selection_ui_v2`.
* **thay đổi** Selection Decision Report dùng schema `bot_selection_decision_v2`.
* **thay đổi** Mỗi item có mã chọn như `M001`, `D001`, kèm path, size, policy, plan action, allowed decisions và recommended decision.
* **thay đổi** Nhóm `do_not_touch` bị locked; chỉ được `keep`, không thể chọn delete/move.
* **thay đổi** Quyết định như `delete_candidate` chỉ là ý định cần xác nhận ở bước sau, không phải thao tác xóa.
* **thay đổi** Menu Bot Controller có thêm preview selection UI và export selection decision report.
* **thay đổi** `select` decision trả selection UI thay vì raw list.

Kết quả mới nhất:

* **thay đổi** Bot Controller report: `D:\tool\reports\bot_controller_20260603_212757.json`.
* **thay đổi** Selection summary: 0 safe-to-execute, 25 selectable needs-selection, 1 locked/do-not-touch.
* **thay đổi** Selection decision report mẫu: `D:\tool\reports\bot_controller_20260603_212800.json`, selected 1, invalid 0, blocked 0, execution false.
* **thay đổi** Tool Tester pass 37/37 tại mốc Selection UI / Decision Report.
* **thay đổi** Full System Tester pass 27/27 tại mốc Selection UI / Decision Report.
* **thay đổi** Feed Readiness ready, 9 pass, 0 warn, 0 fail.

Ý nghĩa:

* **thay đổi** User đã có thể ghi quyết định cụ thể cho từng item mà không đụng file thật.
* **thay đổi** Đây là lớp cần có trước execution adapter; sau này adapter chỉ được đọc decision report hợp lệ, không tự suy diễn.

---

### Execution Adapter v1

**thay đổi** Đã thêm lớp nối giữa Selection Decision Report và execution flow, nhưng bản v1 vẫn không chạy thao tác file thật.

Chức năng:

* **thay đổi** Thêm `tools/core/execution_adapter.py` với schema `execution_adapter_v1`.
* **thay đổi** Đọc decision report schema `bot_selection_decision_v2` từ latest report hoặc path chỉ định.
* **thay đổi** Validate schema, invalid decision, blocked item, missing path và safety contract trước khi apply.
* **thay đổi** `dry_run` cho biết item nào chỉ record-only và item nào bị blocked.
* **thay đổi** `apply` cần token cuối `EXECUTE_SELECTION_V1`.
* **thay đổi** `keep`, `manual_review`, `skip` được ghi nhận dạng record-only.
* **thay đổi** `needs_backup`, `move_later`, `delete_candidate` bị blocked ở Execution Adapter v1; `move_later` đã có File Operation Adapter riêng ở bước sau.
* **thay đổi** `file_operations_executed=false`, `delete_enabled=false`, `move_enabled=false` trong mọi chế độ của v1.

Kết quả mới nhất:

* **thay đổi** Main CLI expose `Execution Adapter` ở mục 38.
* **thay đổi** Dry-run report: `D:\tool\reports\execution_adapter_20260604_200951_1.json`.
* **thay đổi** Apply record-only report: `D:\tool\reports\execution_adapter_20260604_200951.json`.
* **thay đổi** Tool Tester pass 38/38 tại mốc Execution Adapter.
* **thay đổi** Full System Tester pass 28/28 tại mốc Execution Adapter.
* **thay đổi** Feed Readiness ready, 9 pass, 0 warn, 0 fail.

Ý nghĩa:

* **thay đổi** Bot đã có đường đi từ scan/plan/selection sang bước apply có khóa an toàn.
* **thay đổi** Execution Adapter vẫn không tự xóa/move; file operation thật phải đi qua adapter riêng.

---

### Bot Move-later Flow v1

**thay đổi** Đã nối Bot Controller với File Operation Adapter để user không phải tự nhảy qua menu 39 khi xử lý `move_later`.

Chức năng:

* **thay đổi** Bot Controller menu có thêm `Move selected move_later with destination`.
* **thay đổi** Bot summary hiển thị `move_later_selectable_count`.
* **thay đổi** Flow in Selection UI, nhận decision dạng `M001=move_later`, hỏi destination folder, tạo Selection Decision Report.
* **thay đổi** Bot gọi File Operation Adapter dry-run trước, chỉ apply khi user nhập token `MOVE_SELECTION_V1`.
* **thay đổi** Bot flow report dùng schema `bot_move_later_flow_v1`, ghi decision report, operation report, manifest và trạng thái file operation.
* **thay đổi** `OK` vẫn không tự move; nhánh move thật là nhánh riêng.
* **thay đổi** `delete_candidate` vẫn chưa bật.

Ý nghĩa:

* **thay đổi** User có thể đi theo luồng gần với app/bot hơn: bot scan -> user chọn item -> chọn folder đích -> dry-run -> token apply.
* **thay đổi** Đây vẫn là CLI flow, chưa phải Desktop UI có folder picker đồ họa.

Kết quả tại mốc Bot Move-later Flow v1:

* **thay đổi** Bot Move-later Flow Contract tạo report dry-run, thiếu token và apply có manifest restore bằng file giả trong sandbox.
* **thay đổi** Contract report được tag `contract_test`/`full_system`; Recommendation Center cũng lọc marker test từ `note`, `context` và linked `source_report`.
* **thay đổi** Tool Tester pass 39/39 tại `D:\tool\reports\tool_tester_20260605_204040.json`.
* **thay đổi** Full System Tester pass 30/30 tại `D:\tool\reports\full_system_tester_20260605_204115.json`.
* **thay đổi** Feed Readiness ready, 9 pass, 0 warn, 0 fail tại `D:\tool\reports\feed_readiness_20260605_204138.json`.

---

### Obsidian Exporter v1

**thay đổi** Đã thêm lớp xuất bản đồ review-only cho Obsidian để nhìn tổng thể tool, report, queue, policy và safety contract.

Chức năng:

* **thay đổi** Thêm `tools/core/obsidian_exporter.py` với schema `obsidian_export_v1`.
* **thay đổi** Main CLI expose `Obsidian Exporter` ở mục 40.
* **thay đổi** Natural Command route được `obsidian`, `export obsidian`, `database file`, `sơ đồ database file`.
* **thay đổi** Export vault mặc định tại `D:\tool\obsidian_vault`.
* **thay đổi** Vault tạo 9 trang nền: `00_Index.md`, system overview, Mermaid flow, Obsidian Canvas, capability map, recommendation queue, action policies, latest reports và safety contract.
* **thay đổi** Graph Mode tạo nhiều note nhỏ dưới `60_Graph_Nodes`: tools, external apps, reports, policies, decisions và file/folder paths.
* **thay đổi** `60_Graph_Nodes/Graph Hub.md` là note trung tâm để mở Local Graph/Graph view.
* **thay đổi** `10_System_Map/Graph View Guide.md` hướng dẫn group node theo thư mục graph.
* **thay đổi** Vault output được ignore khỏi git bằng `obsidian_vault/`.
* **thay đổi** Tool này chỉ ghi file trong vault; không scan sâu từng file, không xóa, không move, không approve action.

Kết quả mới nhất:

* **thay đổi** Export thật đã tạo 283 note tại `D:\tool\obsidian_vault`, trong đó có 273 graph node; exporter đã prune 159 graph node generated cũ.
* **thay đổi** Obsidian Exporter report: `D:\tool\reports\obsidian_exporter_20260606_124034.json`.
* **thay đổi** Tool Tester pass 43/43 tại `D:\tool\reports\tool_tester_20260606_133546.json`.
* **thay đổi** Full System Tester pass 34/34 tại `D:\tool\reports\full_system_tester_20260606_133601.json`.
* **thay đổi** Feed Readiness ready, 9 pass, 0 warn, 0 fail tại `D:\tool\reports\feed_readiness_20260606_124031.json`.

Ý nghĩa:

* **thay đổi** Obsidian trở thành bản đồ tư duy của assistant, giúp xem lại vì sao tool đề xuất giữ, move, backup hay review thủ công.
* **thay đổi** Đây chưa phải Desktop UI thao tác file; mọi thao tác thật vẫn phải đi qua Bot Controller/File Operation Adapter/Safe Executor.

---

### File Operation Adapter v1

**thay đổi** Đã thêm lớp file-operation đầu tiên cho decision `move_later`.

Chức năng:

* **thay đổi** Thêm `tools/core/file_operation_adapter.py` với schema `file_operation_adapter_v1`.
* **thay đổi** Chỉ đọc Selection Decision Report hợp lệ schema `bot_selection_decision_v2`.
* **thay đổi** Chỉ xử lý item có decision `move_later`; các decision khác là `not_in_scope`.
* **thay đổi** Destination folder phải tồn tại sẵn, là directory, không phải root ổ và không thuộc vùng `PROTECTED`.
* **thay đổi** Source phải là file tồn tại và không thuộc vùng `PROTECTED`.
* **thay đổi** `apply` cần token riêng `MOVE_SELECTION_V1`.
* **thay đổi** Move dùng `safe_move()` và lưu manifest `file_operation_adapter_move_*.json`.
* **thay đổi** Undo Manager restore được manifest sau move.
* **thay đổi** Delete không nằm trong adapter này; `delete_candidate` đã được tách sang Safe Delete Adapter riêng.

Kết quả mới nhất:

* **thay đổi** Main CLI expose `File Operation Adapter` ở mục 39.
* **thay đổi** Dry-run sandbox report: `D:\tool\reports\file_operation_adapter_20260604_205528.json`.
* **thay đổi** Apply sandbox report: `D:\tool\reports\file_operation_adapter_20260604_205528_1.json`.
* **thay đổi** Manifest sandbox đã restore: `D:\tool\backups\file_operation_adapter_move_20260604_205528.json`.
* **thay đổi** Tool Tester pass 43/43.
* **thay đổi** Full System Tester pass 34/34 tại mốc Bot Autonomy v1.
* **thay đổi** Feed Readiness ready, 9 pass, 0 warn, 0 fail.

Ý nghĩa:

* **thay đổi** Bot flow đã có bước move thật đầu tiên, nhưng chỉ cho file được user chọn rõ qua decision report và folder đích cụ thể.
* **thay đổi** `delete_candidate` chỉ trở thành action khi đi qua Safe Delete Adapter, risk `safe_delete`, dry-run và token `DELETE_SELECTION_V1`.

---

### Bot Autonomy v1: Auto Scan / Issue Classifier / Safe Delete

**thay đổi** Đã thêm mốc backend cho assistant tự scan, tự phân loại vấn đề và chuẩn bị action có kiểm soát.

Chức năng:

* **thay đổi** `tools/core/auto_scan_session.py` tạo snapshot read-only cho disk/storage/process/external apps/audit, schema `auto_scan_session_v1`.
* **thay đổi** `tools/core/issue_classifier.py` biến snapshot thành issue/action group cho Bot Controller, schema `issue_classifier_v1`.
* **thay đổi** Bot Controller v2 nay merge action plan cũ với issue classifier và có decision `delete_candidate`.
* **thay đổi** `tools/core/safe_delete_adapter.py` xử lý selection `delete_candidate`, schema `safe_delete_adapter_v1`.
* **thay đổi** Safe Delete Adapter chỉ cho file có risk `safe_delete`; `review_required` và `protected` bị chặn dù user chọn xóa.
* **thay đổi** Apply delete cần token `DELETE_SELECTION_V1` và chỉ gửi file vào Recycle Bin, không permanent delete.
* **thay đổi** Main CLI expose `Auto Scan Session` mục 41, `Issue Classifier` mục 42, `Safe Delete Adapter` mục 43.
* **thay đổi** Natural Command route thêm các lệnh kiểu `auto scan`, `phân loại vấn đề`, `xóa an toàn`.

Kết quả mới nhất:

* **thay đổi** Capability Registry valid 43/43; summary 28 safe, 9 medium, 6 dangerous; 14 tool có thể thay đổi file; 15 tool cần confirmation; 10 tool dùng external app.
* **thay đổi** Tool Tester pass 43/43 tại `D:\tool\reports\tool_tester_20260606_133546.json`.
* **thay đổi** Full System Tester pass 34/34 tại `D:\tool\reports\full_system_tester_20260606_133601.json`.
* **thay đổi** Full System Tester có contract cho Auto Scan + Issue Classifier, Safe Delete Adapter và Bot Safe-delete Flow bằng file giả trong sandbox.

Ý nghĩa:

* **thay đổi** Bot đã tiến gần hơn tới app tự động check máy: scan và phân loại được tự động, còn thao tác thật vẫn cần user chọn và token.
* **thay doi** Backend nay hien da duoc Bot Panel UI v2 dung lai; UI/folder picker khong viet logic xoa/move moi ma goi report/flow san co.

---

### Bot Panel UI v2

**thay doi** Da chuyen desktop UI tu man nghiem thu ky thuat sang man assistant-first de user khong can nho 45 menu CLI.

Chuc nang:

* **thay doi** `tools/ui/bot_panel.py` tao UI Tkinter voi entrypoint `python -m tools.ui.bot_panel`.
* **thay doi** Main CLI expose `Bot Panel UI` o muc 44.
* **thay doi** UI co folder picker, storage mode `light/python/wiztree`, threshold/limit va nut `Auto scan + classify`.
* **thay doi** UI co tab `Assistant` lam man hinh chinh: target folder, trang thai scan, issue cards, count theo backup/move/safe cleanup/review/protected.
* **thay doi** UI co flow 3 buoc tren man chinh: `Dung de xuat AI` -> `Xem ke hoach AI` -> `Ap dung ke hoach`.
* **thay doi** `Xem ke hoach AI` gom backup/move/safe cleanup vao mot preview tong, khong thay doi file.
* **thay doi** `Ap dung ke hoach` yeu cau tick `Toi da xem ke hoach`, popup confirm va preview signature con khop.
* **thay doi** UI co khung `Ket qua gan nhat` tren tab `Assistant`, nen scan/preview/apply co summary de doc ma khong can vao `Advanced`.
* **thay doi** UI co nut `Chay full demo` de tu chay tron luong bang file gia va in step log trong tab `Advanced`.
* **thay doi** Bang selection item, recommended decision, allowed decision, risk/group/action va detail panel da duoc dua vao tab `Advanced` de man chinh bot bot ky thuat hon.
* **thay doi** Man chinh hien issue cards thay cho bang `Recommended work`: moi card co so luong, y nghia, nut xem nhom va nut chon theo de xuat.
* **thay doi** UI co `Demo sandbox` tao file gia trong `D:\_ai_desktop_assistant_ui_demo\run_<timestamp>\...` de test truoc khi dung file that va tranh protected root `D:\tool`.
* **thay doi** UI tao Selection Decision Report, chay Backup/Move/Safe Delete dry-run, va apply chi khi user tick checkbox + popup confirm; backend adapter van nhan token noi bo.
* **thay doi** UI backup chi copy file `needs_backup` sang `D:\tool\backups\selection_backups\...`, source duoc giu nguyen.
* **thay doi** UI khong bypass adapter; delete that van di qua Safe Delete Adapter va Recycle Bin.

Ket qua moi nhat:

* **thay doi** Capability Registry valid 45/45 sau khi them Backup Adapter v1.
* **thay doi** Tool Tester pass 45/45 tai `D:\tool\reports\tool_tester_20260611_204617.json`.
* **thay doi** Full System Tester pass 37/37 tai `D:\tool\reports\full_system_tester_20260611_204703.json`.
* **thay doi** Feed Readiness ready, 9 pass, 0 warn, 0 fail tai `D:\tool\reports\feed_readiness_20260611_204731.json`.
* **thay doi** Huong dan nghiem thu: `D:\tool\docs\UI_ACCEPTANCE.md`.

Con lai:

* **thay doi** UI v2 da co `needs_backup` backup flow, `move_later` destination picker/apply, Undo last move, safe-delete acceptance, Assistant Dashboard, issue cards, one-click AI plan va full demo. Buoc tiep theo la run history/latest report preview, giam bot tab/label ky thuat va polished UI de dat moc nghiem thu 90%.

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

* **thay đổi** Capability count: 39
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
* **thay đổi** Kiểm tra config, Capability Registry, External Apps/drift, Recommendation Queue, Action Policy, latest Full System report, recent report schema, audit snapshot và feed source docs.
* **thay đổi** Xuất report `feed_readiness` với schema `feed_readiness_v1`.
* **thay đổi** Chỉ read-only: không feed/train thật, không cleanup, không sửa config/path.
* **thay đổi** Natural Command có thể route các lệnh như `feed assistant`, `feed readiness`, `san sang feed`.

Kết quả mới nhất:

* **thay đổi** Readiness status: ready.
* **thay đổi** Checks: 9 pass, 0 warn, 0 fail.
* **thay đổi** Không còn warning trong readiness snapshot mới nhất.
* **thay đổi** Tool Tester pass 43/43.
* **thay đổi** Behavior Tester pass 18/18.
* **thay đổi** Scenario Tester pass 6/6.
* **thay đổi** Full System Tester pass 34/34 tại mốc Bot Autonomy v1.

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

### Pending Storage Review

**thay đổi** Đã xử lý bước tiếp theo bằng scan/report read-only cho 2 recommendation còn lại.

Kết quả:

* **thay đổi** `D:\Downloads` root có 0 file lẻ để Download Organizer sắp xếp.
* **thay đổi** `D:\Downloads\Riot Games` khoảng 36.24 GB, không tự động xử lý vì là game data.
* **thay đổi** `D:\Downloads\app` khoảng 7.72 GB, có nhiều bộ cài/archive cần user chọn giữ/xóa/move.
* **thay đổi** Large archive review thấy 6 file, tổng khoảng 8.99 GB.
* **thay đổi** `downloads-folder-heavy` chuyển `handled` cho flow Download Organizer vì không có root file để organize.
* **thay đổi** `large-archive-files` chuyển `deferred` vì cần user quyết định file nào được xóa hoặc chuyển chỗ.
* **thay đổi** Queue mới nhất: 0 pending, 2 deferred, 2 handled, 1 ignored.
* **thay đổi** Feed Readiness tại thời điểm pending storage review: ready, 8 pass, 0 warn, 0 fail.

Reports:

* **thay đổi** Storage review: `D:\tool\reports\recommendation_center_20260601_201426.json`.
* **thay đổi** Queue export: `D:\tool\reports\recommendation_center_20260601_201448.json`.
* **thay đổi** Feed Readiness: `D:\tool\reports\feed_readiness_20260601_201449.json`.

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
* **thay đổi** Scenario Tester
* **thay đổi** Action Policy Manager
* **thay đổi** Candidate Review
* **thay đổi** Dry-run Action Planner
* **thay đổi** Pre-feed Bundle
* **thay đổi** AI Bot Controller
* **thay đổi** Selection UI / Decision Report

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
* **thay đổi** Kiểm tra Scenario Tester contract bằng sandbox fake-file và cleanup guard
* **thay đổi** Kiểm tra default queue loại test-tagged reports
* **thay đổi** Kiểm tra Action Policy Contract và Feed Readiness check `action_policy`
* **thay đổi** Kiểm tra Candidate Review, Dry-run Action Planner và Pre-feed Bundle contract
* **thay đổi** Kiểm tra AI Bot Controller contract: decision screen, selection UI v2, selection decision v2, locked item bị block và OK không execute file trong v2

Kết quả hiện tại:

Passed: 27
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
* **thay đổi** Scenario Tester fake-file sandbox
* **thay đổi** Action Policy Manager
* **thay đổi** Policy Enforcement Gate
* **thay đổi** Candidate Review
* **thay đổi** Dry-run Action Planner
* **thay đổi** Pre-feed Bundle
* **thay đổi** AI Bot Controller v2
* **thay đổi** Selection UI / Decision Report v2
* **thay đổi** Execution Adapter v1 record-only
* **thay đổi** File Operation Adapter v1 cho `move_later`
* **thay đổi** Bot Move-later Flow v1
* **thay đổi** Auto Scan Session v1
* **thay đổi** Issue Classifier v1
* **thay đổi** Safe Delete Adapter v1
* **thay đổi** Bot Safe-delete Flow v1
* **thay doi** Backup Adapter v1 va Bot Backup Flow v1

Cần làm tiếp để ổn định tool tổng:

* **thay doi** Uu tien 1: Nang Bot Panel UI thanh dashboard day du hon de user nhin issue, chon `ok / lua chon / huy` ma khong phai nho 45 menu.
* **thay doi** Uu tien 2: Them issue grouping/filter tot hon cho `keep`, `needs_backup`, `move_later`, `delete_candidate`, `review_required`, tranh phai doc raw report.
* **thay doi** Uu tien 3: Them run history + latest report preview gon hon trong UI.
* **thay đổi** Mở rộng Natural Command v3 thành intent engine sau khi có thêm lịch sử/report để feed assistant
* **thay đổi** Chuẩn hóa feed assistant sau khi Execution/Report flow ổn, để assistant nhớ flow bằng context sạch thay vì train sớm
* **thay đổi** Bổ sung thêm case vào Scenario Tester và Full System Tester khi phát hiện lỗi thực tế mới

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
