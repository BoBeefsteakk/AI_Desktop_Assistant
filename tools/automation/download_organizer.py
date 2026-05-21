from __future__ import annotations

import os
import shutil
from pathlib import Path
from datetime import datetime

from tools.core.safety_utils import safe_move, format_size, save_manifest, restore_from_manifest
from tools.core.assistant_logger import log_action

DOWNLOADS_DIR = Path.home() / "Downloads"

FILE_CATEGORIES = {
    "Anh": {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"
    },
    "Video": {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"
    },
    "Audio": {
        ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"
    },
    "Tai_lieu": {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"
    },
    "Nen": {
        ".zip", ".rar", ".7z", ".tar", ".gz"
    },
    "Code": {
        ".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".java", ".json", ".xml", ".sql"
    },
    "Cai_dat": {
        ".exe", ".msi", ".apk", ".iso"
    }
}

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
    temporary_suffixes = {
        ".crdownload", ".part", ".tmp", ".download", ".idownload"
    }
    return path.suffix.lower() in temporary_suffixes

def organize_downloads_once(downloads_dir: str | Path = DOWNLOADS_DIR) -> None:
    """
    Flow:
    - Khi co file trong Downloads, tao folder theo ngay: YYYY-MM-DD
    - Trong folder ngay, tao folder con theo loai file: Anh/Video/Audio/...
    - Move file vao dung folder con
    - Luu manifest de restore neu can
    """
    downloads_dir = Path(downloads_dir)

    if not downloads_dir.exists():
        print("Khong tim thay folder Downloads.")
        return

    today_folder = downloads_dir / get_today_folder_name()
    records = []

    for item in downloads_dir.iterdir():
        try:
            if not item.is_file():
                continue

            if is_downloading_file(item):
                continue

            category = get_category(item)
            target_folder = today_folder / category
            target_path = target_folder / item.name

            size = item.stat().st_size
            record = safe_move(item, target_path)
            record["category"] = category
            record["size"] = size

            records.append(record)
            print(
                f"Moved [{category}] {format_size(size)}: "
                f"{record['old_path']} -> {record['new_path']}"
            )

        except Exception as e:
            print(f"Loi: {item} | {e}")

    if records:
        manifest = save_manifest("download_organizer_backup", records)
        print(f"\nDa sap xep {len(records)} file Downloads.")
        print(f"Backup manifest: {manifest}")

        log_action(
            "download_organizer",
            "organize_downloads_once",
            "success",
            {"count": len(records), "manifest": str(manifest)}
        )
    else:
        print("Khong co file moi can sap xep.")
        log_action("download_organizer", "organize_downloads_once", "empty")

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
            restore_from_manifest(manifest)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_download_organizer()
