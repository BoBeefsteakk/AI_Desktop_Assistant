from __future__ import annotations

import os
from pathlib import Path
import send2trash

from tools.core.safety_utils import format_size, ask_yes_no, save_report, is_system_path
from config.settings import DEFAULT_SCAN_FOLDER

from tools.core.report_manager import create_report

DEFAULT_JUNK_EXTENSIONS = (".tmp", ".log", ".bak", ".old", ".temp")

SKIP_FILES = {
    "dumpstack.log.tmp",
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
}

def scan_junk_files(
    folder: str,
    extensions: tuple[str, ...] = DEFAULT_JUNK_EXTENSIONS,
    recursive: bool = False,
    include_empty: bool = False,
) -> list[dict]:
    root = Path(folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return []

    if is_system_path(root):
        print("Khong nen quet truc tiep folder he thong.")
        return []

    results = []
    iterator = root.rglob("*") if recursive else root.iterdir()

    for path in iterator:
        try:
            if path.name.lower() in SKIP_FILES:
                continue

            suffix_match = path.name.lower().endswith(extensions) if extensions else False
            empty_match = include_empty and path.stat().st_size == 0

            if suffix_match or empty_match:
                results.append({
                    "path": str(path),
                    "size": path.stat().st_size,
                    "reason": "empty" if empty_match and not suffix_match else "extension",
                })
        except (PermissionError, OSError):
            continue

    return results

def show_junk_files(files: list[dict]) -> None:
    total = sum(item["size"] for item in files)
    print("\n========== FILE RAC TIM THAY ==========")
    for i, item in enumerate(files, start=1):
        print(f"{i:>3}. {format_size(item['size']):>10} | {item['path']}")
    print("-" * 80)
    print(f"Tong file: {len(files)}")
    print(f"Tong dung luong: {format_size(total)}")

def delete_junk_files(files: list[dict]) -> None:
    if not files:
        print("Khong co file de xoa.")
        return

    report_path = save_report("junk_files_before_delete", files)
    print(f"Da luu report backup: {report_path}")
    print("File se duoc dua vao Recycle Bin, khong xoa vinh vien.")

    if not ask_yes_no("Ban muon dua tat ca file nay vao Recycle Bin?", default=False):
        print("Da huy xoa.")
        return

    deleted = 0
    for item in files:
        try:
            send2trash.send2trash(item["path"])
            deleted += 1
        except Exception as e:
            print(f"Loi: {item['path']} | {e}")

    print(f"Da dua {deleted}/{len(files)} file vao Recycle Bin.")

    total_size = sum(item["size"] for item in files)

    report = create_report(
        tool_name="junk_file_cleaner",
        status="success",
        input_data={
            "selected_count": len(files),
        },
        results={
            "deleted_count": deleted,
            "failed_count": len(files) - deleted,
            "total_size": total_size,
            "files": files,
        },
        recommendations=[
            "Files were moved to Recycle Bin, not permanently deleted.",
            "Review Recycle Bin before emptying it.",
        ],
    )

    print(f"Report: {report}")

def run_junk_cleaner() -> None:
    folder = input("Nhap folder can quet: ").strip().strip('"') or DEFAULT_SCAN_FOLDER
    recursive = ask_yes_no("Quet ca folder con?", default=False)
    include_empty = ask_yes_no("Bao gom file rong 0KB?", default=False)

    files = scan_junk_files(folder, recursive=recursive, include_empty=include_empty)
    show_junk_files(files)
    delete_junk_files(files)

if __name__ == "__main__":
    run_junk_cleaner()
