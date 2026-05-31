# Tool Master Plan

**thay đổi** Tài liệu này chốt lại luồng tool tổng và kế hoạch chuẩn sau khi đã rà lại menu, Capability Registry, Advisor, Recommendation Center và Full System Tester.

## Trạng Thái Đã Verify

**thay đổi** Ngày rà lại: 2026-05-31.

**thay đổi** Kết quả hiện tại:

* **thay đổi** Main CLI đang expose 29 tool.
* **thay đổi** Capability Registry valid 29/29, không thiếu entry so với Tool Tester.
* **thay đổi** Tool Tester pass 29/29.
* **thay đổi** Behavior Tester pass 14/14.
* **thay đổi** Full System Tester pass 18/18.
* **thay đổi** Capability summary: 17 safe, 6 medium, 6 dangerous; 11 tool có thể thay đổi file; 11 tool cần confirmation; 9 tool dùng external app.

## Luồng Tool Tổng Chuẩn

**thay đổi** Luồng đúng hiện tại:

1. **thay đổi** User vào `main.py` hoặc Natural Command.
2. **thay đổi** Natural Command v2 normalize lệnh và lookup qua Capability Registry.
3. **thay đổi** Capability Registry cho biết tool nào được route, risk ra sao, có sửa file không, có cần confirmation không.
4. **thay đổi** Config System đọc path/threshold/protected folders/external apps từ `config/user_settings.json`.
5. **thay đổi** External Apps chỉ đóng vai trò helper read-only hoặc tăng tốc scan: Everything, WizTree, smartctl, ExifTool, FFprobe, Sysinternals.
6. **thay đổi** System Advisor v2 gom snapshot read-only từ storage, disk/SMART, process, external apps và audit reports.
7. **thay đổi** System Advisor v2 chỉ tạo recommendation, không tự cleanup, không xóa, không move.
8. **thay đổi** Recommendation Center gom recommendation thành queue read-only để user review.
9. **thay đổi** Nếu user chọn chạy tool thật, tool đó vẫn tự xử lý confirmation, risk classification, safe executor, manifest/undo và report/log.
10. **thay đổi** Audit Center, Report Manager và Undo Manager lưu lại lịch sử, report, manifest để kiểm tra sau.

## Nguyên Tắc Không Được Phá

**thay đổi** Advisor và Recommendation Center không được tự chạy cleanup tool.

**thay đổi** Mọi thao tác xóa phải đi qua `safe_executor.safe_delete()`.

**thay đổi** Mọi thao tác move có khả năng restore phải đi qua manifest/safe move.

**thay đổi** Tool medium/dangerous hoặc `mutates_files=True` phải có confirmation ở flow phù hợp.

**thay đổi** External apps không được tự xóa/move dữ liệu; chỉ được đọc metadata, scan, search hoặc export dữ liệu read-only.

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
* **thay đổi** Natural Command v2
* **thay đổi** System Advisor v2
* **thay đổi** Recommendation Center

**thay đổi** External app layer:

* **thay đổi** Everything CLI cho search nhanh
* **thay đổi** WizTree Adapter cho storage scan read-only
* **thay đổi** smartctl cho disk SMART health
* **thay đổi** ExifTool/FFprobe cho media metadata
* **thay đổi** Sysinternals status cho diagnostics

## Gaps Còn Lại

**thay đổi** Gap 1: External App Health Report v2 còn thiếu mapping rõ app -> tool phụ thuộc.

**thay đổi** Gap 2: External App Health hiện có status/version/path basic, nhưng chưa có drift detection/cảnh báo path đổi theo thời gian.

**thay đổi** Gap 3: Recommendation Center chưa có trạng thái persistent như pending/deferred/handled/ignored.

**thay đổi** Gap 4: Chưa có Guided Action Runner để mở tool từ recommendation với màn xác nhận risk thống nhất.

**thay đổi** Gap 5: Natural Command chưa điều khiển được queue kiểu "xem gợi ý số 1", "hoãn mục 2", "mở tool của mục 3".

**thay đổi** Gap 6: Chưa có lần chạy System Advisor v2 thực tế có review thủ công output trên máy thật để calibrate recommendation.

**thay đổi** Gap 7: Feed assistant chưa nên làm cho đến khi health report và recommendation workflow ổn định hơn.

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

### Bước 4 - Natural Command v3 Nhẹ

**thay đổi** Mục tiêu: điều khiển recommendation queue bằng lệnh tự nhiên.

**thay đổi** Ví dụ:

* **thay đổi** `xem gợi ý`
* **thay đổi** `làm gợi ý số 1`
* **thay đổi** `hoãn mục 2`
* **thay đổi** `đánh dấu mục 3 đã xử lý`

### Bước 5 - Advisor Real Run Calibration

**thay đổi** Mục tiêu: chạy System Advisor v2 trên máy thật, xem recommendation có hợp lý không.

**thay đổi** Việc cần làm:

* **thay đổi** Chạy Advisor với Python scanner hoặc WizTree tùy tình huống.
* **thay đổi** Review report sinh ra.
* **thay đổi** Điều chỉnh rule nếu recommendation quá ồn hoặc thiếu trọng tâm.
* **thay đổi** Sau đó chạy Recommendation Center để kiểm tra queue.

### Bước 6 - Feed Assistant Chuẩn Bị

**thay đổi** Chỉ bắt đầu khi các điều kiện sau đạt:

* **thay đổi** Full System Tester pass.
* **thay đổi** Capability Registry valid.
* **thay đổi** External App Health Report v2 có dependency map rõ.
* **thay đổi** Recommendation queue có trạng thái ổn định.
* **thay đổi** Report schema đủ ổn định để assistant đọc.
* **thay đổi** Advisor real run đã được review thủ công.

**thay đổi** Chưa train ở giai đoạn này.

## Bước Nên Làm Ngay

**thay đổi** Bước tiếp theo chuẩn nhất là External App Health Report v2.

**thay đổi** Lý do: trước khi assistant đọc/ra quyết định, nó cần biết tool nào đang phụ thuộc app ngoài nào, app nào đang thiếu, app nào path bị sai và nếu thiếu thì ảnh hưởng tới độ chính xác/tốc độ ra sao.
