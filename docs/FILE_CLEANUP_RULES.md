# File Cleanup Rules

**thay doi (2026-06-27):** Day la tai lieu nguon cho REQ#5. Rule runtime nam o
`tools/core/cleanup_rules.py`; Risk Classifier van la nguon phan loai duy nhat.

## Ranh gioi quyet dinh

| Risk tu Risk Classifier | De xuat mac dinh | Co the thanh `delete_candidate`? |
|---|---|---|
| `safe_delete` | `delete_candidate` | Co, nhung van can selection + dry-run + token |
| `review_required` | `manual_review` | Khong |
| `protected` | `keep` | Khong, item bi khoa |

**thay doi:** Khong co extension nao tu no du dieu kien xoa. Duoi `.tmp`, `.log`
hoac file giong cache nam ngoai safe zone van la `review_required`.

## Khi nao Risk Classifier tra `safe_delete`

- Duong dan cache trinh duyet da biet, co ca browser hint va cache directory.
- Duong dan cache ro rang nhu `GPUCache`, `Code Cache`, `DawnCache`.
- File co safe-junk extension nam trong safe zone da cau hinh, vi du Temp hoac
  Downloads.

## Khi nao phai review hoac khoa

- Extension nghi la rac nhung nam ngoai safe zone: `review_required`.
- Folder app/game, dev/build artifact, archive, installer, project: xem tay,
  backup hoac move tuy ngu canh; khong de xuat xoa mac dinh.
- Root project/tool, folder he thong, metadata va file he thong: `protected`.
- Khong du thong tin: `review_required`.

## Chuoi an toan sau de xuat

**thay doi:** `delete_candidate` chi la y dinh, khong phai lenh xoa. File chi co
the vao Recycle Bin sau khi user chon dung item, xem dry-run, nhap final token,
Safe Delete Adapter phan loai lai va goi `safe_executor.safe_delete()`.

## API

- `build_cleanup_rule_registry() -> dict`
- `get_cleanup_recommendation(risk_result) -> dict`
- `validate_cleanup_rule_registry() -> dict`

Tat ca API tren read-only va khong thuc hien file operation.

## One-click cleanup plan

**thay doi (2026-06-27):** `tools/core/one_click_cleanup.py` doc selection
session va reclassify tung path qua Risk Classifier + cleanup rule registry.
Chi file dang ton tai, co de xuat `delete_candidate` va van duoc xep
`safe_delete` moi vao plan. Plan chi tra du lieu cho UI; khong execute xoa.
