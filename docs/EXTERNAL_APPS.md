# External Apps

**thay đổi** File này ghi vị trí chuẩn cho các app ngoài được dùng để tăng độ chính xác/tốc độ cho AI Desktop Assistant.

## Đã Có Trên Máy

| App | Trạng thái | Vị trí chuẩn | Ghi chú |
| --- | --- | --- | --- |
| WizTree | OK | `D:\WizTree\WizTree\WizTree64.exe` | Dùng cho scan dung lượng nhanh, read-only. |
| Everything | OK | `D:\SearchEverything\Everything\Everything.exe` | Đang là bản x86 `1.4.1.1032`, vẫn dùng được. Có service chạy tự động. |
| Everything CLI | OK | `D:\tool\external\everything\es.exe` | Bản x64 `1.1.0.30`. Đây là path ổn định tool sẽ trỏ tới. |
| Sysinternals Suite | **thay đổi** OK | `D:\tool\external\sysinternals\` | Đã có các file chính: `autorunsc64.exe`, `handle64.exe`, `procexp64.exe`, `RAMMap64.exe`, `du64.exe`, `sigcheck64.exe`. |
| smartmontools | **thay đổi** OK | `C:\Program Files\smartmontools\bin\smartctl.exe` | Đã cài version `7.5`. |
| 7-Zip | **thay đổi** OK | `C:\Program Files\7-Zip\7z.exe` | Đã cài version `26.01 x64`. |
| rclone | **thay đổi** OK | `D:\tool\external\rclone\rclone.exe` | Đã giải nén từ zip, version `1.74.2`. |
| CrystalDiskInfo | **thay đổi** OK | `C:\Program Files\CrystalDiskInfo\DiskInfo64.exe` | Đã cài version `9.9.1`. |
| ExifTool | **thay đổi** OK | `D:\tool\external\exiftool\exiftool.exe` | Đã giải nén Windows executable 64-bit, version `13.59`; giữ kèm `exiftool_files`. |
| FFmpeg | **thay đổi** OK | `D:\tool\external\ffmpeg\bin\ffmpeg.exe` | Đã giải nén release essentials build `8.1.1`. |
| FFprobe | **thay đổi** OK | `D:\tool\external\ffmpeg\bin\ffprobe.exe` | Đi kèm FFmpeg essentials build `8.1.1`. |

## Chưa Đúng Hoặc Chưa Hoàn Tất

| App | Trạng thái | File hiện có | Cần làm |
| --- | --- | --- | --- |
| Không còn mục bắt buộc | **thay đổi** OK | - | Các app ưu tiên hiện đã có đủ path chuẩn. |

## Vị Trí Tải/Cài Khuyến Nghị

| App | Nên đặt file ở đâu | File chính tool cần | Dùng cho |
| --- | --- | --- | --- |
| Everything x64 | `D:\SearchEverything\Everything\Everything.exe` hoặc `C:\Program Files\Everything\Everything.exe` | `Everything.exe` | Search/index file nhanh. |
| Everything CLI x64 | `D:\tool\external\everything\es.exe` | `es.exe` | Gọi Everything từ command line. |
| Sysinternals Suite | `D:\tool\external\sysinternals\` | `autorunsc64.exe`, `handle64.exe`, `procexp64.exe`, `RAMMap64.exe`, `du64.exe`, `sigcheck64.exe` | Startup, process, file lock, RAM, disk usage, signature check. |
| smartmontools | `C:\Program Files\smartmontools\bin\smartctl.exe` | `smartctl.exe` | SMART health, nhiệt độ, lỗi SSD/HDD. |
| CrystalDiskInfo | `C:\Program Files\CrystalDiskInfo\DiskInfo64.exe` hoặc `D:\tool\external\crystaldiskinfo\DiskInfo64.exe` | `DiskInfo64.exe` | Xem sức khỏe ổ bằng GUI; smartctl phù hợp tích hợp CLI hơn. |
| 7-Zip | `C:\Program Files\7-Zip\7z.exe` | `7z.exe` | Kiểm tra/giải nén/nén archive. |
| ExifTool | `D:\tool\external\exiftool\exiftool.exe` | `exiftool.exe` | Đọc metadata ảnh/video/audio. Nếu tải `exiftool(-k).exe`, đổi tên thành `exiftool.exe`. |
| FFmpeg | `D:\tool\external\ffmpeg\bin\ffmpeg.exe` | `ffmpeg.exe`, `ffprobe.exe` | Đọc media duration/codec, thumbnail, kiểm tra file media. |
| rclone | `D:\tool\external\rclone\rclone.exe` | `rclone.exe` | Backup/sync cloud sau này. |

## Quy Ước

**thay đổi** App dạng portable/zip nên đặt trong `D:\tool\external\<app_name>\`.

**thay đổi** App dạng installer có service/shell integration nên cài vào vị trí mặc định hoặc vị trí riêng ổn định, rồi ghi lại path chính trong bảng trên.

**thay đổi** Thư mục `D:\tool\external\` bị ignore khỏi git để không đưa file exe/zip vào repository.

## Tích Hợp Vào Tool

**thay đổi** Các app ngoài hiện được móc qua `tools/core/external_apps.py` và cấu hình trong `config/user_settings.json`.

**thay đổi** Bước tiếp theo theo `D:\tool\docs\TOOL_MASTER_PLAN.md` là External App Health Report v2: map app -> tool phụ thuộc, path/version, impact nếu missing và recommendation khi app lỗi.

| App | Tool đang dùng | Cách dùng |
| --- | --- | --- |
| Everything CLI | File Indexer, Natural Command | Search nhanh trước, fallback local index nếu lỗi. |
| smartctl | Disk Checker | Đọc SMART health read-only. |
| ExifTool | Media Organizer | Đọc metadata media read-only. |
| FFprobe | Media Organizer | Đọc duration/codec/resolution read-only. |
| Sysinternals | Process Monitor | Ghi nhận helper sẵn sàng cho diagnostics. |
| 7-Zip | External Apps Registry | Sẵn sàng cho archive validation sau này. |
| rclone | External Apps Registry | Sẵn sàng cho backup/sync sau này. |

## External App Health Report v2

**thay đổi** `tools/core/external_apps.py` da co health report v2 de map app ngoai -> tool dang phu thuoc.

**thay đổi** Report v2 gom:

* **thay đổi** `path`, `available`, `version`, `state` cho tung app.
* **thay đổi** `dependent_tools` va `dependent_tool_count` lay tu Capability Registry.
* **thay đổi** `impact` de noi ro neu app thieu thi tool nao bi cham/mat do chinh xac.
* **thay đổi** `recommendations` neu app missing/disabled/unconfigured.
* **thay đổi** `impacted_tool_ids` de Recommendation Center/Advisor doc duoc tool nao dang bi anh huong.

**thay đổi** Menu External Apps Manager hien co:

* **thay đổi** `1` xem status co ban.
* **thay đổi** `2` xem status + version.
* **thay đổi** `3` xem health v2 + dependency map.
* **thay đổi** `4` xuat health report v2.
* **thay đổi** `5` test Everything search.

**thay đổi** Health v2 van read-only: khong auto tai app, khong sua path, khong chay installer.

## External App Path Drift Detection

**thay đổi** Health v2 hiện có drift detection dựa trên baseline local `D:\tool\data\external_apps_health_state.json`.

**thay đổi** Baseline này chỉ lưu trạng thái app ngoài của máy hiện tại và đã được ignore khỏi git.

**thay đổi** Drift detection đang bắt các trường hợp:

* **thay đổi** `path_changed`: config/path app đổi so với lần export trước.
* **thay đổi** `availability_changed`: app từ OK thành missing hoặc ngược lại.
* **thay đổi** `version_changed`: version đổi khi có dữ liệu version.
* **thay đổi** `binary_changed`: cùng path nhưng file size/modified đổi.

**thay đổi** Khi drift ảnh hưởng tool đang phụ thuộc app đó, report tạo structured recommendation `source=external_apps_drift` để Recommendation Center/Guided Action Runner nhìn thấy.

**thay đổi** Export thật gần nhất: 16/16 app available, drift 0, recommendation 0.
