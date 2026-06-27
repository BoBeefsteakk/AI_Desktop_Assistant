# Phase 8 Roadmap — Trợ lý nền thật sự

> **Đích cuối (nhắc lại):** AI tự chạy full tool → tư vấn sức khỏe ổ cứng / file rác / file
> nặng bằng tiếng Việt → user chỉ chọn **xóa hay giữ**. **User không cần mở app, không
> chạy tool nào.**
>
> Phase 7 đã đạt "tự" *sau khi mở app*. Phase 8 lấp đúng khoảng cách còn lại: chữ **"tự"**
> khi máy đang chạy nền — máy tự báo, user không phải mở gì.

Quy ước: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong. Mỗi mục có **Owner** + **Acceptance**.

**Tình hình nhân lực:** Codex hết token tuần này → **Claude solo**. Backend do Claude viết
tạm, **Codex review lại sau khi hồi session** (ghi vào `.agents/AGENT_MAILBOX.md` khi tới lúc).
Trong lúc solo vẫn giữ ownership cũ làm tham chiếu: safety files (adapter/token/safe_executor)
sửa tối thiểu, không nới quyền xóa.

---

## Sprint 0 — Dọn nhà (làm trước, gỡ nợ kỹ thuật)

- [ ] **Merge PR #11** (Bước 5) → Phase 7 đóng trên `main`. Owner: user merge.
- [ ] **Dọn nhánh đã merge** (local + remote): `phase7-step2/step3/step3-plan/ui-inline-delete`,
      `codex/*` đã gộp. Owner: Claude.
      - Acceptance: `git branch` chỉ còn `main` + nhánh đang làm.
- [ ] **Nén `PROJECT_STATUS.md`** (đang 1133 dòng → context bloat): giữ khối "trạng thái
      hiện tại" ở đầu, chuyển log lịch sử sang `docs/STATUS_ARCHIVE.md`. Owner: Claude.
      - Acceptance: `PROJECT_STATUS.md` < ~150 dòng, đọc không bị truncate.

---

## Phase 8 — Trợ lý nền (cốt lõi để đạt goal)

### 8.1 — Quét nền theo lịch (không cần mở UI)  ✅ XONG
- [x] Tận dụng `run_periodic_scan` (đã có, read-only) + autorun launcher để chạy quét
      ngầm định kỳ khi máy rảnh, KHÔNG bật cửa sổ UI.
      → `tools/automation/background_assistant.py`: `run_background_assistant_loop(interval_minutes)`
      + `run_background_assistant_cycle()`; launcher `start_background_assistant.bat`.
  - **Owner:** Claude wiring; backend `run_periodic_scan` đã sẵn (Codex REQ#3).
  - **Acceptance:** có tiến trình/lịch chạy `run_periodic_scan` nền; ghi kết quả ra
    `reports/`; read-only tuyệt đối (không xóa/move); Full System Tester pass.

### 8.2 — Windows toast notification (mảnh thiếu lớn nhất)  ✅ XONG
- [x] Khi quét nền thấy vấn đề mới → bắn toast Windows (title/message từ
      `run_periodic_scan`). → `tools/ui/toast_notifier.py: show_toast(...)`, dùng
      PowerShell + Windows Runtime, KHÔNG cần dep ngoài, read-only.
  - **Owner:** Claude (UI/OS layer).
  - **Acceptance:** toast hiện thật trên Windows; chỉ bắn khi `should_notify=True` +
    có file `safe_delete`; không bắn spam (1 lần/phiên quét); không tự xóa gì.

### 8.3 — Click để mở thẳng banner "Dọn 1 chạm"  ✅ XONG (qua tray icon)
- [x] Mở `bot_panel` nhảy thẳng banner Dọn 1 chạm, highlight file rác sẵn.
      → `bot_panel --cleanup` → `_focus_cleanup_on_open()`; launcher `open_cleanup.py`.
- [x] **Cách click chắc ăn: tray icon** (`tools/ui/tray_assistant.py`) — icon khay
      hệ thống, click / menu "Mở dọn dẹp" → `open_cleanup_panel()` (callback Python,
      luôn chạy). Vòng quét nền chạy trong thread của tray, icon đổi cam khi có vấn đề.
- [~] Toast-click qua protocol (`toast_protocol.py` + AUMID shortcut) đã làm nhưng
      **Windows chặn toast activation cho app Python không-đóng-gói** (dù protocol
      mở được từ shell). Bỏ launch_arg khỏi toast để click toast không ra dialog lỗi;
      hành động chuyển sang tray icon. Giữ lại `toast_protocol.py` cho tương lai.
  - **Owner:** Claude.
  - **Acceptance:** từ toast tới chỗ chọn xóa/giữ ≤ 1 cú bấm; xóa vẫn qua token +
    Recycle Bin.

### 8.4 — Quiet mode (không làm phiền khi chơi game/fullscreen)  ✅ XONG (cơ bản)
- [x] Hoãn toast khi cửa sổ foreground đang fullscreen (game/phim/present).
      → `background_assistant._is_quiet_mode()` so cửa sổ foreground với màn hình.
      (Tinh chỉnh sâu theo process game cụ thể để Codex làm sau.)
  - **Owner:** Claude (Codex tinh chỉnh logic sau).
  - **Acceptance:** đang fullscreen → không toast; thoát ra mới báo.

---

## Phase 9 — Tin cậy & đánh bóng

- [ ] Polish UI lên mốc nghiệm thu 90% theo `docs/UI_ACCEPTANCE.md`.
- [ ] Trang "Lịch sử AI đã tư vấn gì" — để user thấy trợ lý làm việc đều.
- [ ] Đo hiệu quả: GB dọn được/tuần, số đề xuất đúng, số lần user bấm Giữ.

---

## Nguyên tắc giữ nguyên (từ Phase 7)
- Mỗi việc trên branch riêng (`claude/...`) → PR vào `main` → user merge.
- Mọi xóa/move/backup tiếp tục qua Selection Decision Report + token + Recycle Bin.
  **KHÔNG bypass confirmation.**
- Quét nền + toast là **read-only**: chỉ scan và báo, không tự đụng file.
- Trước khi push: Tool Tester + Full System Tester phải pass.
- Backend Claude viết tạm → đánh dấu trong mailbox để **Codex review lại sau**.

---

## Thứ tự đề xuất
1. **Sprint 0** (gỡ nợ) →
2. **8.1 + 8.2** (quét nền + toast — mang lại cảm giác "đích cuối" rõ nhất) →
3. **8.3** (one-click từ toast) →
4. **8.4 + Phase 9** (đánh bóng).
