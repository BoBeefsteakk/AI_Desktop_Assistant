# Bot Panel UI Acceptance

## **thay doi** Muc tieu

**thay doi** UI nay dung de nghiem thu luong bot theo kieu assistant-first: user thay trang thai, issue cards, one-click AI plan preview/apply; bang ky thuat nam trong tab `Advanced`.

**thay doi** UI khong thay the toan bo 45 tool. No la bot panel de gom nhung viec quan trong nhat vao mot man hinh de ban khong phai nho tung menu CLI.

## **thay doi** Cach chay

```powershell
cd /d D:\tool
python -m tools.ui.bot_panel
```

**thay doi** Hoac vao `python main.py`, chon muc `44. Bot Panel UI`.

## **thay doi** Luong demo tu dong

1. **thay doi** O tab `Assistant`, bam `Chay full demo`.
2. **thay doi** UI tu tao sandbox file gia trong `D:\_ai_desktop_assistant_ui_demo\run_<timestamp>\...`.
3. **thay doi** UI tu chay scan/classify, chon de xuat AI, backup dry-run/apply, move dry-run/apply va safe cleanup dry-run/apply.
4. **thay doi** UI tu mo tab `Advanced` va in step log: click nao da duoc mo phong, report nao duoc tao, backup/move/delete count bao nhieu.
5. **thay doi** Dieu kien an toan: full demo chi duoc thao tac tren sandbox file gia, khong dung folder that cua user.

## **thay doi** Luong nghiem thu an toan

1. **thay doi** O tab `Assistant`, bam `Chay thu an toan`/`Try demo`. UI se tao file gia trong `D:\_ai_desktop_assistant_ui_demo\run_<timestamp>\...` va scan luon.
2. **thay doi** Doc dong status: UI phai noi ro co bao nhieu issue, bao nhieu item review duoc, bao nhieu protected.
3. **thay doi** Doc cac issue cards: Backup, Move, Safe cleanup, Needs review, Do not touch. Moi card phai noi ro so item va y nghia.
4. **thay doi** Bam `Dung de xuat AI` de chap nhan de xuat mac dinh cua bot cho cac item co the xu ly.
5. **thay doi** Bam `Xem ke hoach AI`; UI phai tao preview tong cho backup/move/safe cleanup va khong thay doi file.
6. **thay doi** Doc preview trong tab `Advanced`: backup/move/safe cleanup count phai ro rang.
7. **thay doi** Neu hop ly, tick `Toi da xem ke hoach`, roi bam `Ap dung ke hoach`.
8. **thay doi** Neu khong hop ly, bam `Huy lua chon`.

## **thay doi** Dieu kien pass nghiem thu

**thay doi** UI mo duoc bang lenh `python -m tools.ui.bot_panel`.

**thay doi** Tab mac dinh la `Assistant`, khong phai bang ky thuat.

**thay doi** Tab `Assistant` hien issue cards thay cho bang `Recommended work` ky thuat.

**thay doi** Moi issue card co count, y nghia, nut xem nhom va neu co the xu ly thi co nut chon theo de xuat.

**thay doi** `Chay full demo` tu chay du luong tren sandbox file gia va in log tung buoc trong `Advanced`.

**thay doi** `Xem ke hoach AI` gom backup/move/safe cleanup vao mot dry-run tong va khong thay doi file.

**thay doi** `Ap dung ke hoach` chi chay neu da tick `Toi da xem ke hoach`, da co preview khop voi lua chon hien tai va user xac nhan popup.

**thay doi** Sau scan/preview/apply, khung `Ket qua gan nhat` trong tab `Assistant` phai hien summary de doc; user khong bat buoc vao `Advanced`.

**thay doi** Khung `Ket qua gan nhat` phai du rong/cao de doc nhieu dong ket qua; khong duoc bi bop thanh o nho 1-2 dong khi co `Lich su gan day`.

**thay doi** Khung `Ket qua gan nhat` phai la panel full-width ben duoi man `Assistant`, khong nam trong cot phu ben phai.

**thay doi** Khung `Ket qua gan nhat` phai co chieu cao toi thieu lon hon dang log mong: ban hien tai dat toi thieu 520px va co scrollbar.

**thay doi** Vung `Ket qua gan nhat` + `Lich su gan day` phai duoc neo o day man `Assistant`, khong duoc bi `De xuat cua AI` day khoi vung nhin thay.

**thay doi** Khung `Lich su gan day` chi la phan phu de mo report moi nhat, khong duoc chen mat khung ket qua chinh.

**thay doi** Khung `Lich su gan day` phai du doc de xem nhieu report gan nhat: ban hien tai nam trong vung doc cao ben duoi, canh phai `Ket qua gan nhat`, dat 10 dong va co scrollbar.

**thay doi** `Demo sandbox` tao folder test rieng, khong dung file that cua user.

**thay doi** `Auto scan + classify` hien item trong bang, co recommended decision va group ro rang.

**thay doi** Item locked/do-not-touch khong cho ep thanh delete/move.

**thay doi** `Save decision report` tao report ma khong xoa/move file.

**thay doi** `Safe delete dry-run` hien so file requested/deletable/blocked/deleted, va `deleted` phai bang 0 o dry-run.

**thay doi** `Move dry-run` hien so file requested/movable/blocked/moved, va `moved` phai bang 0 o dry-run.

**thay doi** `Backup dry-run` hien so file requested/backupable/blocked/backed_up, va `backed_up` phai bang 0 o dry-run.

**thay doi** `Apply backup` chi chay khi da dry-run, da tick checkbox va xac nhan popup; backend adapter van token-gated bang `BACKUP_SELECTION_V1`, source file phai con nguyen.

**thay doi** `Apply move` chi chay khi co destination folder hop le, da dry-run, da tick checkbox va xac nhan popup; backend adapter van token-gated bang `MOVE_SELECTION_V1`.

**thay doi** `Undo last move` chi restore manifest move moi nhat trong UI session va khong dung safe-delete/Recycling Bin.

**thay doi** `Apply safe delete` chi chay khi da tick checkbox xac nhan va xac nhan popup; backend adapter van token-gated bang `DELETE_SELECTION_V1`.

**thay doi** Safe Delete Adapter chi dua file `risk=safe_delete` vao Recycle Bin; `review_required` va `protected` bi chan.

## **thay doi** Gioi han cua UI v1

**thay doi** UI v2 nay da co Assistant Dashboard + issue cards + activity log + one-click AI plan + full demo + Advanced mode. Backup, safe-delete, `move_later` destination picker/apply qua adapter va Undo last move van duoc giu.

**thay doi** `needs_backup` da co Backup Adapter rieng. Day la flow copy-only: source duoc giu nguyen, manifest chi de audit/report, khong can undo restore.

**thay doi** Deep scan bang `python` tren o lon co the cham; dung `light` cho quick check hoac `wiztree` khi can storage detail nhanh.
