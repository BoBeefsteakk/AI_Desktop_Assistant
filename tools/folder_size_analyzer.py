from __future__ import annotations

import os
from pathlib import Path

from .safety_utils import format_size, save_report
from .assistant_logger import log_action


SKIP_DIR_NAMES = {
    "$recycle.bin",
    "system volume information",
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    ".git",
    "__pycache__",
    "node_modules",
}

SKIP_FILE_NAMES = {
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
}


def should_skip(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return any(skip_name in parts for skip_name in SKIP_DIR_NAMES)


def get_folder_size(folder: Path) -> int:
    total_size = 0

    for root, dirs, files in os.walk(folder):
        root_path = Path(root)

        dirs[:] = [
            dirname for dirname in dirs
            if not should_skip(root_path / dirname)
        ]

        for file_name in files:
            if file_name.lower() in SKIP_FILE_NAMES:
                continue

            file_path = root_path / file_name

            try:
                total_size += file_path.stat().st_size
            except (PermissionError, OSError):
                continue

    return total_size


def analyze_top_folders(root_folder: str, limit: int = 15) -> list[dict]:
    root = Path(root_folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return []

    results = []

    print(f"Dang quet folder: {root}")

    for item in root.iterdir():
        try:
            if not item.is_dir():
                continue

            if should_skip(item):
                continue

            print(f"Dang tinh: {item}")

            size = get_folder_size(item)

            results.append({
                "path": str(item),
                "size": size
            })

        except (PermissionError, OSError):
            continue

    results.sort(key=lambda item: item["size"], reverse=True)

    return results[:limit]


def show_top_folders(results: list[dict]) -> None:
    print("\n========== TOP FOLDER NANG NHAT ==========")

    if not results:
        print("Khong co ket qua.")
        return

    for index, item in enumerate(results, start=1):
        print(f"{index:>2}. {format_size(item['size']):>10} | {item['path']}")


def run_folder_size_analyzer() -> None:
    folder = input("Nhap o dia/folder can scan, VD D:\\: ").strip().strip('"') or "D:\\"

    raw_limit = input("Hien thi top bao nhieu folder? [15]: ").strip()
    limit = int(raw_limit) if raw_limit.isdigit() else 15

    results = analyze_top_folders(folder, limit)
    show_top_folders(results)

    report = save_report("folder_size_analyzer", results)
    print(f"\nDa luu report: {report}")

    log_action(
        "folder_size_analyzer",
        "analyze_top_folders",
        "success",
        {
            "folder": folder,
            "count": len(results),
            "report": str(report)
        }
    )


if __name__ == "__main__":
    run_folder_size_analyzer()
