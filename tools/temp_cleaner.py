from __future__ import annotations

import os
import shutil
from pathlib import Path

from .safety_utils import format_size, ask_yes_no, save_report
from .assistant_logger import log_action

def get_temp_paths() -> list[Path]:
    paths = []

    user_temp = os.environ.get("TEMP")
    local_temp = os.environ.get("TMP")

    for p in [user_temp, local_temp, r"C:\Windows\Temp"]:
        if p:
            path = Path(p)
            if path.exists() and path not in paths:
                paths.append(path)

    return paths

def get_path_size(path: Path) -> int:
    total = 0

    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0

    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except (PermissionError, OSError):
            continue

    return total

def scan_temp_files(max_age_days: int = 1) -> list[dict]:
    """
    Quet file/folder temp co the xoa.
    Mac dinh chi xoa item cu hon 1 ngay de tranh dung vao file app dang su dung.
    """
    import time

    now = time.time()
    min_age_seconds = max_age_days * 24 * 60 * 60
    results = []

    for temp_path in get_temp_paths():
        try:
            for item in temp_path.iterdir():
                try:
                    age = now - item.stat().st_mtime

                    if age < min_age_seconds:
                        continue

                    size = get_path_size(item)

                    results.append({
                        "path": str(item),
                        "size": size,
                        "type": "folder" if item.is_dir() else "file",
                        "age_days": round(age / 86400, 2)
                    })

                except (PermissionError, OSError):
                    continue

        except (PermissionError, OSError):
            continue

    return results

def show_temp_items(items: list[dict]) -> None:
    print("\n========== TEMP ITEMS ==========")

    if not items:
        print("Khong tim thay file temp phu hop.")
        return

    total = sum(x["size"] for x in items)

    for i, item in enumerate(items, start=1):
        print(
            f"{i:>3}. {format_size(item['size']):>10} | "
            f"{item['type']:<6} | {item['age_days']:>6} ngay | {item['path']}"
        )

    print("-" * 90)
    print(f"Tong item: {len(items)}")
    print(f"Tong dung luong co the don: {format_size(total)}")

def clean_temp_items(items: list[dict]) -> None:
    if not items:
        return

    report = save_report("temp_items_before_clean", items)
    print(f"Da luu report: {report}")
    print("Luu y: Tool chi xoa temp cu hon moc ngay da chon.")

    if not ask_yes_no("Ban muon xoa cac temp item nay?", default=False):
        print("Da huy.")
        log_action("temp_cleaner", "clean_temp", "cancelled", {"count": len(items)})
        return

    deleted = 0
    failed = 0

    for item in items:
        path = Path(item["path"])

        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=False)
            elif path.exists():
                path.unlink()

            deleted += 1

        except Exception:
            failed += 1

    print(f"Da xoa {deleted} item. Loi/bi khoa: {failed} item.")
    log_action(
        "temp_cleaner",
        "clean_temp",
        "success",
        {"deleted": deleted, "failed": failed}
    )

def run_temp_cleaner() -> None:
    raw_days = input("Chi don temp cu hon bao nhieu ngay? [1]: ").strip()
    max_age_days = int(raw_days) if raw_days.isdigit() else 1

    items = scan_temp_files(max_age_days=max_age_days)
    show_temp_items(items)
    clean_temp_items(items)

if __name__ == "__main__":
    run_temp_cleaner()
