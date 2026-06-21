# AI Assistant Handoff - 2026-06-15

## **thay doi** Muc dich file nay

**thay doi** File nay la ban take note/handoff de tiep tuc du an `AI Desktop Assistant` neu sau nay quay lai. Doc file nay truoc, sau do doc tiep:

* `D:\tool\docs\TOOL_MASTER_PLAN.md`
* `D:\tool\docs\PROJECT_STATUS.md`
* `D:\tool\docs\ROADMAP.md`
* `D:\tool\docs\UI_ACCEPTANCE.md`

**thay doi** Workspace chinh hien tai: `D:\tool`.

**thay doi** Moc verify gan nhat:

* Tool Tester: 45/45 pass tai `D:\tool\reports\tool_tester_20260614_164416.json`
* Full System Tester: 37/37 pass tai `D:\tool\reports\full_system_tester_20260614_164456.json`
* Feed Readiness: 9 pass, 0 warn, 0 fail tai `D:\tool\reports\feed_readiness_20260614_164517.json`

## **thay doi** Dinh huong cuoi cung

**thay doi** Ket qua cuoi cung khong phai la 45 menu roi rac. Ket qua can dat la mot AI Assistant local co the:

1. Tu scan may/folder/disk theo ngu canh.
2. Tu phan loai van de: file rac, file lon, file trung, cache, file can backup, file nen move, file can review, file khong duoc dung.
3. Tu giai thich ly do de xuat.
4. Cho user quyet dinh bang 3 kieu don gian: `OK`, `lua chon`, `huy`.
5. Chi thuc thi sau dry-run, confirm, token/guardrail va report ro rang.
6. Tao manifest/undo/report de co the kiem tra va khoi phuc neu co loi.

**thay doi** Nguyen tac thiet ke: AI tu dong phan tich va lap ke hoach, user chi dua ra quyet dinh cuoi. User khong phai nho tung tool.

## **thay doi** Nhung gi da lam duoc

**thay doi** Da don va thong nhat root du an:

* Root chinh la `D:\tool`.
* Ban cu `AI_Desktop_Assistant` da duoc tach/backup de tranh nham root.
* Main CLI, docs, reports, backups, config deu tap trung quanh `D:\tool`.

**thay doi** Da co nen safety:

* `risk_classifier`
* `safe_executor`
* protected folders
* safe delete qua Recycle Bin
* dry-run truoc khi apply
* manifest/undo cho move
* report/audit cho hanh dong quan trong

**thay doi** Da harden nhieu tool:

* duplicate finder
* temp cleaner
* junk cleaner
* browser cache cleaner
* recycle bin cleaner
* media organizer
* empty folder finder
* download organizer
* download watcher
* startup launcher
* disk checker
* process monitor

**thay doi** Da co he thong report/log/undo:

* `report_manager`
* report schema v2
* report index
* audit center
* undo manager
* full system tester
* scenario tester bang file gia

**thay doi** Da tich hop app ngoai theo huong read-only/tro ly:

* Everything CLI cho search nhanh
* WizTree Adapter cho storage scan nhanh qua CSV
* smartctl/CrystalDiskInfo context cho disk health
* Sysinternals cho diagnostics
* ExifTool/FFmpeg/FFprobe cho media metadata
* rclone trong external app registry

**thay doi** Da co intelligence layer:

* Capability Registry cho toan bo tool
* Natural Command v3 route lenh qua registry
* System Advisor v2 read-only snapshot
* Recommendation Center
* Action Policy Manager
* Policy Enforcement Gate
* Candidate Review
* Dry-run Action Planner
* Pre-feed Bundle
* Feed Assistant Readiness

**thay doi** Da co bot/autonomy layer:

* Auto Scan Session
* Issue Classifier
* AI Bot Controller v2
* Selection UI / Decision Report
* Backup Adapter copy-only cho `needs_backup`
* File Operation Adapter cho `move_later`
* Safe Delete Adapter cho `delete_candidate`
* Bot Backup Flow
* Bot Move-later Flow
* Bot Safe-delete Flow

**thay doi** Da co UI nghiem thu:

* `python -m tools.ui.bot_panel`
* tab `Tro ly`
* issue cards
* one-click AI plan
* full demo bang file gia
* backup/move/safe-delete flow
* activity/result panel
* run history panel
* Advanced tab cho technical/debug

**thay doi** Da co Obsidian export:

* vault tai `D:\tool\obsidian_vault`
* graph nodes cho tools/apps/reports/policies/decisions
* dung de nhin ban do he thong, khong dung de cleanup truc tiep

## **thay doi** Luong hien tai cua he thong

**thay doi** Luong dung nen giu:

```text
User chon folder / yeu cau
-> Auto Scan Session
-> Issue Classifier
-> Bot Controller
-> Action Policy / Recommendation / Candidate Review
-> User quyet dinh OK / lua chon / huy
-> Dry-run
-> Preview/report
-> Confirm/token
-> Adapter thuc thi rieng
-> Report + audit + manifest/undo neu can
```

**thay doi** Khong nen cho UI goi xoa/move truc tiep. UI chi nen goi bot flow/adapters da co guardrail.

## **thay doi** Nhung quy tac khong duoc pha

**thay doi** Khong xoa file that neu chua co:

* risk classification
* selection ro rang
* dry-run
* confirm/token
* report
* recycle bin hoac manifest/undo tuy loai hanh dong

**thay doi** Safe Delete chi cho `risk=safe_delete`; `review_required` va `protected` phai bi chan.

**thay doi** `Riot Games`, game data, project files, archive/installer user con can, Premiere/project media: mac dinh la review/keep/manual, khong auto delete.

**thay doi** Neu gap case that kho phan loai, tao file gia trong Scenario Tester truoc. Khong thu truc tiep tren file user.

**thay doi** External app chi tang toc scan/search/metadata, khong duoc tu no xoa/move file.

**thay doi** Full System Tester phai pass truoc khi feed assistant hoac refactor lon.

## **thay doi** Trang thai hien tai

**thay doi** Backend safety da kha vung.

**thay doi** Bot flow da co khung dung:

* scan
* classify
* recommend
* decision report
* backup
* move_later
* safe_delete
* report/undo

**thay doi** UI dang o muc nghiem thu/build tool app ban dau, chua phai AI Assistant cuoi cung.

**thay doi** Phan con yeu nhat hien tai la trai nghiem san pham:

* UI con giong tool/debug hon la assistant that
* ngon ngu/label van can don gian hon
* can them man hinh chat/command assistant
* can dashboard tong the may ro hon
* can latest reports preview giong report viewer that

## **thay doi** Roadmap tu bay gio den AI Assistant hoan chinh

### **thay doi** Moc 1 - UI thanh assistant-first that su

**thay doi** Muc tieu: user mo app len la biet can lam gi, khong can hieu backend.

Viec can lam:

1. Tao Home/Dashboard ro rang: `Tinh trang may`, `Van de can xem`, `De xuat AI`, `Hanh dong an toan`.
2. Giam tab/label ky thuat o man chinh.
3. Chuyen `Ket qua gan nhat` thanh report summary dep hon, khong phai raw log.
4. Chuyen `Lich su gan day` thanh danh sach report co status/tag/count.
5. Them detail drawer/modal: bam vao issue/report thi mo chi tiet.
6. Chay nghiem thu UI bang demo sandbox va screenshot.

Dieu kien xong:

* User co the chay demo, scan folder, xem de xuat, preview va apply ma khong can vao Advanced.
* Full System Tester + UI acceptance pass.

### **thay doi** Moc 2 - Real System Dashboard

**thay doi** Muc tieu: bot tu check tong quan may.

Viec can lam:

1. Tao `System Overview` trong UI: disk usage, RAM/process, disk health, external app health, latest warnings.
2. Noi System Advisor v2 vao UI bang card de doc.
3. Them nut `Quet tong quan may`.
4. Tach ro read-only scan voi action co the thay doi file.
5. Luu snapshot theo thoi gian de so sanh thay doi.

Dieu kien xong:

* User bam mot nut va co bao cao tong quan may de doc.
* Khong co action mutating trong dashboard scan.

### **thay doi** Moc 3 - Decision Inbox

**thay doi** Muc tieu: moi van de tro thanh item co trang thai.

Viec can lam:

1. Tao queue UI: `Can backup`, `Can move`, `Co the don`, `Can xem`, `Khong dung toi`.
2. Moi item co ly do, risk, source report, suggested action.
3. User co the bulk choose: keep/manual/backup/move/delete.
4. Ghi nho policy user sau moi quyet dinh.
5. Cho undo/restore ro rang sau move.

Dieu kien xong:

* User co the xu ly van de theo inbox thay vi bang thap ky thuat.

### **thay doi** Moc 4 - Conversational Assistant

**thay doi** Muc tieu: user noi/chats tu nhien, AI route dung tool.

Viec can lam:

1. Them chat/command box vao UI.
2. Noi Natural Command v3 + Capability Registry vao chat.
3. Chat phai tra loi bang y dinh + risk truoc khi mo action.
4. Cho lenh mau:
   * `kiem tra may`
   * `o D day vi sao`
   * `tim file lon`
   * `don file rac an toan`
   * `xem file nen backup`
5. Chat khong tu xoa/move; no tao plan va yeu cau user confirm.

Dieu kien xong:

* User co the dung ngon ngu tu nhien thay vi nho menu.

### **thay doi** Moc 5 - Report Viewer va Explainability

**thay doi** Muc tieu: user tin duoc de xuat cua AI.

Viec can lam:

1. Xay report viewer trong app.
2. Moi hanh dong co "vi sao AI de xuat".
3. Moi file co risk explanation.
4. Show before/after impact: dung luong, so file, vi tri backup/move.
5. Lien ket report -> decision -> adapter -> manifest.

Dieu kien xong:

* User co the kiem tra lai moi quyet dinh sau khi chay.

### **thay doi** Moc 6 - Background Auto Scan

**thay doi** Muc tieu: assistant tu theo doi may ma khong lam phien.

**thay doi** Da co buoc dau (Startup/Boot v1):
- `tools/core/startup_scan.py`: boot scan full o (mode `auto` = WizTree neu co, fallback Python) -> issue classifier -> man tu van 3 lua chon `khong xoa / chon file / xoa tat ca an toan`, route qua Safe Delete flow (dry-run + token + Recycle Bin).
- `tools/automation/startup_registration.py`: bat/tat tu chay khi khoi dong qua launcher `.cmd` trong `shell:startup` (go duoc bang cach xoa launcher). Menu 47.
- `tools/automation/boot_runner.py`: entry chay luc login (`py -m tools.automation.boot_runner`), scan read-only roi mo Bot Panel UI; doc toggle `startup` trong `config/user_settings.json`.
- Menu 46 = Startup Scan. Tool Tester 47/47, Full System Tester 37/37.

Viec can lam tiep:

1. Scheduler/monitor read-only theo lich dinh ky (khong chi luc boot).
2. Scan nhe theo lich.
3. Chi tao notification/recommendation, khong cleanup.
4. Detect path/app drift.
5. Luu trend theo ngay/tuan.
6. Man hinh Decision Inbox do hoa rieng voi dung 3 nut (hien dang dung CLI advisory + mo Bot Panel UI).

Dieu kien xong:

* App co the tu check va dua goi y, nhung khong tu thay doi file.

### **thay doi** Moc 7 - Feed Assistant dung cach

**thay doi** Muc tieu: feed context de AI nho flow, khong phai train model luc dau.

Can feed:

* `TOOL_MASTER_PLAN.md`
* `PROJECT_STATUS.md`
* `ROADMAP.md`
* `UI_ACCEPTANCE.md`
* latest Full System Tester report
* latest Feed Readiness report
* Capability Registry snapshot
* Action policies
* External apps status
* This handoff file

Khong nen feed:

* raw logs qua nhieu
* file ca nhan cua user
* report co path nhay cam neu chua sanitize

Dieu kien xong:

* Assistant moi co the doc context va tiep tuc dung flow an toan.

## **thay doi** Lenh can nho

Chay UI:

```powershell
cd /d D:\tool
python -m tools.ui.bot_panel
```

Chay Tool Tester:

```powershell
cd /d D:\tool
python -m tools.core.tool_tester
```

Chay Full System Tester:

```powershell
cd /d D:\tool
python -m tools.core.full_system_tester
```

Chay Feed Readiness:

```powershell
cd /d D:\tool
python - <<'PY'
from tools.core.feed_readiness import export_feed_readiness_report
r = export_feed_readiness_report()
print(r["report"])
print(r["status"])
print(r["readiness"]["summary"])
PY
```

## **thay doi** Loi nhan cho nguoi tiep tuc

**thay doi** Dung coi day la mot cleanup script. Day la mot assistant dang duoc xay co muc tieu lon hon: hieu may cua user, phan loai rui ro, giai thich de xuat, va chi hanh dong khi user quyet dinh.

**thay doi** Neu phai chon giua nhanh va an toan, chon an toan.

**thay doi** Neu UI gay kho hieu, don gian hoa luong user truoc khi them tinh nang moi.

**thay doi** Neu gap file that nhay cam, tao scenario fake truoc.

**thay doi** Neu quay lai sau mot thoi gian dai, viec dau tien la chay Full System Tester va doc latest Feed Readiness.
