# Phase 7 Checklist — AI Assistant (đích cuối)

> **Đích cuối:** AI tự chạy full tool → tư vấn sức khỏe ổ cứng / file rác / file nặng
> bằng tiếng Việt → user chỉ chọn **xóa hay giữ**. User không phải tự chạy tool nào.

Quy ước: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong. Mỗi mục có **Owner**, **Acceptance** (điều kiện coi như xong).
Chủ trì: **Claude** = kiến trúc + UI (`tools/ui/`). **Codex** = backend (`tools/core`, `storage`, `search`, `automation`).
File an toàn (adapter/token/safe_executor): Codex viết, **Claude review trước merge**.

---

## Đã xong (nền tảng)

- [x] Advisory Dashboard v1: auto-scan khi mở app + panel sức khỏe ổ cứng (Claude)
- [x] UI hiện đại ttkbootstrap, phân biệt DEMO/MÁY THẬT (Claude)
- [x] Bước 1: nút Xóa/Giữ inline cho file rác (Claude)
- [x] REQ#1: `explanation` + `disk_full_reason` ở System Advisor (Codex)
- [x] REQ#2: `answer_user_question()` ở Natural Command (Codex)

---

## Việc của CLAUDE (kiến trúc + UI)

### Bước 2 — Ghép giải thích + hỏi đáp vào UI  ✅ XONG (PR #6)
- [x] Hiển thị `explanation` của mỗi recommendation trong panel "AI tư vấn"
- [x] Hiển thị `disk_full_reason.reason_text` + `action_text` ở đầu panel sức khỏe
- [x] Thêm ô "Hỏi AI" gọi `answer_user_question(text, auto_scan_result=last_scan_data)` và in `answer_text`

### Bước 3 — Gộp luồng còn 1 bước  ✅ XONG (PR #9)
- [x] Sau quét, hiện thẳng "Đề nghị dọn N file rác (~X GB)" + 1 nút [Đồng ý dọn]
- [x] Cột "Lý do an toàn xóa" (reason_text) trong bảng Dọn nhanh; giữ luồng nâng cao ở tab Chi tiết

### Bước 5 (phần UI) — Thông báo quét định kỳ  ✅ XONG (PR #11)
- [x] Banner "Theo dõi định kỳ" + nút "Kiểm tra vấn đề mới" gọi `run_periodic_scan`, hiện title/message, đổi màu khi có vấn đề mới (read-only)

---

## Việc của CODEX (backend)

### REQ#3 — Quét định kỳ read-only (Bước 5 phần backend)
- [x] Tận dụng `boot_runner.py` + `startup_scan.py` làm chế độ quét định kỳ
- [x] Trả payload thông báo có cấu trúc (số vấn đề mới, mức nghiêm trọng nhất)
- [x] Read-only tuyệt đối: không tự xóa/move; expose hàm public ổn định cho UI gọi
  - **Acceptance:** hàm trả dict có schema rõ + `safety_contract.read_only=True`; ghi tên hàm vào mailbox; Full System Tester pass.
  - **thay doi:** public `tools.automation.boot_runner.run_periodic_scan(...)`, schema `periodic_scan_notification_v1`; Full System Tester 39/39.

### REQ#4 — Lý do xóa được/không cho từng file (hỗ trợ Bước 2/3)
- [x] Với mỗi item trong selection, bổ sung field `reason_text` ngắn gọn tiếng Việt
      ("file tạm an toàn xóa" / "cần xem tay vì là project")
- [x] Chỉ thêm dữ liệu, không đổi chữ ký hàm UI đang gọi
  - **Acceptance:** UI đọc `reason_text` hiển thị tooltip; tests pass.
  - **thay doi:** `make_selection_item()` them field, cac public signature giu nguyen.

### REQ#5 (tùy chọn) — Gom rule "file rác" tập trung
- [x] Tài liệu hóa tiêu chí nào → `recommended_decision = delete_candidate`
- [x] Đảm bảo không mở rộng quá tay (an toàn dữ liệu là số 1)
  - **Acceptance:** có doc + test cho ranh giới safe_delete vs review_required.
  - **thay doi:** rule runtime o `tools/core/cleanup_rules.py`, tai lieu o `docs/FILE_CLEANUP_RULES.md`.

### REQ#6 — Kế hoạch "Dọn 1 chạm" cho Bước 3 (hỗ trợ UI)
- [x] Thêm hàm public `build_one_click_cleanup_plan(...) -> dict` trả về
      `{files, count, total_size, summary_text, safety_contract}` từ scan gần nhất
- [x] Chỉ gồm file `safe_delete` — **dùng `tools/core/cleanup_rules.py` làm nguồn chân lý**, không tự định nghĩa lại
- [x] Read-only; KHÔNG đổi chữ ký hàm UI đang gọi (chỉ thêm hàm mới); ghi tên hàm + schema vào mailbox
- [x] (Tùy chọn) thêm `severity` + `summary_text` tiếng Việt để UI hiện thẳng lên banner
  - **Acceptance:** hàm trả dict read-only chỉ chứa file `safe_delete`; có contract test; Full System Tester pass.
  - **Ghi chú:** Claude KHÔNG bị chặn — Bước 3 vẫn làm được từ `selection_session` sẵn có; REQ#6 để gom logic về 1 nguồn (backend) cho sạch kiến trúc, xong thì UI đổi sang gọi hàm này.
  - **thay doi:** public `tools.core.one_click_cleanup.build_one_click_cleanup_plan(...)`, schema `one_click_cleanup_plan_v1`; Full System Tester 40/40.

---

## Nguyên tắc chung (cả hai)
- Mỗi agent branch riêng (`claude/...`, `codex/...`) → PR vào `main` → user merge.
- Cập nhật `.agents/AGENT_MAILBOX.md` khi đổi API public hoặc bàn giao.
- Mọi xóa/move/backup tiếp tục qua Selection Decision Report + token + Recycle Bin. KHÔNG bypass confirmation.
- Trước khi push: Tool Tester + Full System Tester phải pass.
