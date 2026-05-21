from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Dict, Any

APP_DIR = Path(__file__).resolve().parents[1]
BACKUP_DIR = APP_DIR / "backups"
REPORT_DIR = APP_DIR / "reports"

SAFE_SKIP_DIRS = {
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
}

def ensure_dirs() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def format_size(size: int | float) -> str:
    size = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def is_system_path(path: str | Path) -> bool:
    p = str(Path(path).resolve()).lower()
    return any(p.startswith(x.lower()) for x in SAFE_SKIP_DIRS)

def ask_yes_no(message: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    answer = input(f"{message} ({suffix}): ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes", "co", "có")

def save_report(name: str, data: Any) -> Path:
    ensure_dirs()
    path = REPORT_DIR / f"{name}_{timestamp()}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path

def save_manifest(name: str, records: List[Dict[str, Any]]) -> Path:
    ensure_dirs()
    path = BACKUP_DIR / f"{name}_{timestamp()}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return path

def safe_move(src: str | Path, dst: str | Path) -> Dict[str, str]:
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    final_dst = dst
    count = 1
    while final_dst.exists():
        stem, suffix = dst.stem, dst.suffix
        final_dst = dst.with_name(f"{stem}_{count}{suffix}")
        count += 1

    shutil.move(str(src), str(final_dst))
    return {"old_path": str(src), "new_path": str(final_dst)}

def restore_from_manifest(manifest_path: str | Path) -> None:
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        print("Khong tim thay file backup manifest.")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    restored = 0
    for item in reversed(records):
        old_path = Path(item.get("old_path", ""))
        new_path = Path(item.get("new_path", ""))

        if new_path.exists():
            old_path.parent.mkdir(parents=True, exist_ok=True)
            final_old = old_path
            count = 1
            while final_old.exists():
                final_old = old_path.with_name(f"{old_path.stem}_restored_{count}{old_path.suffix}")
                count += 1

            shutil.move(str(new_path), str(final_old))
            restored += 1

    print(f"Da restore {restored} file tu backup manifest.")
