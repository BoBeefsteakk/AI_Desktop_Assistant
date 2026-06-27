"""Organizer Bridge — cầu nối UI cho các tool sắp xếp file.

Bọc các tool CLI thành hàm scan/apply KHÔNG tương tác để Bot Panel gọi.

An toàn tuyệt đối:
- Scan: read-only.
- Move: dùng `safe_move` + manifest restore + report.
- Delete: dùng `safe_delete` (Recycle Bin) + report.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tools.automation.download_organizer import (
    DOWNLOADS_DIR,
    get_category,
    get_today_folder_name,
    is_downloading_file,
    move_download_files,
    scan_download_files,
)
from tools.core.report_manager import create_report
from tools.core.risk_classifier import PROTECTED, classify_file_risk
from tools.core.safe_executor import safe_delete
from tools.core.safety_utils import is_system_path, safe_move, save_manifest
from tools.storage.duplicate_finder import find_duplicates
from tools.storage.empty_folder_finder import is_skipped

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


# ----------------------- SẮP XẾP THEO LOẠI (mọi file) -----------------------
# Gom MỌI file trong thư mục vào các folder con theo loại: Anh / Video / Audio /
# Tai_lieu / Nen / Cai_dat / Khac (dùng get_category). Không đệ quy để tránh
# gom nhầm file trong các folder loại đã tạo.

_CATEGORY_FOLDERS = {"Anh", "Video", "Audio", "Tai_lieu", "Nen", "Cai_dat", "Khac"}


def scan_organize_by_type(folder: str | Path) -> dict[str, Any]:
    root = Path(folder)
    items: list[dict] = []
    if not root.exists() or is_system_path(root):
        return {"tool": "organize_by_type", "folder": str(folder), "items": [],
                "count": 0, "total_size": 0, "safety_contract": _SAFE_CONTRACT_READONLY}
    if classify_file_risk(root)["risk"] == PROTECTED:
        return {"tool": "organize_by_type", "folder": str(folder), "items": [],
                "count": 0, "total_size": 0, "safety_contract": _SAFE_CONTRACT_READONLY}

    for path in root.iterdir():
        try:
            if not path.is_file() or is_downloading_file(path):
                continue
            category = get_category(path)
            target = root / category / path.name
            # Bỏ qua nếu đã nằm đúng folder loại.
            if path.parent.name in _CATEGORY_FOLDERS:
                continue
            risk = classify_file_risk(path)
            items.append({
                "path": str(path),
                "target_path": str(target),
                "category": category,
                "size": path.stat().st_size,
                "risk": risk["risk"],
                "risk_reason": risk["reason"],
            })
        except (PermissionError, OSError):
            continue
    return {
        "tool": "organize_by_type",
        "folder": str(folder),
        "items": items,
        "count": len(items),
        "total_size": sum(i["size"] for i in items),
        "safety_contract": _SAFE_CONTRACT_READONLY,
    }


def apply_organize_by_type(selected_items: list[dict], folder: str | Path) -> dict[str, Any]:
    records = []
    moved = blocked = errors = 0
    for item in selected_items:
        source = Path(item["path"])
        if classify_file_risk(source)["risk"] == PROTECTED:
            blocked += 1
            records.append({**item, "status": "blocked"})
            continue
        try:
            record = safe_move(source, Path(item["target_path"]))
            record.update({"category": item.get("category"), "size": item.get("size"), "status": "moved"})
            records.append(record)
            moved += 1
        except Exception as error:
            errors += 1
            records.append({**item, "status": "error", "error": str(error)})

    moved_records = [r for r in records if r.get("status") == "moved"]
    manifest = save_manifest("organize_by_type_backup", moved_records) if moved_records else None
    report = create_report(
        tool_name="organize_by_type",
        action="ui_organize_by_type",
        status="success",
        input_data={"folder": str(folder)},
        results={"moved_count": moved, "blocked_count": blocked, "error_count": errors,
                 "records": records, "manifest": str(manifest) if manifest else None},
    )
    return {"tool": "organize_by_type", "moved_count": moved, "blocked_count": blocked,
            "error_count": errors, "manifest": str(manifest) if manifest else None,
            "report": str(report)}


# ----------------------- DUPLICATE FINDER (giữ file CŨ nhất) -----------------------

def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def scan_duplicates(folder: str | Path, recursive: bool = True) -> dict[str, Any]:
    raw = find_duplicates(str(folder), recursive=recursive)
    items = []
    for it in raw:
        a, b = it.get("original", ""), it.get("duplicate", "")
        # Giữ file CŨ hơn (file gốc thật sự), xóa file mới hơn.
        if _mtime(b) < _mtime(a):
            keep, drop = b, a
        else:
            keep, drop = a, b
        items.append({**it, "keep": keep, "duplicate": drop, "original": keep})
    return {
        "tool": "duplicate_finder",
        "folder": str(folder),
        "items": items,
        "count": len(items),
        "total_size": sum(i.get("size", 0) for i in items),
        "safety_contract": _SAFE_CONTRACT_READONLY,
    }


def apply_duplicate_delete(selected_items: list[dict]) -> dict[str, Any]:
    """Xóa (Recycle Bin) các bản sao đã chọn — luôn GIỮ file gốc (cũ nhất)."""
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


# ----------------------- EMPTY FOLDER FINDER (đệ quy đúng) -----------------------

def _is_effectively_empty(path: Path) -> bool:
    """Folder rỗng thật sự HOẶC chỉ chứa toàn folder rỗng (không có file nào)."""
    try:
        for child in path.iterdir():
            if child.is_file():
                return False
            if child.is_dir():
                if is_skipped(child):
                    return False
                if not _is_effectively_empty(child):
                    return False
        return True
    except (PermissionError, OSError):
        return False


def scan_empty_folders(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    items: list[dict] = []
    if not base.exists() or is_system_path(base):
        return {"tool": "empty_folder_finder", "root": str(root), "items": [],
                "count": 0, "total_size": 0, "safety_contract": _SAFE_CONTRACT_READONLY}

    # Tìm các folder "rỗng hiệu quả" CAO NHẤT (xóa folder cha sẽ gom cả con rỗng).
    def walk(path: Path):
        try:
            children = [c for c in path.iterdir() if c.is_dir()]
        except (PermissionError, OSError):
            return
        for child in children:
            if is_skipped(child):
                continue
            if _is_effectively_empty(child):
                risk = classify_file_risk(child)
                if risk["risk"] != PROTECTED:
                    items.append({
                        "path": str(child),
                        "risk": risk["risk"],
                        "risk_reason": risk["reason"],
                    })
                # KHÔNG đi sâu thêm — xóa folder cha là đủ.
            else:
                walk(child)

    walk(base)
    return {
        "tool": "empty_folder_finder",
        "root": str(root),
        "items": items,
        "count": len(items),
        "total_size": 0,
        "safety_contract": _SAFE_CONTRACT_READONLY,
    }


def apply_empty_delete(selected_items: list[dict]) -> dict[str, Any]:
    """Xóa (Recycle Bin) các folder rỗng đã chọn (kèm cây con rỗng bên trong)."""
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
