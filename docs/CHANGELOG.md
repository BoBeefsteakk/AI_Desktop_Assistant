# Changelog

## 2026-06-05

### Bot Move-later Flow verification

* **thay đổi** Bot Move-later Flow v1 đã được verify lại sau khi nối Bot Controller với File Operation Adapter.
* **thay đổi** Contract report sinh từ Full System Tester giờ được tag `contract_test` và `full_system` để Recommendation Center không đưa warning guardrail vào queue thật.
* **thay đổi** Recommendation Center nhận diện thêm marker test trong `note`, `context` và linked `source_report`, nên các report contract cũ của Bot/File Operation Adapter cũng không còn làm Feed Readiness bị warn giả.
* **thay đổi** Tool Tester pass 39/39 tại `D:\tool\reports\tool_tester_20260605_204040.json`.
* **thay đổi** Full System Tester pass 30/30 tại `D:\tool\reports\full_system_tester_20260605_204115.json`.
* **thay đổi** Feed Readiness ready, 9 pass, 0 warn, 0 fail tại `D:\tool\reports\feed_readiness_20260605_204138.json`.

## 2026-06-04

### Bot Move-later Flow v1

* **thay đổi** Nối Bot Controller với File Operation Adapter qua flow `move_later_selection_flow`.
* **thay đổi** Menu Bot Controller có thêm lựa chọn `Move selected move_later with destination`.
* **thay đổi** Flow mới in Selection UI, nhận decision như `M001=move_later`, hỏi destination folder, export decision report, chạy File Operation Adapter dry-run, rồi mới apply nếu có token `MOVE_SELECTION_V1`.
* **thay đổi** Bot flow tạo report tổng schema `bot_move_later_flow_v1` để trace decision report, operation report, manifest và trạng thái restore.
* **thay đổi** `OK` vẫn không tự move; move thật chỉ đi qua nhánh move_later riêng.
* **thay đổi** `delete_candidate` vẫn chưa bật.

### File Operation Adapter v1

* **thay đổi** Thêm `tools/core/file_operation_adapter.py` làm lớp file-operation đầu tiên sau Execution Adapter.
* **thay đổi** Bản v1 chỉ xử lý decision `move_later`; các decision khác trong cùng report bị đánh dấu `not_in_scope`, không thành action.
* **thay đổi** Move thật chỉ chạy khi có destination folder đã tồn tại, không phải root ổ, source là file, source/destination không thuộc vùng `PROTECTED`, và user nhập token `MOVE_SELECTION_V1`.
* **thay đổi** Adapter dùng `safe_move()` và tạo manifest `file_operation_adapter_move_*.json` để Undo Manager restore được.
* **thay đổi** Delete vẫn bị tắt hoàn toàn; `delete_candidate` chưa được adapter này xử lý.
* **thay đổi** Main CLI expose `File Operation Adapter` ở mục 39; Capability Registry, Natural Command v3, Tool Tester, Feed Readiness và Full System Tester đã có entry/contract.
* **thay đổi** Dry-run sandbox report: `D:\tool\reports\file_operation_adapter_20260604_205528.json`.
* **thay đổi** Apply sandbox report: `D:\tool\reports\file_operation_adapter_20260604_205528_1.json`.
* **thay đổi** Sandbox manifest đã được restore thành công: `D:\tool\backups\file_operation_adapter_move_20260604_205528.json`.
* **thay đổi** Tool Tester pass 39/39 tại `D:\tool\reports\tool_tester_20260604_210733.json`.
* **thay đổi** Full System Tester pass 29/29 tại mốc File Operation Adapter: `D:\tool\reports\full_system_tester_20260604_210757.json`.
* **thay đổi** Feed Readiness pass 9/9 tại `D:\tool\reports\feed_readiness_20260604_210818.json`.

### Execution Adapter v1

* **thay đổi** Thêm `tools/core/execution_adapter.py` làm lớp thực thi có kiểm soát sau Selection Decision Report.
* **thay đổi** Execution Adapter dùng schema `execution_adapter_v1` và chỉ nhận decision report schema `bot_selection_decision_v2`.
* **thay đổi** Bản v1 chỉ ghi nhận các quyết định record-only như `keep`, `manual_review`, `skip`; không xóa, không move, không backup file thật.
* **thay đổi** Các decision `needs_backup`, `move_later`, `delete_candidate` bị giữ ở trạng thái blocked vì chưa có destination/manifest/undo và chưa bật file operation adapter.
* **thay đổi** Chế độ apply cần token cuối `EXECUTE_SELECTION_V1`; dù có token, file operation vẫn `false` ở bản v1.
* **thay đổi** Main CLI expose `Execution Adapter` ở mục 38; Capability Registry, Natural Command v3, Tool Tester, Feed Readiness và Full System Tester đã có entry/contract.
* **thay đổi** Dry-run Execution Adapter report: `D:\tool\reports\execution_adapter_20260604_200951_1.json`.
* **thay đổi** Apply record-only report: `D:\tool\reports\execution_adapter_20260604_200951.json`.
* **thay đổi** Tool Tester pass 38/38 tại `D:\tool\reports\tool_tester_20260604_202149.json`.
* **thay đổi** Full System Tester pass 28/28 tại `D:\tool\reports\full_system_tester_20260604_202227.json`.
* **thay đổi** Feed Readiness pass 9/9 tại `D:\tool\reports\feed_readiness_20260604_202417.json`.

## 2026-06-03

### Selection UI / Decision Report v2

* **thay đổi** Nâng `tools/core/bot_controller.py` lên schema `bot_controller_v2`.
* **thay đổi** Thêm Selection UI schema `bot_selection_ui_v2` để gán mã chọn ổn định cho từng item: nhóm safe, cần chọn thủ công, do-not-touch và review-only.
* **thay đổi** Thêm Selection Decision schema `bot_selection_decision_v2` để ghi lại quyết định user theo mã như `M001=keep`, `M002=move_later`, `M003=delete_candidate`.
* **thay đổi** Decision report chỉ ghi ý định/selection; `execution_enabled=false`, `executes_file_operations=false`, không xóa/move file thật.
* **thay đổi** Item thuộc nhóm `do_not_touch` bị locked; nếu ép chọn `delete_candidate`/move sẽ bị ghi vào `blocked`, không thành action.
* **thay đổi** Menu Bot Controller có thêm preview Selection UI v2 và export Selection Decision Report.
* **thay đổi** `select` trong Bot Controller giờ trả selection UI thay vì chỉ trả raw item list.
* **thay đổi** Bot Controller report mới nhất: `D:\tool\reports\bot_controller_20260603_212757.json`.
* **thay đổi** Selection decision report mẫu: `D:\tool\reports\bot_controller_20260603_212800.json`, chọn 1 item `keep`, execution vẫn false.
* **thay đổi** Tool Tester pass 37/37 tại `D:\tool\reports\tool_tester_20260603_212659.json`.
* **thay đổi** Full System Tester pass 27/27 tại `D:\tool\reports\full_system_tester_20260603_212733.json`.
* **thay đổi** Feed Readiness pass 9/9 tại `D:\tool\reports\feed_readiness_20260603_212756.json`.
* **thay đổi** Bước này vẫn chưa bật execution adapter; đây là lớp chọn và ghi quyết định trước khi có thao tác thật.

### AI Bot Controller v1

* **thay đổi** Thêm `tools/core/bot_controller.py` làm entrypoint bot tổng cho flow auto-check máy.
* **thay đổi** Bot Controller gom Recommendation Queue, Guided Action context, Action Policy, Candidate Review, Dry-run Action Planner, Feed Readiness và latest reports thành một snapshot tổng.
* **thay đổi** Màn quyết định hiện có 4 nhánh: `ok`, `select`, `cancel`, `details`.
* **thay đổi** `ok` chỉ dành cho safe-only action đã có `can_execute_now`; snapshot hiện tại có `safe_to_execute_count=0` nên `ok` trả về `no_safe_actions` và không chạy cleanup.
* **thay đổi** `select` trả danh sách item cần user chọn thủ công; `cancel` không làm gì; `details` chỉ trả summary/report.
* **thay đổi** Safety contract của v1: `executes_file_operations=false`, `bot_autonomy=scan_and_plan_only_v1`, không đụng `ignore_forever`/`keep`.
* **thay đổi** Main CLI expose `AI Bot Controller` ở mục 37; Natural Command route các lệnh như `ai bot`, `auto check`, `kiem tra may`, `bot tong`.
* **thay đổi** Capability Registry có entry `bot_controller`; Feed Readiness đọc latest `bot_controller` report.
* **thay đổi** Report Bot Controller mới nhất: `D:\tool\reports\bot_controller_20260603_210546.json`.
* **thay đổi** Summary Bot Controller mới nhất: 2 visible recommendation, 5 total recommendation, 0 safe-to-execute, 25 needs selection, 1 do-not-touch, readiness ready.
* **thay đổi** Tool Tester pass 37/37 tại `D:\tool\reports\tool_tester_20260603_210452.json`.
* **thay đổi** Full System Tester pass 27/27 tại `D:\tool\reports\full_system_tester_20260603_210524.json`.
* **thay đổi** Feed Readiness pass 9/9 tại `D:\tool\reports\feed_readiness_20260603_210545.json`.
* **thay đổi** Mốc này vẫn chưa bật auto-delete/auto-move; đây là bot controller scan/plan/decision v1.

### Step 4 Follow-up Batch: Gate, Review, Planner, Bundle

* **thay đổi** Triển khai đủ 4 bước tiếp theo sau Action Policy: Policy Enforcement Gate, Candidate Review Report, Dry-run Action Planner và Pre-feed Bundle.
* **thay đổi** Guided Action Runner giờ đọc `policy_gate`: `ignore_forever`/`keep` bị chặn, còn `manual_only`, `needs_backup`, `move_later`, `delete_candidate` cần token mạnh như `OPEN_MANUAL`, `OPEN_BACKUP`, `OPEN_MOVE_LATER`, `OPEN_DELETE_CANDIDATE`.
* **thay đổi** Thêm `tools/core/candidate_review.py`; report mới `D:\tool\reports\candidate_review_20260603_200623.json` có 26 candidate, 26/26 được policy phủ, auto execute 0.
* **thay đổi** Thêm `tools/core/action_planner.py`; report mới `D:\tool\reports\action_planner_20260603_200623.json` có 26 item, can execute now 0, delete candidate 0.
* **thay đổi** Thêm `tools/core/pre_feed_bundle.py`; bundle mới `D:\tool\data\feed_bundles\pre_feed_bundle_20260603_200750.json`, report `D:\tool\reports\pre_feed_bundle_20260603_200750.json`.
* **thay đổi** Main CLI expose thêm `Candidate Review` mục 34, `Dry-run Action Planner` mục 35, `Pre-feed Bundle` mục 36.
* **thay đổi** Tool Tester pass 36/36; Full System Tester pass 26/26 tại `D:\tool\reports\full_system_tester_20260603_200729.json`.
* **thay đổi** Feed Readiness cuối mốc: `D:\tool\reports\feed_readiness_20260603_200751.json`, ready, 9 pass, 0 warn, 0 fail.
* **thay đổi** Vẫn chưa bật auto cleanup; toàn bộ mốc này chỉ gate/report/plan/bundle, không xóa/move file thật.

## 2026-06-02

### Step 4 Action Policy / User Decision Layer

* **thay đổi** Thêm `tools/core/action_policy.py` làm lớp quyết định read-only trước khi automation xử lý file thật.
* **thay đổi** Seed baseline policy an toàn: `Riot Games`/`League of Legends`/Steam Workshop -> `ignore_forever`, `D:\Downloads\app` -> `manual_only`, `D:\backup` -> `needs_backup`.
* **thay đổi** Recommendation `large-archive-files` được policy `manual_only`; `large-video-files` được policy `move_later`.
* **thay đổi** Recommendation Center hiển thị `action_policy_decision` cho từng gợi ý để user biết item đang bị giữ, hoãn, cần backup hay phải review thủ công.
* **thay đổi** Feed Readiness có check mới `action_policy`; latest report: `D:\tool\reports\feed_readiness_20260602_202933.json`, ready, 9 pass, 0 warn, 0 fail.
* **thay đổi** Action Policy report mới: `D:\tool\reports\action_policy_20260602_202932.json`, 11 policy, Step 3 coverage 26/26, uncovered 0.
* **thay đổi** Main CLI expose `Action Policy Manager` ở mục 33; Tool Tester pass 33/33.
* **thay đổi** Full System Tester thêm `Action Policy Contract` và pass 23/23 tại `D:\tool\reports\full_system_tester_20260602_202910.json`.
* **thay đổi** Không có auto-delete mới ở bước này; policy chỉ ghi quyết định và báo cáo, không xóa/move file.

### Step 3 Deferred Storage Review

* **thay đổi** Đã deep review 2 mục deferred còn lại bằng report read-only, không xóa/move file thật.
* **thay đổi** Review report: `D:\tool\reports\step3_deferred_storage_review_20260602_201152.json`.
* **thay đổi** Archive/bộ cài lớn: 4 file, tổng khoảng 5.48 GB; tất cả là `manual_review_only`, không có auto-delete candidate.
* **thay đổi** Archive gồm 2 file Premiere/Downloads app và 2 file backup/asset; cần user quyết định từng file.
* **thay đổi** Video lớn: 22 file, tổng khoảng 21.34 GB; gồm 1 Steam Workshop app-managed media và 21 backup/export videos.
* **thay đổi** `large-archive-files` và `large-video-files` tiếp tục ở `deferred` với note chi tiết trỏ về Step 3 report.
* **thay đổi** Feed Readiness sau Step 3: ready, 8 pass, 0 warn, 0 fail.

### Step 2 Real Workflow Dry Run

* **thay đổi** Đã chạy System Advisor snapshot thật trên `D:\` theo chế độ read-only, không xóa/move file.
* **thay đổi** Advisor report mới: `D:\tool\reports\system_advisor_20260602_200124.json`.
* **thay đổi** Recommendation queue sau sync có 5 item: 0 critical, 2 warning, 3 info.
* **thay đổi** Đã review queue: `downloads-folder-heavy` và `largest-folder-review` -> handled; `large-archive-files` và `large-video-files` -> deferred; `heavy-processes` -> ignored.
* **thay đổi** Lý do chính: `D:\Downloads` root có 0 file lẻ, Riot Games/app/archive/video đều cần quyết định thủ công, không tự cleanup.
* **thay đổi** Guided Action Runner dry-run 2 item deferred, cả hai đều `executed=False`: archive -> Large File Finder, video -> Media Organizer.
* **thay đổi** Feed Readiness sau Step 2: ready, 8 pass, 0 warn, 0 fail.

### Scenario Tester

* **thay đổi** Thêm `tools/core/scenario_tester.py` để test các case nhạy cảm bằng file giả trong sandbox.
* **thay đổi** Sandbox nằm tại `D:\_ai_desktop_assistant_scenario_tests\run_<timestamp>` và cleanup chỉ được phép trong prefix này.
* **thay đổi** Test Download Organizer scan skip `.crdownload`, move fake root files và restore bằng manifest.
* **thay đổi** Test Media Organizer move fake media và restore bằng manifest.
* **thay đổi** Test guardrail cho `Riot Games`, archive/bộ cài, dev artifact, file project protected và missing path.
* **thay đổi** Test large file/folder scan, temp/junk risk classification và empty folder scan trên dữ liệu giả.
* **thay đổi** Main CLI expose `Scenario Tester` ở mục 32.
* **thay đổi** Tool Tester, Capability Registry, Natural Command và Full System Tester đã có entry/contract cho Scenario Tester.
* **thay đổi** Scenario Tester chạy riêng pass 6/6; Tool Tester pass 32/32; Full System Tester pass 22/22.
* **thay đổi** Feed Readiness sau thay đổi pass 8/8, 0 warn, 0 fail.

## 2026-06-01

### Pending Storage Review

* **thay đổi** Đã xử lý bước tiếp theo của queue bằng review read-only, không xóa/move file.
* **thay đổi** Scan `D:\Downloads` cho thấy root Downloads có 0 file lẻ để Download Organizer sắp xếp.
* **thay đổi** Dung lượng Downloads nằm chủ yếu ở thư mục con: `D:\Downloads\Riot Games` khoảng 36.24 GB và `D:\Downloads\app` khoảng 7.72 GB.
* **thay đổi** Không tự động đụng `D:\Downloads\Riot Games` vì đây là game data, chỉ nên xử lý nếu user muốn move/uninstall thủ công.
* **thay đổi** Large File Finder review thấy 6 archive/bộ cài lớn, tổng khoảng 8.99 GB.
* **thay đổi** Chuyển `downloads-folder-heavy` sang `handled` cho flow Download Organizer vì không có root file để organize.
* **thay đổi** Chuyển `large-archive-files` sang `deferred` vì xóa/move archive cần user chọn cụ thể.
* **thay đổi** Queue mới nhất: 0 pending, 2 deferred, 2 handled, 1 ignored.
* **thay đổi** Feed Readiness tại thời điểm pending storage review: ready, 8 pass, 0 warn, 0 fail.

### Recommendation Queue Review

* **thay đổi** Đã review 5 pending recommendations thật sau Feed Readiness.
* **thay đổi** Giữ `downloads-folder-heavy` ở `pending` vì cần user quyết định chạy Download Organizer trên `D:\Downloads`.
* **thay đổi** Giữ `large-archive-files` ở `pending` vì cần review file nén/bộ cài lớn bằng Large File Finder trước khi xóa hoặc move.
* **thay đổi** Chuyển `large-video-files` sang `deferred` vì gom/move video cần user chọn storage đích, không auto-move.
* **thay đổi** Chuyển `largest-folder-review` sang `handled` vì trùng ngữ cảnh với `downloads-folder-heavy`.
* **thay đổi** Chuyển `heavy-processes` sang `ignored` vì `MemCompression` là cơ chế nén RAM bình thường của Windows, không nên cleanup.
* **thay đổi** Queue mới nhất: 2 pending, 1 deferred, 1 handled, 1 ignored.
* **thay đổi** Feed Readiness mới nhất vẫn `ready`: 7 pass, 1 warn, 0 fail; warning còn lại là 2 pending recommendations cần user review.

### Feed Assistant Readiness

* **thay đổi** Thêm `tools/core/feed_readiness.py` để kiểm tra trạng thái pre-feed theo dạng read-only.
* **thay đổi** Feed Readiness kiểm tra config, Capability Registry, External Apps/drift, Recommendation Queue, latest Full System report, schema report gần đây, audit snapshot và feed source docs.
* **thay đổi** Main CLI expose `Feed Assistant Readiness` ở mục 31.
* **thay đổi** Capability Registry, Tool Tester, Natural Command và Full System Tester đã có entry/contract cho Feed Readiness.
* **thay đổi** Recommendation Center chỉ lấy structured recommendations từ nguồn được phép như `system_advisor`, `external_apps`, `audit_center`, tránh report readiness/test làm nhiễu queue thật.
* **thay đổi** Readiness report mới nhất: ready, 7 pass, 1 warn, 0 fail; warning duy nhất là còn 5 pending recommendation cần review trước automation.
* **thay đổi** Tool Tester pass 31/31, Behavior Tester pass 18/18, Full System Tester pass 21/21.

### External App Path Drift Detection

* **thay đổi** External Apps Health v2 có baseline local tại `data/external_apps_health_state.json` để so sánh lần chạy trước và lần chạy hiện tại.
* **thay đổi** Health report phát hiện `path_changed`, `availability_changed`, `version_changed`, `binary_changed` cho app ngoài.
* **thay đổi** Drift được đưa vào structured recommendations với `source=external_apps_drift`, nhưng tool vẫn chỉ read-only và không tự sửa config/path.
* **thay đổi** Export report mới nhất ghi nhận 16/16 app available, drift 0, recommendation 0.
* **thay đổi** Recommendation Center đọc buffer report lớn hơn trước khi lọc test reports để test report không che mất Advisor report thật.
* **thay đổi** Behavior Tester vẫn pass 18/18, Tool Tester pass 30/30, Full System Tester pass 20/20 sau drift detection.

### Advisor Real Run Calibration

* **thay đổi** Chạy System Advisor thật trên `D:\` bằng Python scanner read-only
* **thay đổi** Sửa lỗi console crash khi in đường dẫn Unicode/tiếng Việt bằng UTF-8 output trong System Advisor
* **thay đổi** Recommendation Center mặc định bỏ qua report test/contract để queue thật không bị nhiễu
* **thay đổi** Recommendation Center chỉ giữ snapshot mới nhất của `system_advisor`/`external_apps` để tránh duplicate recommendation từ report cũ
* **thay đổi** Queue thực tế sau calibration còn 5 recommendation: Downloads nặng, archive lớn, process RAM, video lớn, folder lớn nhất
* **thay đổi** Behavior/Full tests có assertion đảm bảo default queue không lấy test-tagged reports

### Natural Command v3

* **thay đổi** Natural Command nhận lệnh queue trực tiếp: `xem goi y`, `lam goi y so 1`, `hoan muc 2`, `danh dau muc 3 da xu ly`, `bo qua muc 4`
* **thay đổi** Lệnh mở recommendation theo index đi qua Guided Action Runner, vẫn cần xác nhận `OPEN` khi chạy thật
* **thay đổi** Lệnh state update chỉ ghi queue state, không cleanup, không xóa/move file
* **thay đổi** Thêm dry-run helper để test không execute target tool
* **thay đổi** Behavior Tester thêm Natural Command v3 Queue Actions và hiện pass 18/18
* **thay đổi** Full System Tester thêm Natural Command v3 Queue Contract và hiện pass 20/20

## 2026-05-31

### Guided Action Runner

* **thay đổi** Thêm `tools/core/guided_action_runner.py`
* **thay đổi** Sync recommendation queue pending/deferred rồi resolve `suggested_tool_id` qua Capability Registry
* **thay đổi** Hiển thị risk, mutates_files, needs_confirmation, undo_strategy, external apps và report gốc trước khi mở tool
* **thay đổi** Bắt user nhập đúng `OPEN` trước khi mở target tool
* **thay đổi** Không tự cleanup, không bypass confirmation của target tool, không tự mark recommendation handled
* **thay đổi** Dry-run path tạo report nhưng không execute target tool
* **thay đổi** Main CLI expose Guided Action Runner ở mục 30
* **thay đổi** Natural Command route lệnh `lam goi y`/`mo goi y` sang Guided Action Runner
* **thay đổi** Tool Tester mở rộng lên 30 tool
* **thay đổi** Behavior Tester thêm Guided Action Runner Contract
* **thay đổi** Full System Tester thêm Guided Action Runner Contract

### Recommendation Workflow v1

* **thay đổi** Recommendation Center co queue state persistent tai `data/recommendation_queue.jsonl`
* **thay đổi** Them state `pending`, `deferred`, `handled`, `ignored`
* **thay đổi** Them sync queue, filter theo severity/state, doi state va export queue report
* **thay đổi** Queue dung fingerprint on dinh de tranh lap lai cung mot goi y sau moi lan chay Advisor/report
* **thay đổi** Behavior Tester them case state transition
* **thay đổi** Full System Tester kiem tra state file va handled state

### Recommendation Center

* **thay đổi** Thêm `tools/core/recommendation_center.py`
* **thay đổi** Gom gợi ý từ System Advisor v2 và Audit/report warning-error thành queue read-only
* **thay đổi** Enrich suggested tool bằng Capability Registry: tên tool, risk, confirmation
* **thay đổi** Main CLI expose Recommendation Center ở mục 29
* **thay đổi** Natural Command route được lệnh recommendation/queue/gợi ý sang Recommendation Center
* **thay đổi** Tool Tester mở rộng lên 30 tool
* **thay đổi** Behavior Tester thêm case Recommendation Center Queue
* **thay đổi** Full System Tester thêm case Recommendation Center Contract
* **thay đổi** Behavior Tester hiện pass 18/18
* **thay đổi** Full System Tester hiện pass 20/20

### System Advisor v2

* **thay đổi** Nâng System Advisor thành phân tích read-only, không tự chạy cleanup
* **thay đổi** Gom snapshot từ storage, disk/SMART, process, external apps và audit reports
* **thay đổi** Recommendation có severity `critical`, `warning`, `info`
* **thay đổi** Recommendation gắn `suggested_tool_id` và metadata từ Capability Registry
* **thay đổi** Report mới dùng action `analyze_system_v2`, risk `safe`, tags `system_advisor/read_only/v2`
* **thay đổi** Behavior Tester thêm case System Advisor v2 Recommendations
* **thay đổi** Full System Tester thêm case System Advisor v2 Contract
* **thay đổi** Behavior Tester hiện pass 13/13 ở thời điểm System Advisor v2
* **thay đổi** Full System Tester hiện pass 17/17 ở thời điểm System Advisor v2

### Natural Command v2

* **thay đổi** Thay keyword hard-code bằng router dựa trên Capability Registry
* **thay đổi** Chuẩn hóa lệnh tiếng Việt có dấu/không dấu trước khi match intent
* **thay đổi** Giữ nguyên `find <từ khóa>`/`tim <từ khóa>` để search qua File Indexer/Everything fallback
* **thay đổi** Tool medium/dangerous hoặc có khả năng thay đổi file sẽ hỏi xác nhận trước khi chạy từ Natural Command
* **thay đổi** Behavior Tester thêm case Natural Command Router
* **thay đổi** Behavior Tester hiện pass 12/12 ở thời điểm Natural Command v2

## 2026-05-30

### Refactor

* Chuẩn hóa cấu trúc thư mục
* Chia module system/storage/search/automation/core

### Core

Thêm:

* risk_classifier.py
* safe_executor.py

### Duplicate Finder

Nâng cấp:

* Risk Classification
* Safe Delete
* Backup Report
* Protected Zone

### Temp Cleaner

Nâng cấp:

* Risk Classification
* Safe Delete
* Report
* Selective Cleanup

### Junk File Cleaner

Nâng cấp:

* Risk Classification
* Safe Executor
* Report

### Browser Cache Cleaner

Nâng cấp:

* Risk Classification cho browser cache
* Safe Executor
* Report
* Audit Log
* Không còn xóa trực tiếp bằng rmtree

### Recycle Bin Cleaner

**thay đổi** Nâng cấp:

* Scan Recycle Bin trước khi empty
* Preview report
* Confirmation flow nhiều bước
* Final report
* Audit Log

### Media Organizer

**thay đổi** Nâng cấp:

* Risk Classification
* Preview và chọn file trước khi move
* Chặn protected path
* Backup manifest
* Report
* Restore report
* Audit Log

### Empty Folder Finder

**thay đổi** Nâng cấp:

* Risk Classification
* Preview và chọn folder trước khi xóa
* Safe Executor
* Report
* Audit Log
* Không còn gọi send2trash trực tiếp

### Download Organizer

**thay đổi** Nâng cấp:

* Risk Classification
* Preview và chọn file trước khi move
* Bỏ qua file đang tải dở
* Backup manifest
* Report
* Restore report
* Audit Log

### Download Watcher

**thay đổi** Nâng cấp nhẹ:

* Giữ nguyên flow watcher hiện có
* Move bằng safe_move
* Audit Log cho từng file tự động move
* Startup scan report khi có thay đổi
* Helper trả về kết quả có cấu trúc để test

### Requirements

**thay đổi** Thêm:

* watchdog

### Main CLI Menu

**thay đổi** Nâng cấp:

* Thêm Temp Cleaner
* Thêm Empty Folder Finder
* Thêm Download Organizer
* Thêm Download Watcher
* Thêm Assistant Logs
* Thêm Behavior Tester
* **thay đổi** Thêm Config Manager
* **thay đổi** Thêm Audit Center
* **thay đổi** Thêm Undo Manager
* **thay đổi** Thêm Full System Tester
* **thay đổi** Thêm WizTree Adapter
* **thay đổi** Thêm External Apps Manager
* **thay đổi** Thêm Capability Registry
* Chuyển Tool Tester sang mục 21

### Tool Tester

**thay đổi** Mở rộng:

* Kiểm tra 30 tool
* Passed: 30
* Failed: 0

### Behavior Tester

**thay đổi** Thêm:

* Sandbox behavior tests
* Risk Classifier và Safe Delete bad cases
* Download Organizer roundtrip
* Download Watcher startup scan
* Media Organizer roundtrip
* Empty Folder Finder fake delete
* Missing manifest restore
* Startup Launcher config audit
* Read-only system snapshots
* Config System snapshot
* Audit Center snapshot
* Undo Manager roundtrip
* **thay đổi** Sandbox name dùng microsecond để tránh collision khi chạy song song
* Passed: 11
* Failed: 0

### Startup Launcher

**thay đổi** Nâng cấp audit:

* Ghi log khi xem profiles
* Report khi thêm app vào profile
* Report khi mở profile
* Lưu trạng thái từng app khi launch
* Behavior test không mở app thật

### Read-only System Tools

**thay đổi** Nâng cấp audit:

* Disk Checker có `get_disk_info`
* Disk Checker tạo report và audit log
* Process Monitor tạo report và audit log khi `show_top_process`
* Behavior Tester kiểm tra snapshot của Disk Checker và Process Monitor

### Config System

**thay đổi** Thêm config tập trung:

* Thêm `config/user_settings.json`
* `config/settings.py` đọc user settings và merge với default an toàn
* Gom Downloads path, default scan folder, thresholds, protected folders
* Gom browser cache path templates, watcher timing, file categories, media extensions
* Risk Classifier dùng protected/safe zone từ config
* Browser Cache Cleaner dùng browser cache templates từ config
* Download Organizer, Download Watcher, Media Organizer dùng category/extension từ config
* Disk Checker và Process Monitor dùng warning/critical threshold từ config
* Thêm `tools/core/config_manager.py`
* **thay đổi** Thêm nhóm `wiztree` cho exe_path, export_dir, timeout, use_admin và tùy chọn dùng trong System Advisor
* **thay đổi** Thêm nhóm `external_apps` cho Everything, smartctl, Sysinternals, 7-Zip, ExifTool, FFmpeg, rclone

### WizTree Adapter

**thay đổi** Thêm adapter WizTree read-only:

* Thêm `tools/storage/wiztree_adapter.py`
* Tự đọc executable từ config, mặc định `D:\WizTree\WizTree\WizTree64.exe`
* Export CSV vào `data/wiztree_exports`
* Parse CSV thành top folders và large files
* System Advisor có thể dùng WizTree để scan nhanh và fallback về Python scanner nếu lỗi
* Full System Tester kiểm tra parser bằng CSV mẫu trong sandbox, không chạy scan thật

### External Apps Integration

**thay đổi** Móc app ngoài vào tool theo hướng read-only:

* Thêm `tools/core/external_apps.py`
* File Indexer và Natural Command dùng Everything CLI để search nhanh, fallback về local index
* Disk Checker đọc thêm SMART health qua smartctl nếu khả dụng
* Media Organizer có chế độ đọc metadata bằng ExifTool/FFprobe, không move file
* Process Monitor ghi nhận Sysinternals helpers sẵn có
* External Apps Manager xem status/version và xuất report

### Capability Registry

**thay đổi** Thêm bản đồ capability chính thức:

* Thêm `tools/core/capability_registry.py`
* Mỗi tool có metadata về category, risk, confirmation, mutates_files, undo_strategy, report/log, external_apps
* Main CLI expose Capability Registry
* Full System Tester kiểm tra Tool Tester entry nào cũng có capability tương ứng
* Full System Tester kiểm tra risk trong registry không lệch với Tool Tester

### Audit System

**thay đổi** Thêm audit nền tảng:

* `create_report()` tự append vào `reports/report_index.jsonl`
* **thay đổi** Report schema v2 có `schema_version`, `action`, `risk_level`, `summary`, `manifest`, `undo_available`, `tags`
* **thay đổi** Report index có thêm `action`, `risk_level`, `summary`, `manifest`, `undo_available`
* **thay đổi** `create_report()` tự suy luận manifest từ results
* **thay đổi** Thêm `validate_report_file()` và `validate_report_data()`
* Report path tự thêm suffix khi trùng timestamp để tránh ghi đè
* Tool Tester chuyển sang dùng `create_report()`
* Thêm `tools/core/audit_center.py`
* Audit Center gom assistant logs và report index thành snapshot
* Main CLI expose Audit Center
* Behavior Tester kiểm tra Audit Center snapshot

### Undo System

**thay đổi** Thêm Undo Manager:

* Thêm `tools/core/undo_manager.py`
* Liệt kê manifest gần đây trong backups
* Preview manifest trước restore
* Restore manifest mặc định chỉ cho file trong backups
* Tạo report và audit log khi restore
* Main CLI expose Undo Manager
* Behavior Tester kiểm tra Undo Manager roundtrip

### Full System Tester

**thay đổi** Thêm test siêu tổng hợp:

* Compile all
* Tool import matrix
* Main menu coverage
* Config health
* Safety static audit
* Risk classifier guardrails
* Report manager và audit index
* **thay đổi** Report schema validation
* Audit Center health
* Undo Manager roundtrip
* Behavior suite subprocess
* **thay đổi** WizTree Adapter sample CSV
* **thay đổi** External Apps Registry
* **thay đổi** Capability Registry coverage
* Dependency health
* Git submodule health
* Passed: 16
* Failed: 0

### Repository Layout

**thay đổi** Dọn vấn đề repo lồng:

* Gỡ gitlink `AI_Desktop_Assistant` khỏi root index
* Move snapshot cũ từ `D:\tool\AI_Desktop_Assistant` vào `D:\tool\backups\AI_Desktop_Assistant_old_20260530_144926`
* Thêm `AI_Desktop_Assistant/` vào `.gitignore`
* Root project active là `D:\tool`

### Testing

Tool Tester:

Passed: 31

Failed: 0

Behavior Tester:

Passed: 18

Failed: 0

Full System Tester:

Passed: 21

Failed: 0

### GitHub

Đã khôi phục project sau khi cài lại Windows.

Toàn bộ thay đổi đã được push lên GitHub.
