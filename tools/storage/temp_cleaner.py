from __future__ import annotations

from pathlib import Path

from tools.core.safety_utils import format_size, ask_yes_no, save_report
from tools.core.assistant_logger import log_action
from tools.core.risk_classifier import classify_file_risk, PROTECTED, SAFE_DELETE
from tools.core.safe_executor import safe_delete
from config.settings import SAFE_SYSTEM_FOLDERS


SKIP_DIR_NAMES = {name.lower() for name in SAFE_SYSTEM_FOLDERS}


def is_safe_temp_path(path: Path) -> bool:
    lower_path = str(path).lower()

    for skip_name in SKIP_DIR_NAMES:
        if skip_name in lower_path and "temp" not in lower_path:
            return False

    return True


def scan_temp_files(folder: str, max_age_days: int = 1) -> list[dict]:
    import time

    root = Path(folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return []

    if not is_safe_temp_path(root):
        print("Folder nay khong an toan de quet.")
        return []

    now = time.time()
    results = []

    for item in root.rglob("*"):
        try:
            if not item.is_file():
                continue

            age_seconds = now - item.stat().st_mtime
            age_days = age_seconds / 86400

            # Chi lay file trong vong N ngay gan day
            if age_days > max_age_days:
                continue

            risk_data = classify_file_risk(item)

            if risk_data["risk"] == PROTECTED:
                continue

            results.append({
                "path": str(item),
                "size": item.stat().st_size,
                "type": "file",
                "age_days": round(age_days, 2),
                "risk": risk_data["risk"],
                "risk_reason": risk_data["reason"],
                "risk_category": risk_data.get("category"),
                "risk_rule": risk_data.get("matched_rule"),
            })

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
        risk_category = item.get("risk_category") or item["risk"]
        print(
            f"{i:>3}. {format_size(item['size']):>10} | "
            f"{item['risk']:<15} | {risk_category:<24} | "
            f"{item['type']:<6} | {item['age_days']:>6} ngay | {item['path']}"
        )

    print("-" * 90)
    print(f"Tong item: {len(items)}")
    print(f"Tong dung luong co the don: {format_size(total)}")


def choose_temp_items_to_clean(items: list[dict]) -> list[dict]:
    if not items:
        return []

    while True:
        print("\nChon temp item muon don:")
        print("- Nhap 0 de huy")
        print("- Nhap all de chon tat ca SAFE_DELETE")
        print("- Nhap so thu tu, cach nhau boi dau phay. VD: 1,3,5")

        choice = input("Lua chon: ").strip().lower()

        if choice == "0" or not choice:
            return []

        if choice == "all":
            risky_items = [
                item for item in items
                if item["risk"] != SAFE_DELETE
            ]

            if risky_items:
                print("Co item can review thu cong. Khong cho phep chon ALL.")
                print("Vui long chon tung item hoac nhap 0 de huy.")
                continue

            if not ask_yes_no("Ban chac chan muon don tat ca SAFE_DELETE?", default=False):
                continue

            return items

        selected = []

        for raw_index in choice.split(","):
            raw_index = raw_index.strip()

            if not raw_index.isdigit():
                continue

            index = int(raw_index) - 1

            if 0 <= index < len(items):
                selected.append(items[index])

        if selected:
            return selected

        print("Lua chon khong hop le. Vui long nhap lai.")


def clean_temp_items(items: list[dict]) -> None:
    if not items:
        return

    selected_items = choose_temp_items_to_clean(items)

    if not selected_items:
        print("Da huy.")
        log_action("temp_cleaner", "clean_temp", "cancelled", {"count": len(items)})
        return

    report = save_report("temp_items_before_clean", selected_items)
    print(f"Da luu report: {report}")
    print("Luu y: item se duoc dua vao Recycle Bin neu co the.")

    if not ask_yes_no("Xac nhan don cac item da chon?", default=False):
        print("Da huy.")
        return

    results = []

    for item in selected_items:
        result = safe_delete(item["path"])
        results.append(result)

    deleted = sum(1 for item in results if item["status"] == "deleted")
    blocked = sum(1 for item in results if item["status"] == "blocked")
    missing = sum(1 for item in results if item["status"] == "missing")
    errors = sum(1 for item in results if item["status"] == "error")

    print(f"Deleted: {deleted} | Blocked: {blocked} | Missing: {missing} | Errors: {errors}")

    log_action(
        "temp_cleaner",
        "clean_temp",
        "success",
        {
            "deleted": deleted,
            "blocked": blocked,
            "missing": missing,
            "errors": errors,
        }
    )


def run_temp_cleaner() -> None:
    raw_days = input("Hien file temp trong vong bao nhieu ngay gan day? [1]: ").strip()
    max_age_days = int(raw_days) if raw_days.isdigit() else 1

    folder = input("Nhap folder can quet: ").strip().strip('"') or r"D:\temp_cleaner_test"

    items = scan_temp_files(
        folder=folder,
        max_age_days=max_age_days
    )

    show_temp_items(items)
    clean_temp_items(items)


if __name__ == "__main__":
    run_temp_cleaner()
