"""Organizer Bridge — cầu nối UI cho 4 tool sắp xếp file.

Bọc các tool CLI (Download Organizer, Media Organizer, Duplicate Finder, Empty
Folder Finder) thành hàm scan/apply KHÔNG tương tác để Bot Panel gọi được.

An toàn tuyệt đối:
- Scan: read-only, trả danh sách item (đã loại file PROTECTED ở tầng tool).
- Apply move: dùng `move_download_files`/`move_media_files` (qua `safe_move` +
  manifest restore + report).
- Apply delete: dùng `safe_delete` (vào Recycle Bin, không xóa vĩnh viễn) +
  report. Chỉ xử lý đúng các item user đã chọn.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.automation.download_organizer import (
    DOWNLOADS_DIR,
    get_today_folder_name,
    move_download_files,
    scan_download_files,
)
from tools.core.report_manager import create_report
from tools.core.safe_executor import safe_delete
from tools.storage.duplicate_finder import find_duplicates
from tools.storage.empty_folder_finder import find_empty_folders
from tools.storage.media_organizer import (
    MEDIA_ORGANIZER_TARGET_FOLDER_NAME,
    move_media_files,
    scan_media_files,
)

_SAFE_CONTRACT_READONLY = {"read_only": True, "delete_enabled": False, "move_enabled": False}


# ----------------------- DOWNLOAD ORGANIZER -----------------------

def scan_downloads(downloads_dir: str | Path = DOWNLOADS_DIR) -> dict[str, Any]:
    items = scan_download_files(downloads_dir)
    return {
        "tool": "download_organizer",
        "downloads_dir": str(downloads_dir),
        "items": items,
        "count": len(items),
        "total_size": sum(i.get("size", 0) for i in items),
        "safety_contract": _SAFE_CONTRACT_READONLY,
    }


def apply_downloads(selected_items: list[dict], downloads_dir: str | Path = DOWNLOADS_DIR) -> dict[str, Any]:
    downloads_dir = Path(downloads_dir)
    today_folder = downloads_dir / get_today_folder_name()
    if not selected_items:
        return {"tool": "download_organizer", "moved_count": 0, "skipped": "empty_selection"}
    return move_download_files(selected_items, downloads_dir, today_folder, preview_report="ui_organizer")


# ----------------------- MEDIA ORGANIZER -----------------------

def scan_media(folder: str | Path, recursive: bool = False) -> dict[str, Any]:
    items = scan_media_files(str(folder), recursive=recursive)
    return {
        "tool": "media_organizer",
        "folder": str(folder),
        "recursive": recursive,
        "items": items,
        "count": len(items),
        "total_size": sum(i.get("size", 0) for i in items),
        "safety_contract": _SAFE_CONTRACT_READONLY,
    }


def apply_media(selected_items: list[dict], folder: str | Path, recursive: bool = False) -> dict[str, Any]:
    root = Path(folder)
    target = root / MEDIA_ORGANIZER_TARGET_FOLDER_NAME
    if not selected_items:
        return {"tool": "media_organizer", "moved_count": 0, "skipped": "empty_selection"}
    return move_media_files(selected_items, root, target, recursive, preview_report="ui_organizer")


# ----------------------- DUPLICATE FINDER -----------------------

def scan_duplicates(folder: str | Path, recursive: bool = True) -> dict[str, Any]:
    items = find_duplicates(str(folder), recursive=recursive)
    return {
        "tool": "duplicate_finder",
        "folder": str(folder),
        "items": items,
        "count": len(items),
        "total_size": sum(i.get("size", 0) for i in items),
        "safety_contract": _SAFE_CONTRACT_READONLY,
    }


def apply_duplicate_delete(selected_items: list[dict]) -> dict[str, Any]:
    """Xóa (vào Recycle Bin) các bản sao đã chọn — giữ nguyên bản gốc."""
    results = []
    for item in selected_items:
        dup_path = item.get("duplicate")
        if not dup_path:
            continue
        results.append({**item, **safe_delete(dup_path)})
    deleted = sum(1 for r in results if r.get("status") == "deleted")
    blocked = sum(1 for r in results if r.get("status") == "blocked")
    report = create_report(
        tool_name="duplicate_finder",
        action="ui_delete_duplicates",
        status="success",
        risk_level="safe_delete",
        input_data={"selected_count": len(selected_items)},
        results={"deleted": deleted, "blocked": blocked, "records": results},
    )
    return {"tool": "duplicate_finder", "deleted": deleted, "blocked": blocked,
            "records": results, "report": str(report)}


# ----------------------- EMPTY FOLDER FINDER -----------------------

def scan_empty_folders(root: str | Path) -> dict[str, Any]:
    items = find_empty_folders(str(root))
    return {
        "tool": "empty_folder_finder",
        "root": str(root),
        "items": items,
        "count": len(items),
        "total_size": 0,
        "safety_contract": _SAFE_CONTRACT_READONLY,
    }


def apply_empty_delete(selected_items: list[dict]) -> dict[str, Any]:
    """Xóa (vào Recycle Bin) các folder rỗng đã chọn."""
    results = []
    for item in selected_items:
        path = item.get("path")
        if not path:
            continue
        results.append({**item, **safe_delete(path)})
    deleted = sum(1 for r in results if r.get("status") == "deleted")
    blocked = sum(1 for r in results if r.get("status") == "blocked")
    report = create_report(
        tool_name="empty_folder_finder",
        action="ui_delete_empty_folders",
        status="success",
        risk_level="safe_delete",
        input_data={"selected_count": len(selected_items)},
        results={"deleted": deleted, "blocked": blocked, "records": results},
    )
    return {"tool": "empty_folder_finder", "deleted": deleted, "blocked": blocked,
            "records": results, "report": str(report)}
