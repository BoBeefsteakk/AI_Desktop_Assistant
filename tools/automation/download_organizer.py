from __future__ import annotations

from pathlib import Path
from datetime import datetime

from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report
from tools.core.risk_classifier import classify_file_risk, PROTECTED
from tools.core.safety_utils import (
    ask_yes_no,
    format_size,
    is_system_path,
    restore_from_manifest,
    safe_move,
    save_manifest,
)
from config.settings import (
    DEFAULT_DOWNLOAD_FOLDER,
    DOWNLOAD_ORGANIZER_FILE_CATEGORIES,
    DOWNLOAD_ORGANIZER_TEMP_EXTENSIONS,
)

DOWNLOADS_DIR = Path(DEFAULT_DOWNLOAD_FOLDER)
FILE_CATEGORIES = DOWNLOAD_ORGANIZER_FILE_CATEGORIES
TEMPORARY_DOWNLOAD_EXTENSIONS = DOWNLOAD_ORGANIZER_TEMP_EXTENSIONS

def get_today_folder_name() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def get_category(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    for category, extensions in FILE_CATEGORIES.items():
        if suffix in extensions:
            return category

    return "Khac"

def is_downloading_file(path: Path) -> bool:
    """
    Bo qua file dang tai do: Chrome/Edge/Firefox/IDM hay tao cac duoi tam.
    """
    return path.suffix.lower() in TEMPORARY_DOWNLOAD_EXTENSIONS

def scan_download_files(downloads_dir: str | Path = DOWNLOADS_DIR) -> list[dict]:
    downloads_dir = Path(downloads_dir)

    if not downloads_dir.exists():
        print("Khong tim thay folder Downloads.")
        return []

    if is_system_path(downloads_dir):
        print("Khong nen sap xep truc tiep folder he thong.")
        return []

    root_risk = classify_file_risk(downloads_dir)
    if root_risk["risk"] == PROTECTED:
        print("Folder Downloads dang nam trong vung protected. Da huy.")
        return []

    today_folder = downloads_dir / get_today_folder_name()
    results = []

    for item in downloads_dir.iterdir():
        try:
            if not item.is_file():
                continue

            if is_downloading_file(item):
                continue

            category = get_category(item)
            target_folder = today_folder / category
            target_path = target_folder / item.name

            risk_data = classify_file_risk(item)
            results.append({
                "path": str(item),
                "target_path": str(target_path),
                "category": category,
                "size": item.stat().st_size,
                "extension": item.suffix.lower() or "[no_ext]",
                "risk": risk_data["risk"],
                "risk_reason": risk_data["reason"],
            })

        except (PermissionError, OSError):
            continue

    return results


def show_download_files(files: list[dict]) -> None:
    print("\n========== DOWNLOAD FILES ==========")

    if not files:
        print("Khong co file moi can sap xep.")
        return

    total_size = sum(item["size"] for item in files)

    for index, item in enumerate(files, start=1):
        print(
            f"{index:>3}. {format_size(item['size']):>10} | "
            f"{item['category']:<10} | {item['risk']:<18} | {item['path']}"
        )

    print("-" * 90)
    print(f"Tong file: {len(files)}")
    print(f"Tong dung luong: {format_size(total_size)}")


def choose_download_files_to_move(files: list[dict]) -> list[dict]:
    if not files:
        return []

    movable_files = [
        item for item in files
        if item["risk"] != PROTECTED
    ]

    if not movable_files:
        print("Tat ca file deu bi chan boi safety layer.")
        return []

    while True:
        print("\nChon file Downloads muon sap xep:")
        print("- Nhap 0 de huy")
        print("- Nhap all de chon tat ca file khong PROTECTED")
        print("- Nhap so thu tu, cach nhau boi dau phay. VD: 1,3,5")

        choice = input("Lua chon: ").strip().lower()

        if choice == "0" or not choice:
            return []

        if choice == "all":
            if not ask_yes_no("Ban chac chan muon sap xep tat ca file khong PROTECTED?", default=False):
                continue

            return movable_files

        selected = []

        for raw_index in choice.split(","):
            raw_index = raw_index.strip()

            if not raw_index.isdigit():
                continue

            index = int(raw_index) - 1

            if 0 <= index < len(files):
                item = files[index]

                if item["risk"] == PROTECTED:
                    print(f"Bo qua file protected: {item['path']}")
                    continue

                selected.append(item)

        if selected:
            return selected

        print("Lua chon khong hop le. Vui long nhap lai.")


def move_download_files(
    selected_files: list[dict],
    downloads_dir: Path,
    today_folder: Path,
    preview_report: str,
) -> dict:
    records = []
    blocked = 0
    errors = 0

    for item in selected_files:
        source = Path(item["path"])
        risk_data = classify_file_risk(source)

        if risk_data["risk"] == PROTECTED:
            blocked += 1
            records.append({
                **item,
                "status": "blocked",
                "risk": risk_data["risk"],
                "risk_reason": risk_data["reason"],
            })
            continue

        try:
            target_path = Path(item["target_path"])
            record = safe_move(source, target_path)
            record.update({
                "category": item["category"],
                "size": item["size"],
                "extension": item["extension"],
                "risk": risk_data["risk"],
                "risk_reason": risk_data["reason"],
                "status": "moved",
            })
            records.append(record)
            print(
                f"Moved [{item['category']}] {format_size(item['size'])}: "
                f"{record['old_path']} -> {record['new_path']}"
            )

        except Exception as error:
            errors += 1
            records.append({
                **item,
                "status": "error",
                "error": str(error),
            })
            print(f"Loi: {item['path']} | {error}")

    moved_records = [
        item for item in records
        if item["status"] == "moved"
    ]

    manifest = None
    if moved_records:
        manifest = save_manifest("download_organizer_backup", moved_records)

    report = create_report(
        tool_name="download_organizer",
        status="success",
        input_data={
            "downloads_dir": str(downloads_dir),
            "target_day_folder": str(today_folder),
            "preview_report": preview_report,
        },
        results={
            "moved_count": len(moved_records),
            "blocked_count": blocked,
            "error_count": errors,
            "records": records,
            "manifest": str(manifest) if manifest else None,
        },
        recommendations=[
            "Use restore option if files were moved incorrectly.",
            "Review backup manifest before deleting it.",
        ],
    )

    log_action(
        "download_organizer",
        "organize_downloads_once",
        "success",
        {
            "moved": len(moved_records),
            "blocked": blocked,
            "errors": errors,
            "manifest": str(manifest) if manifest else None,
            "report": str(report),
        },
    )

    print(f"\nDa sap xep {len(moved_records)} file Downloads.")
    if manifest:
        print(f"Backup manifest: {manifest}")
    print(f"Report: {report}")

    return {
        "moved_count": len(moved_records),
        "blocked_count": blocked,
        "error_count": errors,
        "records": records,
        "manifest": str(manifest) if manifest else None,
        "report": str(report),
    }


def organize_downloads_once(downloads_dir: str | Path = DOWNLOADS_DIR) -> None:
    """
    Flow:
    - Scan file o root Downloads
    - Preview va chon file
    - Tao folder theo ngay: YYYY-MM-DD
    - Trong folder ngay, tao folder con theo loai file: Anh/Video/Audio/...
    - Move file vao dung folder con
    - Luu manifest de restore neu can
    """
    downloads_dir = Path(downloads_dir)
    today_folder = downloads_dir / get_today_folder_name()

    files = scan_download_files(downloads_dir)
    show_download_files(files)

    selected_files = choose_download_files_to_move(files)

    if not selected_files:
        print("Da huy sap xep Downloads.")
        log_action(
            "download_organizer",
            "organize_downloads_once",
            "cancelled",
            {"downloads_dir": str(downloads_dir), "found_count": len(files)},
        )
        return

    preview_report = create_report(
        tool_name="download_organizer_preview",
        status="preview",
        input_data={
            "downloads_dir": str(downloads_dir),
            "target_day_folder": str(today_folder),
        },
        results={
            "found_count": len(files),
            "selected_count": len(selected_files),
            "files": selected_files,
        },
        recommendations=[
            "Review target paths before confirming the move.",
            "Protected files are not selectable.",
        ],
    )

    print(f"Preview report: {preview_report}")

    if not ask_yes_no("Xac nhan sap xep cac file da chon?", default=False):
        print("Da huy sap xep Downloads.")
        log_action(
            "download_organizer",
            "organize_downloads_once",
            "cancelled",
            {
                "downloads_dir": str(downloads_dir),
                "selected_count": len(selected_files),
                "preview_report": str(preview_report),
            },
        )
        return

    move_download_files(
        selected_files=selected_files,
        downloads_dir=downloads_dir,
        today_folder=today_folder,
        preview_report=str(preview_report),
    )


def restore_downloads_from_manifest(manifest_path: str) -> None:
    result = restore_from_manifest(manifest_path)

    status = "success" if result["status"] == "success" else "error"
    report = create_report(
        tool_name="download_organizer_restore",
        status=status,
        input_data={
            "manifest": manifest_path,
        },
        results=result,
        recommendations=[
            "Review restored paths for rename-on-collision suffixes.",
        ],
    )

    log_action(
        "download_organizer",
        "restore_from_manifest",
        status,
        {
            "manifest": manifest_path,
            "restored": result["restored_count"],
            "skipped": result["skipped_count"],
            "report": str(report),
        },
    )

    print(f"Restore report: {report}")

def run_download_organizer() -> None:
    while True:
        print("""
========== DOWNLOAD ORGANIZER ==========
1. Sap xep Downloads ngay bay gio
2. Restore tu backup manifest
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            folder = input(f"Folder Downloads [{DOWNLOADS_DIR}]: ").strip().strip('"')
            organize_downloads_once(folder or DOWNLOADS_DIR)

        elif choice == "2":
            manifest = input("Nhap duong dan backup manifest .json: ").strip().strip('"')
            restore_downloads_from_manifest(manifest)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_download_organizer()
