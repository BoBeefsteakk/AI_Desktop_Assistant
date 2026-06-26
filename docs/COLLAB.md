# COLLAB.md — Quy trình hai agent làm song song, không xung đột

Tài liệu này để **Claude Code** và **Codex** cùng làm trên repo `D:\tool` mà không
giẫm chân nhau. Cả hai agent PHẢI đọc file này trước mỗi phiên.

---

## Phần 1 — Nguyên tắc vàng

1. **Không bao giờ hai agent sửa cùng một file trong cùng một lúc.**
2. **Mỗi agent làm trên branch riêng**, rồi tạo PR cho user review/merge.
3. **Pull trước khi làm, push ngay sau khi xong** một đơn vị công việc.
4. **Việc nhạy cảm an toàn (xóa/move/adapter/token) chỉ một agent chủ trì**; agent
   kia review chéo, không tự sửa.
5. **Mọi thay đổi phải pass Tool Tester + Full System Tester** trước khi push.

---

## Phần 2 — Phân vùng sở hữu (Ownership map)

Để tránh đụng file, chia trách nhiệm theo thư mục. Quy ước mặc định:

| Vùng | Đường dẫn | Chủ trì |
|---|---|---|
| Kiến trúc tổng thể, luồng chuẩn | `docs/TOOL_MASTER_PLAN.md`, `docs/ARCHITECTURE.md`, thiết kế cross-module | **Claude** |
| Giao diện desktop | `tools/ui/` | **Claude** |
| Backend logic, tool, adapter | `tools/core/`, `tools/storage/`, `tools/system/`, `tools/search/`, `tools/automation/` | **Codex** |
| Config | `config/` | Ai sửa thì báo trước ở Worklog |
| Docs | `docs/`, `CLAUDE.md`, `AGENTS.md` | Cả hai (mỗi agent chỉ sửa mục của mình) |
| Tests | `tools/core/*tester*.py` | Agent nào thêm feature thì thêm test cho feature đó |

> Phân vùng này có thể đổi — nhưng phải **thống nhất qua user** và ghi lại ở Phần 4.
> Tuyệt đối không tự ý sửa file ngoài vùng của mình mà không khai báo.

### File nhạy cảm an toàn — Codex viết, Claude (architecture) DUYỆT trước khi merge:
- `tools/core/safe_executor.py`, `tools/core/risk_classifier.py`
- `tools/core/safe_delete_adapter.py`, `tools/core/backup_adapter.py`,
  `tools/core/file_operation_adapter.py`, `tools/core/execution_adapter.py`

> Lý do: đây là rào an toàn (token, dry-run, Recycle Bin, manifest). Codex cứ
> implement, nhưng PR đụng các file này PHẢI được Claude review để chắc chắn không
> có bypass confirmation / xóa-move trực tiếp. Đây là vai "architecture" của Claude,
> không phải tranh chấp quyền sửa code.

### Ranh giới UI ↔ Backend (để không đụng nhau):
- Claude (UI) chỉ **gọi** hàm backend đã có (vd `export_*_report`, `build_*_result`),
  không tự viết logic xóa/move trong `tools/ui/`.
- Codex (backend) khi đổi chữ ký hàm public mà UI đang gọi → **báo ở Worklog** trước,
  để Claude cập nhật UI tương ứng, tránh vỡ giao diện.

---

## Phần 3 — Quy trình git (chống xung đột)

### Cách an toàn nhất: branch riêng + PR
```
# Đầu phiên
git checkout main
git pull origin main
git checkout -b <agent>/<tinh-nang>      # vd: codex/ui-inline-delete, claude/intent-engine

# Làm việc, commit nhiều lần nhỏ
git add <file cua minh>
git commit -m "..."

# Cuối phiên
git push origin <branch>
# Tạo PR, để user review + merge
```

Quy ước tên branch: `claude/...` và `codex/...` để nhìn là biết của ai.

### Nếu buộc phải dùng chung một branch
- Luôn `git pull --rebase` TRƯỚC khi bắt đầu sửa.
- Làm xong **commit + push ngay**, đừng giữ thay đổi lâu trong máy.
- Báo ở Worklog (Phần 4) là "đang sửa file X" để agent kia tránh.

### Khi có conflict
- Agent gây conflict tự resolve, **giữ nguyên ý của cả hai bên**, không xóa code
  của agent kia. Nếu không chắc → hỏi user, đừng đoán.

---

## Phần 4 — Worklog (bảng tin chung)

Mỗi agent ghi 1 dòng trước khi bắt đầu và sau khi xong. Mới nhất ở trên cùng.
Format: `[YYYY-MM-DD HH:MM] <agent> | <branch> | <trạng thái> | <file/vùng đang đụng>`

**thay doi (2026-06-27):** Kênh nhắn chung dài hơn Worklog là
`.agents/AGENT_MAILBOX.md`. Dùng file này để lại câu hỏi, handoff ngắn, hoặc
cảnh báo đổi API giữa Codex và Claude. Worklog vẫn dùng cho trạng thái bắt
đầu/kết thúc phiên.

<!-- WORKLOG: thêm dòng mới ngay dưới đây -->

- [2026-06-27 02:10] codex | codex/backend-collab-bridge | DONE | tạo `.agents/AGENT_MAILBOX.md`, cập nhật COLLAB/PROJECT_STATUS, không sửa backend logic
- [2026-06-27 02:00] codex | codex/backend-collab-bridge | START | đọc AGENTS/COLLAB/CLAUDE, tạo mailbox chung, không sửa backend logic
- [2026-06-25] claude | add-claude-md-and-marketing-skills | DONE | tạo AGENTS.md + docs/COLLAB.md, advisory dashboard UI
- (Codex ghi dòng đầu tiên của mình ở đây)

---

## Phần 5 — Checklist cuối phiên (cả hai agent)

- [ ] Code chạy được, không lỗi import.
- [ ] Tool Tester pass, Full System Tester pass.
- [ ] Cập nhật `docs/PROJECT_STATUS.md` (đã làm gì).
- [ ] Cập nhật Worklog (Phần 4) trạng thái DONE.
- [ ] Commit message rõ ràng; chỉ push/PR khi user đồng ý.
- [ ] Không vi phạm safety invariant nào trong `AGENTS.md` / `CLAUDE.md`.
