# Trạng thái dự án AI Desktop Assistant

> Nhật ký lịch sử đầy đủ (Phase 1–7) đã chuyển sang [`STATUS_ARCHIVE.md`](STATUS_ARCHIVE.md).
> Roadmap đang chạy: [`PHASE8_ROADMAP.md`](PHASE8_ROADMAP.md). File này chỉ giữ **trạng thái
> hiện hành** — cập nhật tại chỗ, không append log dài.

**Cập nhật:** 2026-06-27

---

## Mục tiêu (đích cuối)

AI tự chạy full tool → tư vấn sức khỏe ổ cứng / file rác / file nặng bằng tiếng Việt →
user chỉ chọn **xóa hay giữ**. **User không cần mở app, không chạy tool nào.**
Ưu tiên số 1: **an toàn dữ liệu** trước hiệu năng.

---

## Trạng thái hiện hành

**Phase 7 — HOÀN TẤT** (merged vào `main`, PR #6/#9/#11 + backend Codex #4/#7/#10):

- **Bước 1** — Dọn nhanh inline: bảng file rác `delete_candidate`, nút [Xóa]/[Giữ] → safe-delete qua token + Recycle Bin.
- **Bước 2** — Giải thích + Hỏi AI: panel sức khỏe hiện `explanation` + `disk_full_reason`; ô "Hỏi AI" gọi `answer_user_question`.
- **Bước 3** — Dọn 1 chạm: banner "AI đề nghị dọn N file rác (~X GB)" + nút [Đồng ý dọn]; cột "Lý do an toàn xóa".
- **Bước 5** — Theo dõi định kỳ: banner + nút "Kiểm tra vấn đề mới" gọi `run_periodic_scan` (read-only), báo vấn đề mới so baseline.
- **Nền tảng** — auto-scan khi mở app, storage mode storage-aware, UI ttkbootstrap (theme cosmo), phân biệt DEMO/MÁY THẬT.

**Backend public API (Codex, Claude đã nối vào UI):**
- `tools.storage.system_advisor` — `explanation` + `disk_full_reason`
- `tools.search.natural_command.answer_user_question(...)` — schema `natural_command_answer_v1`
- `tools.core.cleanup_rules` — `build_cleanup_rule_registry()` / `get_cleanup_recommendation()` (chỉ `safe_delete` → `delete_candidate`)
- `tools.core.one_click_cleanup.build_one_click_cleanup_plan(...)` — schema `one_click_cleanup_plan_v1`
- `tools.automation.boot_runner.run_periodic_scan(...)` — schema `periodic_scan_notification_v1`
- `tools.core.bot_controller.make_selection_item()` — thêm `reason_text`

**Đang làm tiếp:** Phase 8 (trợ lý nền: quét ngầm + Windows toast + one-click từ toast) — xem `PHASE8_ROADMAP.md`.
Codex hết token tuần này → Claude solo; backend Claude viết tạm sẽ để Codex review sau.

---

## Mốc verify gần nhất

| Suite | Kết quả |
|---|---|
| Tool Tester | 48/48 |
| Behavior Tester | 18/18 |
| Scenario Tester | 6/6 |
| Full System Tester | 40/40 (canonical `D:\tool`) |
| Feed Readiness | 9 pass, 0 warn, 0 fail |

---

## Safety invariants (KHÔNG vi phạm)

- Mọi **xóa** qua `safe_executor.safe_delete()` → Safe Delete Adapter (risk `safe_delete`) → Recycle Bin.
- Mọi **move** có manifest restore, qua `safe_move()` + File Operation Adapter.
- **Backup Adapter** copy-only vào `D:\tool\backups/`, không xóa source.
- Token mạnh (`DELETE_SELECTION_V1`/`MOVE_SELECTION_V1`/`BACKUP_SELECTION_V1`) phải do user nhập trước khi apply.
- Advisor / Recommendation Center / quét nền: **read-only**, không tự chạy cleanup.
- KHÔNG thêm confirmation bypass vào bất kỳ adapter nào.
- Máy chỉ có Python 3.12 — không dùng `py -3.11`.

---

## Ghi chú cho AI

Trước khi sửa tool cleanup: đọc `docs/TOOL_MASTER_PLAN.md` + file này. Mọi thao tác xóa
phải đi qua `safe_executor.py`. Chi tiết lịch sử từng tool ở `STATUS_ARCHIVE.md`.
