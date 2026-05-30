from __future__ import annotations

import csv
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import (
    DEFAULT_LARGE_FILE_MB,
    DEFAULT_RESULT_LIMIT,
    DEFAULT_SCAN_FOLDER,
    WIZTREE_ENABLED,
    WIZTREE_EXE_PATH,
    WIZTREE_EXPORT_DIR,
    WIZTREE_PREFER_FOR_SYSTEM_ADVISOR,
    WIZTREE_TIMEOUT_SECONDS,
    WIZTREE_USE_ADMIN,
)
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report
from tools.core.safety_utils import ask_yes_no, format_size


def is_wiztree_available() -> bool:
    return WIZTREE_ENABLED and WIZTREE_EXE_PATH.exists()


def get_wiztree_status() -> dict[str, Any]:
    return {
        "enabled": WIZTREE_ENABLED,
        "available": is_wiztree_available(),
        "exe_path": str(WIZTREE_EXE_PATH),
        "export_dir": str(WIZTREE_EXPORT_DIR),
        "use_admin": WIZTREE_USE_ADMIN,
        "timeout_seconds": WIZTREE_TIMEOUT_SECONDS,
        "prefer_for_system_advisor": WIZTREE_PREFER_FOR_SYSTEM_ADVISOR,
    }


def parse_int_cell(value: Any) -> int:
    if value is None:
        return 0

    text = str(value).strip().replace(",", "")
    if not text:
        return 0

    try:
        return int(text)
    except ValueError:
        return 0


def get_case_insensitive(row: dict[str, Any], key: str, default: Any = "") -> Any:
    wanted = key.lower()
    for row_key, value in row.items():
        if str(row_key).strip().lower() == wanted:
            return value
    return default


def normalize_wiztree_row(row: dict[str, Any]) -> dict[str, Any] | None:
    raw_path = str(get_case_insensitive(row, "File Name", "")).strip()
    if not raw_path:
        return None

    size = parse_int_cell(get_case_insensitive(row, "Size", 0))
    allocated = parse_int_cell(get_case_insensitive(row, "Allocated", 0))
    files = parse_int_cell(get_case_insensitive(row, "Files", 0))
    folders = parse_int_cell(get_case_insensitive(row, "Folders", 0))
    attributes = str(get_case_insensitive(row, "Attributes", ""))
    is_folder = raw_path.endswith("\\") or "D" in attributes.upper() or files > 0 or folders > 0
    path = raw_path.rstrip("\\") if is_folder else raw_path

    return {
        "path": path,
        "size": size,
        "allocated": allocated,
        "modified": str(get_case_insensitive(row, "Modified", "")),
        "attributes": attributes,
        "files": files,
        "folders": folders,
        "is_folder": is_folder,
        "extension": Path(path).suffix.lower() or "[no_ext]",
        "source": "wiztree",
    }


def parse_wiztree_csv(csv_path: str | Path) -> list[dict[str, Any]]:
    path = Path(csv_path)
    records = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            record = normalize_wiztree_row(row)
            if record:
                records.append(record)

    return records


def get_top_wiztree_folders(records: list[dict[str, Any]], limit: int = 15) -> list[dict[str, Any]]:
    folders = [
        {
            "path": item["path"],
            "size": item["size"],
            "allocated": item["allocated"],
            "files": item["files"],
            "folders": item["folders"],
            "source": "wiztree",
        }
        for item in records
        if item["is_folder"]
    ]
    folders.sort(key=lambda item: item["size"], reverse=True)
    return folders[:limit]


def get_top_wiztree_files(
    records: list[dict[str, Any]],
    min_size_mb: int = DEFAULT_LARGE_FILE_MB,
    limit: int = DEFAULT_RESULT_LIMIT,
) -> list[dict[str, Any]]:
    min_size_bytes = min_size_mb * 1024 * 1024
    files = [
        {
            "path": item["path"],
            "size": item["size"],
            "allocated": item["allocated"],
            "extension": item["extension"],
            "modified": item["modified"],
            "source": "wiztree",
        }
        for item in records
        if not item["is_folder"] and item["size"] >= min_size_bytes
    ]
    files.sort(key=lambda item: item["size"], reverse=True)
    return files[:limit]


def build_export_path(root: str | Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_root = str(root).replace("\\", "_").replace(":", "").strip("_") or "root"
    return WIZTREE_EXPORT_DIR / f"wiztree_{safe_root}_{timestamp}.csv"


def export_wiztree_csv(
    root: str | Path,
    *,
    export_files: bool = True,
    export_folders: bool = True,
    filter_pattern: str | None = None,
) -> dict[str, Any]:
    if not is_wiztree_available():
        return {
            "status": "unavailable",
            "reason": "WizTree is disabled or executable is missing.",
            "wiztree": get_wiztree_status(),
        }

    scan_root = str(root)
    export_path = build_export_path(scan_root)
    export_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        str(WIZTREE_EXE_PATH),
        scan_root,
        f"/export={export_path}",
        f"/admin={1 if WIZTREE_USE_ADMIN else 0}",
        f"/exportfiles={1 if export_files else 0}",
        f"/exportfolders={1 if export_folders else 0}",
        "/sortby=1",
    ]

    if filter_pattern:
        command.append(f"/filter={filter_pattern}")

    try:
        completed = subprocess.run(
            command,
            cwd=str(WIZTREE_EXE_PATH.parent),
            text=True,
            capture_output=True,
            timeout=WIZTREE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        result = {
            "status": "timeout",
            "command": command,
            "timeout_seconds": WIZTREE_TIMEOUT_SECONDS,
            "error": str(exc),
        }
        log_action("wiztree_adapter", "export_wiztree_csv", "timeout", result)
        return result

    status = "success" if completed.returncode == 0 and export_path.exists() else "error"
    result = {
        "status": status,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-2000:],
        "export_path": str(export_path),
        "export_exists": export_path.exists(),
    }

    log_action("wiztree_adapter", "export_wiztree_csv", status, result)
    return result


def scan_storage_with_wiztree(
    root: str | Path,
    *,
    min_size_mb: int = DEFAULT_LARGE_FILE_MB,
    limit: int = DEFAULT_RESULT_LIMIT,
    create_tool_report: bool = True,
) -> dict[str, Any]:
    export_result = export_wiztree_csv(root)

    if export_result["status"] != "success":
        return {
            "status": export_result["status"],
            "export": export_result,
            "top_folders": [],
            "large_files": [],
        }

    records = parse_wiztree_csv(export_result["export_path"])
    top_folders = get_top_wiztree_folders(records, limit=limit)
    large_files = get_top_wiztree_files(records, min_size_mb=min_size_mb, limit=limit)

    result = {
        "status": "success",
        "export": export_result,
        "record_count": len(records),
        "top_folders": top_folders,
        "large_files": large_files,
    }

    if create_tool_report:
        report = create_report(
            tool_name="wiztree_adapter",
            action="scan_storage",
            status="success",
            risk_level="safe",
            input_data={
                "root": str(root),
                "min_size_mb": min_size_mb,
                "limit": limit,
                "use_admin": WIZTREE_USE_ADMIN,
            },
            results=result,
            summary={
                "status": "success",
                "record_count": len(records),
                "top_folder_count": len(top_folders),
                "large_file_count": len(large_files),
                "undo_available": False,
            },
            undo_available=False,
            recommendations=[
                "WizTree adapter is read-only; review results before running cleanup tools.",
                "Use Undo Manager only for operations that created manifests.",
            ],
            tags=["storage", "wiztree", "read_only"],
        )
        result["report"] = str(report)

    log_action(
        "wiztree_adapter",
        "scan_storage_with_wiztree",
        result["status"],
        {
            "root": str(root),
            "record_count": result.get("record_count", 0),
            "top_folder_count": len(top_folders),
            "large_file_count": len(large_files),
            "report": result.get("report"),
        },
    )
    return result


def show_wiztree_results(result: dict[str, Any]) -> None:
    if result["status"] != "success":
        print(f"WizTree khong scan duoc: {result['status']}")
        print(result.get("export", {}).get("reason") or result.get("export", {}).get("stderr", ""))
        return

    print("\n========== WIZTREE TOP FOLDERS ==========")
    for index, item in enumerate(result["top_folders"], start=1):
        print(f"{index:>2}. {format_size(item['size']):>10} | {item['path']}")

    print("\n========== WIZTREE LARGE FILES ==========")
    for index, item in enumerate(result["large_files"], start=1):
        print(
            f"{index:>2}. {format_size(item['size']):>10} | "
            f"{item['extension']:<8} | {item['path']}"
        )

    print(f"\nCSV export: {result['export']['export_path']}")
    if result.get("report"):
        print(f"Report: {result['report']}")


def run_wiztree_adapter() -> None:
    while True:
        print("""
========== WIZTREE ADAPTER ==========
1. Xem trang thai WizTree
2. Scan nhanh bang WizTree
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print(get_wiztree_status())

        elif choice == "2":
            root = input(f"Nhap drive/folder can scan [{DEFAULT_SCAN_FOLDER}]: ").strip().strip('"') or DEFAULT_SCAN_FOLDER
            raw_limit = input(f"Hien thi top bao nhieu item? [{DEFAULT_RESULT_LIMIT}]: ").strip()
            limit = int(raw_limit) if raw_limit.isdigit() else DEFAULT_RESULT_LIMIT
            raw_size = input(f"Large file threshold MB [{DEFAULT_LARGE_FILE_MB}]: ").strip()
            min_size_mb = int(raw_size) if raw_size.isdigit() else DEFAULT_LARGE_FILE_MB

            if not ask_yes_no("WizTree se export CSV chi doc. Tiep tuc?", default=False):
                print("Da huy.")
                continue

            result = scan_storage_with_wiztree(root, min_size_mb=min_size_mb, limit=limit)
            show_wiztree_results(result)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_wiztree_adapter()
