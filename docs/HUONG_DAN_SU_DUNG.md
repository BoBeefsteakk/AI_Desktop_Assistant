# Hướng dẫn sử dụng — AI Desktop Assistant

Trợ lý tự quét máy, tư vấn sức khỏe ổ cứng / file rác bằng tiếng Việt. Bạn chỉ
việc **chọn xóa hay giữ** — không phải tự chạy tool nào.

---

## 1. Hai cách dùng

### A. Trợ lý nền (tự động — khuyến nghị)
- Chạy ẩn dưới khay đồng hồ (góc dưới phải), tự quét theo chu kỳ.
- Thấy file rác mới → bắn **toast thông báo** + icon khay đổi **màu cam**.
- **Click icon khay** (hoặc chuột phải → **"Mở dọn dẹp"**) → mở app tới chỗ dọn.

Bật trợ lý nền (cách **ẩn hẳn, không nháy terminal** — khuyến nghị):
```
Double-click  start_hidden.vbs
```
Hoặc bằng lệnh (cũng không có console vì dùng pythonw):
```
pythonw -m tools.ui.tray_assistant
```
Menu chuột phải ở icon khay: **Mở dọn dẹp · Quét ngay · Thoát**.

> Quét nền dùng scanner Python (in-process) nên **không bật cửa sổ terminal** lúc quét.

### B. Mở app trực tiếp (khi muốn kiểm tra ngay)
```
python -m tools.ui.bot_panel
```
App tự quét máy thật ngay khi mở.

---

## 2. Màn hình chính (tab "Trợ lý")

Từ trên xuống:

| Khu vực | Ý nghĩa |
|---|---|
| **Nút góc phải** | `Kiểm tra máy thật` (quét lại) · `Xem thử (file giả)` / `Chạy demo` (thử an toàn) · `Xem chi tiết kỹ thuật` |
| **Theo dõi định kỳ** | Nút `Kiểm tra vấn đề mới` — so với lần quét trước, báo có gì mới |
| **Dọn dẹp 1 chạm** | "AI đề nghị dọn N file rác (~X GB)" + nút **`Đồng ý dọn`**; `Xem từng file` để chọn lẻ |
| **Thư mục cần kiểm tra** | Đổi ổ/thư mục quét (`Chọn thư mục`); `Mở báo cáo` xem JSON |
| **Tóm tắt AI tìm thấy** | Đếm nhanh: Cần backup / Cần move / Dọn an toàn / Cần xem / Được bảo vệ |
| **Sức khỏe ổ cứng & tư vấn** | Giải thích "vì sao ổ đầy", ổ đĩa, SMART, file nặng, tư vấn theo mức độ |

---

## 3. Luồng dọn file rác

1. App quét xong → mục **"Dọn dẹp 1 chạm"** hiện số file rác an toàn.
2. Bấm **`Đồng ý dọn`** (dọn hết) **hoặc** `Xem từng file` rồi chọn từng cái.
3. Xác nhận (nhập token) → file vào **Recycle Bin** (khôi phục được).

> **An toàn:** chỉ file `safe_delete` mới được đề xuất xóa. File project/tài liệu/
> game → "cần xem tay", không bao giờ tự xóa. Mọi thao tác qua Recycle Bin.

---

## 3b. Tab "Sắp xếp" (4 tool sắp xếp file)

Mỗi mục: bấm **`Quét`** → chọn dòng (giữ Ctrl/Shift chọn nhiều) → bấm **`Áp dụng`**.

| Mục | Làm gì | Áp dụng |
|---|---|---|
| **Sắp xếp Downloads** | Gom file Downloads theo loại/ngày | Di chuyển (khôi phục được) |
| **Sắp xếp theo loại** | Gom **mọi** file cùng loại vào 1 folder (Ảnh / Video / Audio / Tài liệu / Nén / Cài đặt / Khác) | Di chuyển (khôi phục được) |
| **Tìm file trùng** | Tìm bản sao — **luôn giữ file gốc (cũ nhất)**, xóa bản mới | Xóa → Recycle Bin |
| **Tìm folder rỗng** | Tìm folder rỗng (gồm cả folder lồng nhau toàn rỗng) | Xóa → Recycle Bin |

> Di chuyển có **manifest** trong `backups/` để hoàn tác. Xóa vào **Recycle Bin**.
> File PROTECTED luôn bị loại khỏi danh sách.

---

## 3c. Tab "Lịch sử" (AI đã làm gì + hiệu quả)

- **Hiệu quả 7 ngày qua**: tổng file đã sắp xếp / dọn-xóa / số lần thao tác.
- **Hành động gần đây**: mỗi dòng là một lần bạn dùng app, kèm thời gian.
- Chỉ tính **hành động thật bạn bấm trong app** (không tính chạy test/CLI).
- Bấm **`Làm mới`** để cập nhật.

---

## 4. Hỏi AI (tab Trợ lý)

Gõ câu hỏi tiếng Việt, vd:
- "tại sao ổ C đầy"
- "file nào nặng nhất"
- "máy có gì cần dọn"

AI trả lời dựa trên lần quét gần nhất (read-only, không tự xóa).

---

## 5. Quiet mode (không làm phiền)

Khi bạn đang **chơi game / xem phim fullscreen**, trợ lý nền **nín** — không bắn
toast. Thoát fullscreen mới báo.

---

## 6. Tự chạy khi khởi động Windows (tùy chọn)

Bật (chạy 1 lần):
```
py -c "from tools.automation.background_registration import enable_background_autostart as e; e()"
```
Tắt:
```
py -c "from tools.automation.background_registration import disable_background_autostart as d; d()"
```

---

## 7. Lưu ý kỹ thuật

- **Toast chỉ để báo** — không bấm vào toast được (giới hạn Windows với app Python
  không đóng gói). Hành động "mở để dọn" nằm ở **icon khay hệ thống**.
- Báo cáo lưu ở `reports/` (JSON, có timestamp).
- Máy chỉ dùng **Python 3.12** (không dùng `py -3.11`).
- Cần thư viện: `pip install -r requirements.txt` (gồm winotify, pystray, Pillow).
