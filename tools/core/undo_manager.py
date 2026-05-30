from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.settings import BACKUPS_DIR
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report
from tools.core.safety_utils import ask_yes_no, format_size, restore_from_manifest


def list_manifest_files(limit: int = 30) -> list[dict[str, Any]]:
    manifests = sorted(
        BACKUPS_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    results = []
    for path in manifests[:limit]:
        try:
            stat = path.stat()
            record_count = len(load_manifest_records(path))
            status = "readable"
            error = None
        except Exception as exc:
            stat = path.stat()
            record_count = 0
            status = "error"
            error = str(exc)

        results.append({
            "path": str(path),
            "name": path.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "record_count": record_count,
            "status": status,
            "error": error,
        })

    return results


def load_manifest_records(manifest_path: str | Path) -> list[dict[str, Any]]:
    path = Path(manifest_path)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Manifest must be a JSON list.")

    records = []
    for item in data:
        if isinstance(item, dict):
            records.append(item)

    return records


def preview_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path)

    if not path.exists():
        return {
            "status": "missing",
            "manifest": str(path),
            "records": [],
            "restorable_count": 0,
            "missing_count": 0,
            "invalid_count": 0,
        }

    records = load_manifest_records(path)
    preview_records = []
    restorable_count = 0
    missing_count = 0
    invalid_count = 0

    for item in records:
        old_path_raw = item.get("old_path")
        new_path_raw = item.get("new_path")

        if not old_path_raw or not new_path_raw:
            invalid_count += 1
            preview_records.append({
                "status": "invalid",
                "reason": "Missing old_path or new_path.",
                "record": item,
            })
            continue

        old_path = Path(old_path_raw)
        new_path = Path(new_path_raw)

        if new_path.exists():
            restorable_count += 1
            status = "restorable"
        else:
            missing_count += 1
            status = "missing"

        preview_records.append({
            "status": status,
            "old_path": str(old_path),
            "new_path": str(new_path),
            "new_path_exists": new_path.exists(),
        })

    return {
        "status": "success",
        "manifest": str(path),
        "records": preview_records,
        "restorable_count": restorable_count,
        "missing_count": missing_count,
        "invalid_count": invalid_count,
    }


def restore_manifest(
    manifest_path: str | Path,
    *,
    require_under_backups: bool = True,
) -> dict[str, Any]:
    path = Path(manifest_path)

    if require_under_backups:
        try:
            path.resolve().relative_to(BACKUPS_DIR.resolve())
        except ValueError:
            result = {
                "status": "blocked",
                "manifest": str(path),
                "reason": "Manifest is outside backups directory.",
            }
            log_action("undo_manager", "restore_manifest", "blocked", result)
            return result

    preview = preview_manifest(path)
    if preview["status"] != "success":
        log_action("undo_manager", "restore_manifest", preview["status"], preview)
        return preview

    result = restore_from_manifest(path)
    status = "success" if result["status"] == "success" else "error"

    report = create_report(
        tool_name="undo_manager",
        status=status,
        input_data={
            "manifest": str(path),
            "require_under_backups": require_under_backups,
        },
        results={
            "preview": preview,
            "restore": result,
        },
        recommendations=[
            "Review restored_to paths, especially when name collisions created _restored suffixes.",
            "Keep manifests until the restored files are verified.",
        ],
    )

    log_action(
        "undo_manager",
        "restore_manifest",
        status,
        {
            "manifest": str(path),
            "restored": result.get("restored_count", 0),
            "skipped": result.get("skipped_count", 0),
            "report": str(report),
        },
    )

    return {
        **result,
        "preview": preview,
        "report": str(report),
    }


def show_manifests(limit: int = 30) -> None:
    manifests = list_manifest_files(limit=limit)

    print("\n========== UNDO MANIFESTS ==========")
    if not manifests:
        print("Chua co manifest nao trong backups.")
        return

    for index, item in enumerate(manifests, start=1):
        print(
            f"{index:>2}. {item['name']} | "
            f"{item['record_count']} records | "
            f"{format_size(item['size'])} | "
            f"{item['status']}"
        )


def run_undo_manager() -> None:
    while True:
        print("""
========== UNDO MANAGER ==========
1. Xem manifest gan day
2. Preview manifest
3. Restore manifest
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            raw_limit = input("So manifest muon xem [30]: ").strip()
            limit = int(raw_limit) if raw_limit.isdigit() else 30
            show_manifests(limit=limit)

        elif choice == "2":
            manifest = input("Nhap duong dan manifest .json: ").strip().strip('"')
            preview = preview_manifest(manifest)
            print(json.dumps(preview, ensure_ascii=False, indent=2))

        elif choice == "3":
            manifest = input("Nhap duong dan manifest .json: ").strip().strip('"')
            preview = preview_manifest(manifest)
            print(json.dumps(preview, ensure_ascii=False, indent=2))

            if preview.get("restorable_count", 0) <= 0:
                print("Khong co file nao co the restore.")
                continue

            if not ask_yes_no("Xac nhan restore manifest nay?", default=False):
                print("Da huy restore.")
                continue

            result = restore_manifest(manifest)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_undo_manager()
