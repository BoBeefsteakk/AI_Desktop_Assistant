from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

import send2trash

from tools.core.safety_utils import format_size, ask_yes_no, save_report, is_system_path

def file_hash(path: Path, chunk_size: int = 1024 * 1024) -> str | None:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None

def list_files(folder: str, recursive: bool) -> list[Path]:
    root = Path(folder)
    if not root.exists():
        print("Folder khong ton tai.")
        return []

    if is_system_path(root):
        print("Khong nen quet truc tiep folder he thong.")
        return []

    iterator = root.rglob("*") if recursive else root.iterdir()
    files = []
    for path in iterator:
        try:
            if path.is_file():
                files.append(path)
        except (PermissionError, OSError):
            continue
    return files

def find_duplicates(folder: str, recursive: bool = True) -> list[dict]:
    files = list_files(folder, recursive)
    print(f"Dang quet {len(files)} file...")

    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in files:
        try:
            by_size[path.stat().st_size].append(path)
        except (PermissionError, OSError):
            continue

    duplicates = []
    for size, same_size_files in by_size.items():
        if len(same_size_files) < 2:
            continue

        by_hash: dict[str, list[Path]] = defaultdict(list)
        for path in same_size_files:
            h = file_hash(path)
            if h:
                by_hash[h].append(path)

        for same_hash_files in by_hash.values():
            if len(same_hash_files) < 2:
                continue

            # Giu file dau tien lam ban goc, chi dua cac ban con lai vao danh sach xoa.
            original = same_hash_files[0]
            for duplicate in same_hash_files[1:]:
                duplicates.append({
                    "original": str(original),
                    "duplicate": str(duplicate),
                    "size": size,
                })

    return duplicates

def show_duplicates(duplicates: list[dict]) -> None:
    total = sum(item["size"] for item in duplicates)
    print("\n========== FILE TRUNG LAP ==========")
    for i, item in enumerate(duplicates, start=1):
        print(f"\n[{i}] {format_size(item['size'])}")
        print(f"Goc   : {item['original']}")
        print(f"Trung : {item['duplicate']}")
    print("\n" + "=" * 80)
    print(f"Tong file trung: {len(duplicates)}")
    print(f"Dung luong co the tiet kiem: {format_size(total)}")

def delete_duplicates(duplicates: list[dict]) -> None:
    if not duplicates:
        print("Khong co file trung de xoa.")
        return

    report_path = save_report("duplicates_before_delete", duplicates)
    print(f"Da luu report backup: {report_path}")
    print("File trung se duoc dua vao Recycle Bin, khong xoa vinh vien.")

    if not ask_yes_no("Ban muon dua CAC FILE TRUNG vao Recycle Bin?", default=False):
        print("Da huy xoa.")
        return

    deleted = 0
    for item in duplicates:
        try:
            send2trash.send2trash(item["duplicate"])
            deleted += 1
        except Exception as e:
            print(f"Loi: {item['duplicate']} | {e}")

    print(f"Da dua {deleted}/{len(duplicates)} file trung vao Recycle Bin.")

def run_duplicate_finder() -> None:
    folder = input("Nhap folder can quet: ").strip().strip('"') or "D:\\"
    recursive = ask_yes_no("Quet ca folder con?", default=True)

    duplicates = find_duplicates(folder, recursive)
    show_duplicates(duplicates)
    delete_duplicates(duplicates)

if __name__ == "__main__":
    run_duplicate_finder()
