# Tool Master Plan

**thay đổi** Tài liệu này chốt lại luồng tool tổng và kế hoạch chuẩn sau khi đã rà lại menu, Capability Registry, Advisor, Recommendation Center và Full System Tester.

## Trạng Thái Đã Verify

**thay đổi** Ngày rà lại: 2026-06-02.

**thay đổi** Kết quả hiện tại:

* **thay đổi** Main CLI đang expose 36 tool.
* **thay đổi** Capability Registry valid 36/36, không thiếu entry so với Tool Tester.
* **thay đổi** Tool Tester pass 36/36.
* **thay đổi** Behavior Tester pass 18/18.
* **thay đổi** Scenario Tester pass 6/6.
* **thay đổi** Full System Tester pass 26/26.
* **thay đổi** Capability summary: 23 safe, 7 medium, 6 dangerous; 11 tool có thể thay đổi file; 12 tool cần confirmation; 9 tool dùng external app.

## Luồng Tool Tổng Chuẩn

**thay đổi** Luồng đúng hiện tại:

1. **thay đổi** User vào `main.py` hoặc Natural Command.
2. **thay đổi** Natural Command v3 normalize lệnh, lookup qua Capability Registry và điều khiển recommendation queue theo index.
3. **thay đổi** Capability Registry cho biết tool nào được route, risk ra sao, có sửa file không, có cần confirmation không.
4. **thay đổi** Config System đọc path/threshold/protected folders/external apps từ `config/user_settings.json`.
5. **thay đổi** External Apps chỉ đóng vai trò helper read-only hoặc tăng tốc scan: Everything, WizTree, smartctl, ExifTool, FFprobe, Sysinternals.
6. **thay đổi** System Advisor v2 gom snapshot read-only từ storage, disk/SMART, process, external apps và audit reports.
7. **thay đổi** System Advisor v2 chỉ tạo recommendation, không tự cleanup, không xóa, không move.
8. **thay đổi** Recommendation Center gom recommendation thành queue read-only để user review.
9. **thay đổi** Action Policy Manager gắn quyết định keep/move/delete/manual/ignore theo path/context/recommendation trước khi mở action thật.
10. **thay đổi** Policy Enforcement Gate kiểm tra policy trước khi Guided Action Runner mở target tool.
11. **thay đổi** Candidate Review và Dry-run Action Planner phân loại candidate thành keep/manual/backup/move sau, nhưng không execute.
12. **thay đổi** Guided Action Runner mở tool được đề xuất từ recommendation sau khi user nhập token phù hợp.
13. **thay đổi** Scenario Tester tái hiện case rủi ro bằng file giả trước khi đụng dữ liệu thật.
14. **thay đổi** Feed Assistant Readiness và Pre-feed Bundle đóng gói pre-feed checklist/context, nhưng chưa feed/train thật.
15. **thay đổi** Nếu user chọn chạy tool thật, tool đó vẫn tự xử lý confirmation, risk classification, safe executor, manifest/undo và report/log.
16. **thay đổi** Audit Center, Report Manager và Undo Manager lưu lại lịch sử, report, manifest để kiểm tra sau.

## Nguyên Tắc Không Được Phá

**thay đổi** Advisor và Recommendation Center không được tự chạy cleanup tool.

**thay đổi** Guided Action Runner chỉ được mở tool sau xác nhận rõ ràng; không được bypass confirmation của tool đích.

**thay đổi** Mọi thao tác xóa phải đi qua `safe_executor.safe_delete()`.

**thay đổi** Mọi thao tác move có khả năng restore phải đi qua manifest/safe move.

**thay đổi** Tool medium/dangerous hoặc `mutates_files=True` phải có confirmation ở flow phù hợp.

**thay đổi** External apps không được tự xóa/move dữ liệu; chỉ được đọc metadata, scan, search hoặc export dữ liệu read-only.

**thay đổi** Action Policy không được tự thực thi cleanup; policy chỉ là lớp quyết định/ghi nhớ để Advisor, Recommendation Center và user nhìn rõ file nào phải giữ, hoãn, backup hoặc review thủ công.

**thay đổi** Full System Tester phải pass trước khi feed assistant hoặc refactor lớn.

## Phần Đã Xong

**thay đổi** Core safety:

* **thay đổi** Risk Classifier
* **thay đổi** Safe Executor
* **thay đổi** Report schema v2
* **thay đổi** Audit Center
* **thay đổi** Undo Manager nền tảng
* **thay đổi** Full System Tester

**thay đổi** Tool intelligence layer:

* **thay đổi** Capability Registry
* **thay đổi** Natural Command v3
* **thay đổi** System Advisor v2
* **thay đổi** Recommendation Center
* **thay đổi** Guided Action Runner
* **thay đổi** Action Policy Manager
* **thay đổi** Policy Enforcement Gate
* **thay đổi** Candidate Review
* **thay đổi** Dry-run Action Planner
* **thay đổi** Pre-feed Bundle

**thay đổi** External app layer:

* **thay đổi** Everything CLI cho search nhanh
* **thay đổi** WizTree Adapter cho storage scan read-only
* **thay đổi** smartctl cho disk SMART health
* **thay đổi** ExifTool/FFprobe cho media metadata
* **thay đổi** Sysinternals status cho diagnostics

## Gaps Còn Lại

**thay đổi** Gap 1: External App Health Report v2 da co mapping app -> tool phu thuoc.

**thay đổi** Gap 2: External App Health path drift detection đã hoàn thành; health report hiện cảnh báo nếu app/path/version/helper binary đổi so với baseline lần trước.

**thay đổi** Gap 3: Recommendation Center da co trang thai persistent pending/deferred/handled/ignored.

**thay đổi** Gap 4: Guided Action Runner đã có, mở tool từ recommendation với màn xác nhận risk thống nhất và dry-run contract test.

**thay đổi** Gap 5: Natural Command v3 đã điều khiển được queue kiểu `xem goi y`, `lam goi y so 1`, `hoan muc 2`, `danh dau muc 3 da xu ly`, `bo qua muc 4`.

**thay đổi** Gap 6: Advisor real-run calibration đã chạy trên `D:\`, đã sửa lỗi Unicode output và lọc test reports khỏi queue mặc định.

**thay đổi** Gap 7: Feed Assistant readiness report đã hoàn thành; chưa train/feed thật ở bước này.

**thay đổi** Gap 8: Scenario Tester đã hoàn thành để test fake-file trước khi xử lý case thật như Riot Games/archive/bộ cài.

**thay đổi** Gap 9: Action Policy Manager đã hoàn thành baseline Step 4; Step 3 deferred items được phủ policy 26/26, uncovered 0.

**thay đổi** Gap 10: Policy Enforcement Gate, Candidate Review, Dry-run Action Planner và Pre-feed Bundle đã hoàn thành; hiện chưa có auto cleanup.

## Kế Hoạch Chuẩn Từ Bây Giờ

### Bước 1 - External App Health Report v2

**thay đổi** Mục tiêu: làm rõ app ngoài nào đang phục vụ tool nào và nếu app lỗi thì tool nào bị giảm chất lượng.

**thay đổi** Việc cần làm:

* **thay đổi** Thêm dependency map: app -> dependent tools.
* **thay đổi** Export report có path, available, version, dependent tools, impact nếu missing.
* **thay đổi** Sinh recommendation nếu app thiếu hoặc path sai.
* **thay đổi** Full System Tester kiểm tra health report contract.
* **thay đổi** Docs cập nhật `EXTERNAL_APPS.md`.

**thay đổi** Không làm ở bước này: không auto tải app, không sửa path tự động, không chạy installer.

### Bước 2 - Recommendation Workflow v1

**thay đổi** Mục tiêu: queue có trạng thái để không lặp lại cùng một gợi ý.

**thay đổi** Việc cần làm:

* **thay đổi** Lưu queue vào `data/recommendation_queue.jsonl`.
* **thay đổi** Thêm trạng thái: pending, deferred, handled, ignored.
* **thay đổi** Có command xem pending/deferred/handled.
* **thay đổi** Export report queue theo trạng thái.
* **thay đổi** Behavior Tester kiểm tra state transition trên sandbox/data test.

### Bước 3 - Guided Action Runner

**thay đổi** Mục tiêu: từ một recommendation, user có thể mở tool được đề xuất với màn xác nhận rõ ràng.

**thay đổi** Flow:

1. **thay đổi** User chọn recommendation.
2. **thay đổi** Tool hiện suggested tool, risk, mutates_files, undo_strategy, external apps.
3. **thay đổi** User xác nhận chỉ để mở tool.
4. **thay đổi** Tool thật tiếp tục tự hỏi confirmation riêng nếu nó có thao tác nguy hiểm.

**thay đổi** Không làm ở bước này: không bypass confirmation của tool thật.

**thay đổi** Trạng thái: đã hoàn thành. Main CLI expose mục 30, Capability Registry/Tool Tester/Natural Command đã có entry, Behavior Tester và Full System Tester đều có contract test dry-run.

### Bước 4 cũ - Natural Command v3 Nhẹ

**thay đổi** Mục tiêu: điều khiển recommendation queue bằng lệnh tự nhiên.

**thay đổi** Ví dụ:

* **thay đổi** `xem gợi ý`
* **thay đổi** `làm gợi ý số 1`
* **thay đổi** `hoãn mục 2`
* **thay đổi** `đánh dấu mục 3 đã xử lý`

**thay đổi** Trạng thái: đã hoàn thành. Parser v3 xử lý preview/open/state update theo index, open vẫn đi qua Guided Action Runner và test dry-run không execute target tool.

### Bước 5 - Advisor Real Run Calibration

**thay đổi** Mục tiêu: chạy System Advisor v2 trên máy thật, xem recommendation có hợp lý không.

**thay đổi** Việc cần làm:

* **thay đổi** Chạy Advisor với Python scanner hoặc WizTree tùy tình huống.
* **thay đổi** Review report sinh ra.
* **thay đổi** Điều chỉnh rule nếu recommendation quá ồn hoặc thiếu trọng tâm.
* **thay đổi** Sau đó chạy Recommendation Center để kiểm tra queue.

**thay đổi** Trạng thái: đã hoàn thành lượt calibration đầu. Kết quả `D:\` hiện có 5 recommendation thực tế, không còn recommendation nhiễu từ report test/contract.

### Bước 5.5 - External App Path Drift Detection

**thay đổi** Mục tiêu: phát hiện sớm khi app ngoài bị move, mất file, đổi version hoặc update binary làm tool phụ thuộc chạy sai/chậm.

**thay đổi** Trạng thái: đã hoàn thành.

**thay đổi** Kết quả:

* **thay đổi** Baseline local nằm ở `data/external_apps_health_state.json` và đã ignore khỏi git.
* **thay đổi** Export External Apps Health report sẽ load baseline cũ, sinh drift events, rồi cập nhật baseline mới.
* **thay đổi** Drift event có các loại `path_changed`, `availability_changed`, `version_changed`, `binary_changed`.
* **thay đổi** Drift được đưa vào structured recommendation `source=external_apps_drift`, nhưng không tự sửa config/path.
* **thay đổi** Real export hiện tại: 16/16 app available, drift 0, recommendation 0.
* **thay đổi** Recommendation Center đọc buffer report lớn hơn trước khi lọc test reports, tránh test report che mất Advisor report thật.

### Bước 6 - Feed Assistant Chuẩn Bị

**thay đổi** Chỉ bắt đầu khi các điều kiện sau đạt:

* **thay đổi** Full System Tester pass.
* **thay đổi** Capability Registry valid.
* **thay đổi** External App Health Report v2 có dependency map rõ.
* **thay đổi** Recommendation queue có trạng thái ổn định.
* **thay đổi** Report schema đủ ổn định để assistant đọc.
* **thay đổi** Advisor real run đã được review thủ công.

**thay đổi** Trạng thái: đã hoàn thành readiness report/checklist.

**thay đổi** Kết quả mới nhất:

* **thay đổi** `tools/core/feed_readiness.py` đã được thêm.
* **thay đổi** Main CLI expose `Feed Assistant Readiness` ở mục 31.
* **thay đổi** Readiness report kiểm tra config, registry, external apps/drift, queue, latest full test, report schema, audit snapshot và docs feed source.
* **thay đổi** Latest readiness: ready, 9 pass, 0 warn, 0 fail.
* **thay đổi** Không còn warning trong readiness snapshot mới nhất.
* **thay đổi** Tool Tester pass 36/36, Behavior Tester pass 18/18, Scenario Tester pass 6/6, Full System Tester pass 26/26.

**thay đổi** Chưa train/feed thật ở giai đoạn này.

## Bước Nên Làm Ngay

**thay đổi** Bước review 5 pending recommendations thật đã hoàn thành.

**thay đổi** Kết quả review:

* **thay đổi** Ban đầu giữ pending: `downloads-folder-heavy`, `large-archive-files`; sau scan read-only đã xử lý state tiếp ở phần dưới.
* **thay đổi** Chuyển deferred: `large-video-files`.
* **thay đổi** Chuyển handled: `largest-folder-review`.
* **thay đổi** Chuyển ignored: `heavy-processes`.

**thay đổi** Bước tiếp theo đã chạy read-only:

* **thay đổi** `D:\Downloads` root có 0 file lẻ, nên Download Organizer không có gì để move.
* **thay đổi** `D:\Downloads\Riot Games` chiếm khoảng 36.24 GB nhưng là game data, không tự động xử lý.
* **thay đổi** `D:\Downloads\app` chiếm khoảng 7.72 GB.
* **thay đổi** Large File Finder thấy 6 archive/bộ cài lớn, tổng khoảng 8.99 GB.
* **thay đổi** `downloads-folder-heavy` đã chuyển `handled` cho flow Download Organizer.
* **thay đổi** `large-archive-files` đã chuyển `deferred` vì cần user chọn file cụ thể trước khi xóa/move.

**thay đổi** Queue mới nhất: 0 pending, 2 deferred, 2 handled, 1 ignored.

**thay đổi** Bước tiếp theo chuẩn nhất đã đổi: không xóa `D:\Downloads\Riot Games` vì là game data, không xóa các archive/bộ cài thật nếu user còn cần; mọi case cleanup/move nhạy cảm phải được tái hiện trong Scenario Tester bằng file giả trước.

## Step 2 Real Workflow Dry Run

**thay đổi** Đã triển khai bước 2 bằng workflow read-only/dry-run trên máy thật.

**thay đổi** Kết quả:

* **thay đổi** System Advisor snapshot thật trên `D:\`: 5 recommendation, 0 critical, 2 warning, 3 info.
* **thay đổi** `D:\Downloads` root có 0 file lẻ, nên không chạy Download Organizer trên file thật.
* **thay đổi** Queue sau review: 0 pending, 2 deferred, 2 handled, 1 ignored.
* **thay đổi** 2 deferred còn lại là `large-archive-files` và `large-video-files`; cả hai cần user quyết định thủ công trước khi xóa/move.
* **thay đổi** Guided Action Runner dry-run đã route đúng target tool và không execute tool thật.
* **thay đổi** Feed Readiness sau bước 2: ready, 8 pass, 0 warn, 0 fail.

**thay đổi** Nguyên tắc tiếp theo: nếu muốn xử lý archive/video thật, phải chọn rõ từng nhóm file hoặc tái hiện thêm case bằng Scenario Tester trước.

## Step 3 Deferred Storage Review

**thay đổi** Đã review sâu 2 mục deferred còn lại, vẫn theo chế độ read-only.

**thay đổi** Kết quả:

* **thay đổi** Report chính: `D:\tool\reports\step3_deferred_storage_review_20260602_201152.json`.
* **thay đổi** `large-archive-files`: 4 file, khoảng 5.48 GB, gồm Premiere/Downloads app installer bundle và backup/asset archives.
* **thay đổi** `large-video-files`: 22 file, khoảng 21.34 GB, gồm Steam Workshop media và backup/export videos.
* **thay đổi** Không có auto-delete candidate; toàn bộ vẫn là manual/deferred.
* **thay đổi** Queue hiện tại: 0 pending, 2 deferred, 2 handled, 1 ignored.
* **thay đổi** Feed Readiness sau bước 3: ready, 8 pass, 0 warn, 0 fail.

**thay đổi** Bước kế tiếp chỉ nên làm nếu user chọn rõ chính sách cho 2 nhóm deferred: giữ nguyên, chuyển sang ổ/folder khác, hoặc xóa từng file cụ thể sau khi tự xác nhận.

## Step 4 Action Policy / User Decision Layer

**thay đổi** Đã triển khai Action Policy Manager để biến quyết định của user thành rule đọc được bởi Recommendation Center và Feed Readiness.

**thay đổi** Kết quả:

* **thay đổi** File state local: `D:\tool\data\action_policy.jsonl`, đã ignore khỏi git.
* **thay đổi** Baseline có 11 policy: `ignore_forever`, `manual_only`, `needs_backup`, `move_later`; chưa có `delete_candidate`.
* **thay đổi** Game data như `Riot Games`/`League of Legends` và Steam Workshop được `ignore_forever`.
* **thay đổi** `D:\Downloads\app` và recommendation archive lớn là `manual_only`.
* **thay đổi** `D:\backup` và backup/export context là `needs_backup`.
* **thay đổi** Video lớn là `move_later`, chỉ move khi user chọn destination/chính sách giữ.
* **thay đổi** Recommendation Center hiện hiển thị policy decision cho từng item.
* **thay đổi** Feed Readiness có check `action_policy`: ready, 9 pass, 0 warn, 0 fail.
* **thay đổi** Tại thời điểm Action Policy baseline, Full System Tester có `Action Policy Contract`: pass 23/23.

**thay đổi** Ý nghĩa: tới đây assistant vẫn chưa tự cleanup, nhưng đã có lớp ghi nhớ quyết định để tránh hỏi lại/đề xuất sai với nhóm file user đã nói là cần giữ.

## Step 4 Follow-up Batch: Gate, Review, Planner, Bundle

**thay đổi** Đã hoàn thành cả 4 bước user yêu cầu làm liền.

**thay đổi** Kết quả:

* **thay đổi** Guided Action Runner có `policy_gate`; `ignore_forever`/`keep` bị chặn.
* **thay đổi** Các quyết định cần người dùng như `manual_only`, `needs_backup`, `move_later`, `delete_candidate` cần token mạnh trước khi mở tool thật.
* **thay đổi** Candidate Review report: `D:\tool\reports\candidate_review_20260603_200623.json`, 26 candidate, policy coverage 26/26, auto execute 0.
* **thay đổi** Dry-run Action Planner report: `D:\tool\reports\action_planner_20260603_200623.json`, 26 item, can execute now 0, delete candidate 0.
* **thay đổi** Pre-feed Bundle: `D:\tool\data\feed_bundles\pre_feed_bundle_20260603_200750.json`.
* **thay đổi** Pre-feed Bundle report: `D:\tool\reports\pre_feed_bundle_20260603_200750.json`.
* **thay đổi** Feed Readiness cuối mốc: `D:\tool\reports\feed_readiness_20260603_200751.json`, ready, 9 pass, 0 warn, 0 fail.
* **thay đổi** Full System Tester cuối mốc: `D:\tool\reports\full_system_tester_20260603_200729.json`, pass 26/26.

**thay đổi** Ý nghĩa: tool tổng đã có đường đi an toàn từ recommendation -> policy gate -> candidate review -> dry-run plan -> bundle chuẩn bị feed. Chưa có thao tác tự xóa/move.

## Deletion Safety / UX v2

**thay đổi** Risk Classifier da duoc tach thanh nhieu lop thay vi chi dua vao mot danh sach `protected_dir_names`.

**thay đổi** Cac lop hien tai:

* **thay đổi** `protected_root_paths`: chan cung root cua tool/project, mac dinh la `{BASE_DIR}`.
* **thay đổi** `protected_dir_names`: chi giu cac folder he thong/metadata that su nguy hiem nhu `Windows`, `Program Files`, `ProgramData`, `.git`.
* **thay đổi** `guarded_dir_names`: cac folder app/user data nhu `AppData`, game data, `Mobile`, `Zalo Data`; khong auto cleanup, nhung user co the review thu cong.
* **thay đổi** `dev_artifact_dir_names`: cac folder dev/build nhu `node_modules`, `__pycache__`, `build`, `dist`; khong con bi hard-block hang loat, duoc gan `review_required`.
* **thay đổi** Moi risk result co them `category`, `matched_rule`, `can_auto_delete`, `can_user_confirm` de user biet vi sao file bi chan hoac can review.

**thay đổi** Nguyen tac moi:

* **thay đổi** System/project van bi `protected` va `safe_delete()` se block.
* **thay đổi** Browser cache va temp file trong vung an toan co the la `safe_delete`.
* **thay đổi** AppData/user app data/dev artifacts mac dinh la `review_required`, khong auto delete bang lenh `all`.
* **thay đổi** Empty Folder Finder doi `all` thanh chi chon `SAFE_DELETE`; muon chon hang loat folder `REVIEW_REQUIRED` phai dung lua chon `review` va xac nhan rieng.

## Scenario Tester Layer

**thay đổi** `tools/core/scenario_tester.py` là lớp test bằng file giả cho các case user dễ gặp trước khi chạy tool thật.

**thay đổi** Scope hiện tại:

* **thay đổi** Downloads root: file ảnh/tài liệu/bộ cài, file `.crdownload` đang tải dở, folder app nested.
* **thay đổi** Game/app data: `Riot Games` và archive/bộ cài chỉ được phân loại `review_required`, không tự xóa.
* **thay đổi** Move/restore: Download Organizer và Media Organizer được test bằng fake move + manifest restore.
* **thay đổi** Cleanup scan: temp/junk/empty folders chỉ scan và phân loại trên sandbox, không xóa file thật.
* **thay đổi** Cleanup sandbox dùng guard path bắt buộc nằm dưới `D:\_ai_desktop_assistant_scenario_tests`.

**thay đổi** Khi gặp case thật gây khó hiểu, bước đúng là tái hiện bằng Scenario Tester trước rồi mới sửa tool thật nếu cần.

## External App Health Report v2

**thay đổi** Buoc External App Health Report v2 da duoc them vao `tools/core/external_apps.py`.

**thay đổi** Health v2 gom dependency map tu Capability Registry, bao gom ca app cau hinh rieng nhu `wiztree`.

**thay đổi** Moi app co them:

* **thay đổi** `state`: available, missing, disabled, unconfigured.
* **thay đổi** `dependent_tools`: tool nao dang phu thuoc app do.
* **thay đổi** `impact`: app thieu se lam giam chat luong phan nao.
* **thay đổi** `recommendations`: goi y read-only neu app thieu/path sai.

**thay đổi** External Apps Manager da co lua chon xem health v2 va xuat health report v2.

**thay đổi** External App Health path drift detection, Feed Assistant readiness report và Action Policy baseline đã hoàn thành. Queue thật hiện còn 2 nhóm deferred đã có policy, chưa có auto-delete.

## Recommendation Workflow v1

**thay đổi** Recommendation Center da co queue persistent tai `data/recommendation_queue.jsonl`.

**thay đổi** Queue dung fingerprint on dinh dua tren source, report tool, title, detail va suggested tool de tranh lap lai cung mot goi y khi Advisor/report chay lai.

**thay đổi** Trang thai ho tro:

* **thay đổi** `pending`: goi y moi, can xem.
* **thay đổi** `deferred`: tam hoan, van hien trong queue mac dinh.
* **thay đổi** `handled`: da xu ly, an khoi queue mac dinh.
* **thay đổi** `ignored`: bo qua, an khoi queue mac dinh.

**thay đổi** Recommendation Center hien co the sync queue, loc theo severity/state, doi trang thai va xuat report queue co summary theo state.

**thay đổi** Workflow nay van read-only doi voi du lieu user: no chi ghi state queue trong `data/` va report trong `reports/`, khong chay cleanup/tool thay user.

**thay đổi** Guided Action Runner đã hoàn thành bước mở tool từ queue qua xác nhận `OPEN`, có dry-run test và không tự mark handled.

## Guided Action Runner

**thay đổi** Thêm `tools/core/guided_action_runner.py`.

**thay đổi** Runner làm 4 việc:

* **thay đổi** Sync queue pending/deferred từ Recommendation Center.
* **thay đổi** Resolve `suggested_tool_id` qua Capability Registry.
* **thay đổi** Hiển thị risk, mutates_files, needs_confirmation, undo_strategy, external_apps và report gốc.
* **thay đổi** Chỉ mở tool sau khi user nhập đúng `OPEN`.

**thay đổi** Safety contract:

* **thay đổi** Runner không tự xóa/move/cleanup.
* **thay đổi** Runner không bypass confirmation của tool thật.
* **thay đổi** Dry-run tạo report nhưng không execute target tool.
* **thay đổi** Recommendation không tự chuyển `handled`; user phải xác nhận sau khi tool đích chạy xong.

**thay đổi** Feed Assistant readiness report đã hoàn thành; queue thật đã review, còn 2 nhóm deferred đã có Action Policy và cần user quyết định nếu muốn xử lý file thật.

## Natural Command v3 Nhẹ

**thay đổi** Natural Command v3 đã thêm parser riêng cho recommendation queue trước khi fallback sang Capability Registry.

**thay đổi** Lệnh hỗ trợ:

* **thay đổi** `xem goi y`: preview queue pending/deferred.
* **thay đổi** `lam goi y so N`: mở recommendation số N qua Guided Action Runner.
* **thay đổi** `hoan muc N`: chuyển recommendation số N sang `deferred`.
* **thay đổi** `danh dau muc N da xu ly`: chuyển recommendation số N sang `handled`.
* **thay đổi** `bo qua muc N`: chuyển recommendation số N sang `ignored`.

**thay đổi** Safety contract:

* **thay đổi** Lệnh mở theo index vẫn cần confirmation của Guided Action Runner khi chạy thật.
* **thay đổi** Lệnh state update chỉ ghi state queue, không xóa/move/cleanup.
* **thay đổi** Test dry-run chứng minh Natural Command không execute target tool trong test.

## Advisor Real Run Calibration

**thay đổi** Đã chạy `System Advisor v2` thật trên `D:\` bằng Python scanner read-only.

**thay đổi** Kết quả calibration:

* **thay đổi** Sửa lỗi crash khi in đường dẫn Unicode/tiếng Việt trong console Windows.
* **thay đổi** Recommendation Center mặc định bỏ qua report có tag test/contract.
* **thay đổi** Queue mặc định chỉ giữ snapshot mới nhất của `system_advisor`/`external_apps` để tránh duplicate từ report cũ.
* **thay đổi** Queue thật còn 5 recommendation pending, 2 warning và 3 info.

**thay đổi** Recommendation thực tế hiện tại:

* **thay đổi** `downloads-folder-heavy` -> Download Organizer.
* **thay đổi** `large-archive-files` -> Large File Finder.
* **thay đổi** `heavy-processes` -> Process Monitor.
* **thay đổi** `large-video-files` -> Media Organizer.
* **thay đổi** `largest-folder-review` -> Folder Size Analyzer.
