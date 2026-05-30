from __future__ import annotations

from pathlib import Path

from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report
from tools.core.risk_classifier import classify_file_risk, PROTECTED
from tools.core.safe_executor import safe_delete
from tools.core.safety_utils import ask_yes_no, is_system_path, save_report

SKIP_NAMES = {
    "$recycle.bin",
    "system volume information",
    ".git",
    "__pycache__",
    "node_modules",
}

def is_skipped(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return any(part in SKIP_NAMES for part in parts)

def find_empty_folders(root_folder: str) -> list[dict]:
    root = Path(root_folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return []

    if is_system_path(root):
        print("Khong nen quet truc tiep folder he thong.")
        return []

    empty_folders = []

    # Duyet bottom-up de bat duoc folder cha bi rong sau khi folder con rong.
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            if not path.is_dir():
                continue

            if is_skipped(path):
                continue

            if not any(path.iterdir()):
                risk_data = classify_file_risk(path)

                empty_folders.append({
                    "path": str(path),
                    "risk": risk_data["risk"],
                    "risk_reason": risk_data["reason"],
                })

        except (PermissionError, OSError):
            continue

    return empty_folders

def show_empty_folders(folders: list[dict]) -> None:
    print("\n========== EMPTY FOLDERS ==========")

    if not folders:
        print("Khong tim thay folder rong.")
        return

    for i, item in enumerate(folders, start=1):
        print(f"{i:>3}. {item['risk']:<18} | {item['path']}")

    print("-" * 80)
    print(f"Tong folder rong: {len(folders)}")

def choose_empty_folders_to_delete(folders: list[dict]) -> list[dict]:
    if not folders:
        return []

    deletable_folders = [
        item for item in folders
        if item["risk"] != PROTECTED
    ]

    if not deletable_folders:
        print("Tat ca folder rong deu bi chan boi safety layer.")
        return []

    while True:
        print("\nChon folder rong muon dua vao Recycle Bin:")
        print("- Nhap 0 de huy")
        print("- Nhap all de chon tat ca folder khong PROTECTED")
        print("- Nhap so thu tu, cach nhau boi dau phay. VD: 1,3,5")

        choice = input("Lua chon: ").strip().lower()

        if choice == "0" or not choice:
            return []

        if choice == "all":
            if not ask_yes_no("Ban chac chan muon chon tat ca folder khong PROTECTED?", default=False):
                continue

            return deletable_folders

        selected = []

        for raw_index in choice.split(","):
            raw_index = raw_index.strip()

            if not raw_index.isdigit():
                continue

            index = int(raw_index) - 1

            if 0 <= index < len(folders):
                item = folders[index]

                if item["risk"] == PROTECTED:
                    print(f"Bo qua folder protected: {item['path']}")
                    continue

                selected.append(item)

        if selected:
            return selected

        print("Lua chon khong hop le. Vui long nhap lai.")

def delete_empty_folders(folders: list[dict]) -> None:
    if not folders:
        return

    selected_folders = choose_empty_folders_to_delete(folders)

    if not selected_folders:
        print("Da huy.")
        log_action(
            "empty_folder_finder",
            "delete_empty_folders",
            "cancelled",
            {"count": len(folders)},
        )
        return

    preview_report = save_report("empty_folders_before_delete", selected_folders)
    print(f"Da luu preview report: {preview_report}")
    print("Folder rong se duoc dua vao Recycle Bin neu co the.")

    if not ask_yes_no("Ban muon dua cac folder da chon vao Recycle Bin?", default=False):
        print("Da huy.")
        log_action(
            "empty_folder_finder",
            "delete_empty_folders",
            "cancelled",
            {
                "selected_count": len(selected_folders),
                "preview_report": str(preview_report),
            },
        )
        return

    results = []

    for item in selected_folders:
        path = Path(item["path"])

        try:
            if not path.exists():
                results.append({
                    "path": str(path),
                    "risk": "unknown",
                    "reason": "Folder khong ton tai.",
                    "status": "missing",
                })
                continue

            if not path.is_dir():
                results.append({
                    "path": str(path),
                    "risk": "unknown",
                    "reason": "Path khong phai folder.",
                    "status": "skipped",
                })
                continue

            if any(path.iterdir()):
                results.append({
                    "path": str(path),
                    "risk": item["risk"],
                    "reason": "Folder khong con rong.",
                    "status": "skipped",
                })
                continue

            results.append(safe_delete(path))

        except Exception as error:
            results.append({
                "path": str(path),
                "risk": item.get("risk", "unknown"),
                "reason": item.get("risk_reason", ""),
                "status": "error",
                "error": str(error),
            })

    deleted = sum(1 for item in results if item["status"] == "deleted")
    blocked = sum(1 for item in results if item["status"] == "blocked")
    missing = sum(1 for item in results if item["status"] == "missing")
    skipped = sum(1 for item in results if item["status"] == "skipped")
    errors = sum(1 for item in results if item["status"] == "error")

    print(
        f"Deleted: {deleted} | Blocked: {blocked} | "
        f"Missing: {missing} | Skipped: {skipped} | Errors: {errors}"
    )

    report = create_report(
        tool_name="empty_folder_finder",
        status="success",
        input_data={
            "selected_count": len(selected_folders),
            "preview_report": str(preview_report),
        },
        results={
            "deleted_count": deleted,
            "blocked_count": blocked,
            "missing_count": missing,
            "skipped_count": skipped,
            "error_count": errors,
            "folders": selected_folders,
            "execution_results": results,
        },
        recommendations=[
            "Folders were moved to Recycle Bin, not permanently deleted.",
            "Review Recycle Bin before emptying it.",
        ],
    )

    log_action(
        "empty_folder_finder",
        "delete_empty_folders",
        "success",
        {
            "deleted": deleted,
            "blocked": blocked,
            "missing": missing,
            "skipped": skipped,
            "errors": errors,
            "report": str(report),
        }
    )

    print(f"Report: {report}")

def run_empty_folder_finder() -> None:
    folder = input("Nhap folder can quet: ").strip().strip('"') or "D:\\"

    folders = find_empty_folders(folder)
    show_empty_folders(folders)
    delete_empty_folders(folders)

if __name__ == "__main__":
    run_empty_folder_finder()
