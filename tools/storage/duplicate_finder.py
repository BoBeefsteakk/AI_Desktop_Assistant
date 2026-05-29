from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from tools.core.safety_utils import format_size, ask_yes_no, save_report, is_system_path
from tools.core.risk_classifier import classify_file_risk, SAFE_DELETE, PROTECTED
from tools.core.safe_executor import safe_delete


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

            original = same_hash_files[0]

            for duplicate in same_hash_files[1:]:
                risk_data = classify_file_risk(duplicate)

                if risk_data["risk"] == PROTECTED:
                    continue

                duplicates.append({
                    "original": str(original),
                    "duplicate": str(duplicate),
                    "size": duplicate.stat().st_size,
                    "risk": risk_data["risk"],
                    "risk_reason": risk_data["reason"],
                })

    return duplicates


def show_duplicates(duplicates: list[dict]) -> None:
    print("\n========== FILE TRUNG LAP ==========")

    if not duplicates:
        print("Khong tim thay file trung lap.")
        return

    total = sum(item["size"] for item in duplicates)

    for i, item in enumerate(duplicates, start=1):
        print(f"\n[{i}] {format_size(item['size'])}")
        print(f"Goc     : {item['original']}")
        print(f"Ban sao : {item['duplicate']}")
        print(f"Risk    : {item['risk']}")
        print(f"Reason  : {item['risk_reason']}")
        print("-" * 80)

    print("\n" + "=" * 80)
    print(f"Tong file trung: {len(duplicates)}")
    print(f"Dung luong co the tiet kiem: {format_size(total)}")


def choose_duplicates_to_delete(duplicates: list[dict]) -> list[dict]:
    if not duplicates:
        return []

    while True:
        print("\nChon file trung muon dua vao Recycle Bin:")
        print("- Nhap 0 de huy")
        print("- Nhap all de chon tat ca file SAFE_DELETE")
        print("- Nhap so thu tu, cach nhau boi dau phay. VD: 1,3,5")

        choice = input("Lua chon: ").strip().lower()

        if choice == "0" or not choice:
            return []

        if choice == "all":
            risky_files = [
                item for item in duplicates
                if item["risk"] != SAFE_DELETE
            ]

            if risky_files:
                print("Co file can review thu cong. Khong cho phep chon ALL.")
                print("Vui long chon tung file hoac nhap 0 de huy.")
                continue

            if not ask_yes_no("Ban chac chan muon xoa tat ca SAFE_DELETE?", default=False):
                continue

            return duplicates

        selected = []

        for raw_index in choice.split(","):
            raw_index = raw_index.strip()

            if not raw_index.isdigit():
                continue

            index = int(raw_index) - 1

            if 0 <= index < len(duplicates):
                selected.append(duplicates[index])

        if selected:
            return selected

        print("Lua chon khong hop le. Vui long nhap lai.")


def delete_duplicates(duplicates: list[dict]) -> None:
    if not duplicates:
        print("Khong co file trung de xoa.")
        return

    selected = choose_duplicates_to_delete(duplicates)

    if not selected:
        print("Da huy xoa.")
        return

    report_path = save_report("duplicates_before_delete", selected)
    print(f"Da luu report backup: {report_path}")
    print("File trung se duoc dua vao Recycle Bin, khong xoa vinh vien.")

    if not ask_yes_no("Xac nhan dua cac file da chon vao Recycle Bin?", default=False):
        print("Da huy xoa.")
        return

    results = []

    for item in selected:
        result = safe_delete(item["duplicate"])
        results.append(result)

    deleted = sum(1 for item in results if item["status"] == "deleted")
    blocked = sum(1 for item in results if item["status"] == "blocked")
    missing = sum(1 for item in results if item["status"] == "missing")
    errors = sum(1 for item in results if item["status"] == "error")

    print(f"Da dua {deleted}/{len(selected)} file trung vao Recycle Bin.")
    print(f"Blocked: {blocked} | Missing: {missing} | Errors: {errors}")


def run_duplicate_finder() -> None:
    folder = input("Nhap folder can quet, khong nhap truc tiep ca o dia: ").strip().strip('"')

    if not folder:
        print("Da huy. Vui long nhap folder cu the.")
        return

    recursive = ask_yes_no("Quet ca folder con?", default=True)

    duplicates = find_duplicates(folder, recursive)
    show_duplicates(duplicates)
    delete_duplicates(duplicates)


if __name__ == "__main__":
    run_duplicate_finder()