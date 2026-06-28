# Phase 10 — Dashboard UI (Spotify-style) + chạy ẩn

Giao diện mới dạng **Spotify desktop** cho AI Desktop Assistant, dùng **pywebview**
(HTML/CSS/JS) nhưng **giữ nguyên toàn bộ backend an toàn** (read-only + token-gated).

## Kiến trúc
- `tools/ui/dashboard_data.py` — bộ cấp số liệu **read-only**: `get_dashboard_snapshot()`,
  `get_clean_details()`, `get_organizer_overview()`, `get_history_overview()`.
- `tools/ui/web/dashboard.html` — giao diện: nền đen, panel bo góc, sidebar "Thư viện",
  **gauge tròn (SVG)** + **biểu đồ ngang (CSS)** vẽ thuần (không cần CDN).
- `tools/ui/dashboard_app.py` — cửa sổ pywebview + cầu nối `DashboardApi` (JS↔Python).
  Mọi thao tác xóa/move thật vẫn mở Bot Panel cũ qua `open_cleanup()` (token-gated).

## Đã xong
- [x] Màn **Trang chủ**: 3 gauge tròn (Ổ C / RAM / CPU) + biểu đồ ngang dung lượng các ổ + 4 thẻ điều hướng.
- [x] Màn **Dọn dẹp**: gauge số file/dung lượng rác + danh sách file + nút mở bảng xác nhận.
- [x] Màn **Sắp xếp**: biểu đồ ngang (file chưa sắp xếp / bản trùng / folder rỗng) + dung lượng theo loại.
- [x] Màn **Lịch sử**: 3 thẻ metric + biểu đồ ngang "AI đã làm gì" + danh sách gần đây.
- [x] Màn **Cài đặt** (cơ bản).
- [x] **Chạy ẩn khi khởi động**: `background_registration` dùng launcher `.vbs`
  (`pythonw`, window style 0 → không terminal), tự gỡ `Boot.cmd`/`.cmd` cũ.
- [x] Tray icon mở **dashboard mới** thay vì bot panel cũ.
- [x] requirements.txt thêm `pywebview`.
- [x] Safety static audit sạch (`findings: []`).

## Chạy
```
python -m tools.ui.dashboard_app        # mở dashboard
pythonw -m tools.ui.tray_assistant      # chạy ẩn (tray)
# Tự chạy khi khởi động:
py -c "from tools.automation.background_registration import enable_background_autostart as e; e()"
```

## TODO / nâng cấp tiếp (nếu còn thời gian)
- [ ] Cho phép **chọn dọn/giữ + xác nhận token NGAY trong dashboard** (hiện vẫn mở Bot Panel cũ).
- [ ] Nút "Áp dụng" cho Sắp xếp (move) ngay trong dashboard (qua token-gated adapter).
- [ ] Đóng gói `.exe` (PyInstaller) để người không rành kỹ thuật dùng.
- [ ] Test headless cho dashboard_data (mock psutil) + thêm vào Full System Tester.
- [ ] `scan_duplicates` in stdout "Dang quet..." — nên tắt print khi gọi từ UI.
