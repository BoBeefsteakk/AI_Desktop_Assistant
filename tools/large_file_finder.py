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


def parse_size_to_mb(raw_size: str, default_mb: int = 500) -> int:
    raw_size = raw_size.strip().lower().replace(" ", "")

    if not raw_size:
        return default_mb

    try:
        if raw_size.endswith("gb"):
            return int(float(raw_size.replace("gb", "")) * 1024)

        if raw_size.endswith("mb"):
            return int(float(raw_size.replace("mb", "")))

        if raw_size.endswith("kb"):
            return max(1, int(float(raw_size.replace("kb", "")) / 1024))

        return int(float(raw_size))

    except ValueError:
        print("Gia tri khong hop le, dung mac dinh.")
        return default_mb


def find_large_files(
    root_folder: str,
    min_size_mb: int = 500,
    limit: int = 50
) -> list[dict]:

    root = Path(root_folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return []

    results = []
    min_size_bytes = min_size_mb * 1024 * 1024

    print(f"Dang scan file lon hon {min_size_mb} MB...")

    for current_root, dirs, files in os.walk(root):
        current_path = Path(current_root)

        dirs[:] = [
            dirname for dirname in dirs
            if not should_skip(current_path / dirname)
        ]

        for file_name in files:
            if file_name.lower() in SKIP_FILE_NAMES:
                continue

            file_path = current_path / file_name

            try:
                if should_skip(file_path):
                    continue

                size = file_path.stat().st_size

                if size >= min_size_bytes:
                    results.append({
                        "path": str(file_path),
                        "size": size,
                        "extension": file_path.suffix.lower() or "[no_ext]"
                    })

            except (PermissionError, OSError):
                continue

    results.sort(key=lambda item: item["size"], reverse=True)

    return results[:limit]


def show_large_files(results: list[dict]) -> None:
    print("\n========== LARGE FILES ==========")

    if not results:
        print("Khong tim thay file lon.")
        return

    for index, item in enumerate(results, start=1):
        print(
            f"{index:>2}. "
            f"{format_size(item['size']):>10} | "
            f"{item['extension']:<8} | "
            f"{item['path']}"
        )


def run_large_file_finder() -> None:
    folder = input(
        "Nhap o dia/folder can scan [D:\\]: "
    ).strip().strip('"') or "D:\\"

    raw_size = input(
        "Tim file lon hon bao nhieu? VD: 500mb | 2gb [500mb]: "
    ).strip()

    min_size_mb = parse_size_to_mb(raw_size, default_mb=500)

    raw_limit = input(
        "Hien thi top bao nhieu file? [50]: "
    ).strip()

    limit = int(raw_limit) if raw_limit.isdigit() else 50

    results = find_large_files(
        folder,
        min_size_mb=min_size_mb,
        limit=limit
    )

    show_large_files(results)

    report = save_report("large_file_finder", results)

    print(f"\nDa luu report: {report}")

    log_action(
        "large_file_finder",
        "find_large_files",
        "success",
        {
            "folder": folder,
            "min_size_mb": min_size_mb,
            "count": len(results),
            "report": str(report)
        }
    )


if __name__ == "__main__":
    run_large_file_finder()
