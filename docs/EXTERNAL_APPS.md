# External Apps

**thay đổi** File này ghi vị trí chuẩn cho các app ngoài được dùng để tăng độ chính xác/tốc độ cho AI Desktop Assistant.

## Đã Có Trên Máy

| App | Trạng thái | Vị trí chuẩn | Ghi chú |
| --- | --- | --- | --- |
| WizTree | OK | `D:\WizTree\WizTree\WizTree64.exe` | Dùng cho scan dung lượng nhanh, read-only. |
| Everything | OK | `D:\SearchEverything\Everything\Everything.exe` | Đang là bản x86 `1.4.1.1032`, vẫn dùng được. Có service chạy tự động. |
| Everything CLI | OK | `D:\tool\external\everything\es.exe` | Bản x64 `1.1.0.30`. Đây là path ổn định tool sẽ trỏ tới. |

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
