from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime

from .safety_utils import format_size, save_report, ask_yes_no

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
INDEX_FILE = DATA_DIR / "file_index.json"

SKIP_DIR_NAMES = {
    "$Recycle.Bin", "System Volume Information", "Windows",
    "Program Files", "Program Files (x86)", "ProgramData",
    "AppData", "node_modules", ".git", "__pycache__"
}

def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)

def build_file_index(root_folder: str, index_path: str | Path = INDEX_FILE) -> None:
    root = Path(root_folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    count = 0

    print(f"Dang index: {root}")

    for current_root, dirs, files in os.walk(root):
        current_path = Path(current_root)

        # Bo qua folder nguy hiem / qua nang
        dirs[:] = [d for d in dirs if not should_skip(current_path / d)]

        for file_name in files:
            path = current_path / file_name

            try:
                stat = path.stat()
                records.append({
                    "name": path.name,
                    "suffix": path.suffix.lower(),
                    "path": str(path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
                })
                count += 1

                if count % 1000 == 0:
                    print(f"Da index {count} file...")

            except (PermissionError, OSError):
                continue

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"\nDa tao index {len(records)} file.")
    print(f"Luu tai: {index_path}")

def search_file_index(keyword: str, index_path: str | Path = INDEX_FILE, limit: int = 30) -> list[dict]:
    index_path = Path(index_path)

    if not index_path.exists():
        print("Chua co file index. Hay tao index truoc.")
        return []

    keyword = keyword.lower().strip()

    with open(index_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    results = []
    for item in records:
        if keyword in item["name"].lower() or keyword in item["path"].lower():
            results.append(item)

    results.sort(key=lambda x: x["modified"], reverse=True)
    return results[:limit]

def show_search_results(results: list[dict]) -> None:
    if not results:
        print("Khong tim thay file phu hop.")
        return

    print("\n========== KET QUA TIM KIEM ==========")
    for i, item in enumerate(results, start=1):
        print(f"{i:>2}. {item['name']}")
        print(f"    Size: {format_size(item['size'])}")
        print(f"    Path: {item['path']}")
        print(f"    Modified: {item['modified']}")

def run_file_indexer() -> None:
    while True:
        print("""
========== FILE INDEXER ==========
1. Tao index file
2. Tim file trong index
3. Xuat report ket qua tim kiem
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            folder = input("Nhap folder/drive can index, VD D:\\: ").strip().strip('"') or "D:\\"
            build_file_index(folder)

        elif choice == "2":
            keyword = input("Nhap ten file/cum tu can tim: ").strip()
            results = search_file_index(keyword)
            show_search_results(results)

        elif choice == "3":
            keyword = input("Nhap ten file/cum tu can tim: ").strip()
            results = search_file_index(keyword, limit=200)
            report = save_report("file_search_results", results)
            print(f"Da luu report: {report}")

        elif choice == "0":
            break
        else:
            print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_file_indexer()
