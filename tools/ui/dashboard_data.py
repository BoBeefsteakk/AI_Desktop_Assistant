"""Dashboard Data — bộ cấp số liệu read-only cho giao diện Trang chủ (Phase 10).

Gom nhanh tình trạng máy thành một dict gọn để giao diện web (pywebview) vẽ
dashboard: ổ đĩa, RAM, CPU, file rác trong Downloads, sức khỏe SMART, và hiệu
quả 7 ngày qua.

Module này CHỈ đọc — không xóa, move hay đụng file user. Mọi thao tác thật vẫn
đi qua flow token-gated cũ (Bot Panel / safe_executor).

Entry point: `get_dashboard_snapshot()`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

DASHBOARD_SCHEMA = "dashboard_snapshot_v1"

# Phân loại file -> nhóm gọn để vẽ thanh "dung lượng theo loại".
_CATEGORY_GROUP = {
    "Anh": "image",
    "Video": "video",
    "Audio": "audio",
    "Tai_lieu": "doc",
    "Nen": "archive",
    "Cai_dat": "installer",
}


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 11:
        return "Chào buổi sáng"
    if hour < 14:
        return "Chào buổi trưa"
    if hour < 18:
        return "Chào buổi chiều"
    return "Chào buổi tối"


def _primary_disk(disks: list[dict]) -> dict | None:
    """Ưu tiên ổ C:, không có thì lấy ổ đầu tiên."""
    for d in disks:
        if str(d.get("mountpoint", "")).upper().startswith("C"):
            return d
    return disks[0] if disks else None


def _ram_snapshot() -> dict[str, Any]:
    import psutil

    vm = psutil.virtual_memory()
    return {
        "total": vm.total,
        "used": vm.used,
        "available": vm.available,
        "percent": round(vm.percent),
    }


def _cpu_percent() -> int:
    import psutil

    # interval ngắn để có số thực, không treo UI quá lâu.
    return round(psutil.cpu_percent(interval=0.3))


def _junk_snapshot() -> dict[str, Any]:
    """Quét file rác trong Downloads (không đệ quy, read-only)."""
    try:
        from tools.automation.download_organizer import DOWNLOADS_DIR
        from tools.system.junk_file_cleaner import scan_junk_files

        files = scan_junk_files(str(DOWNLOADS_DIR), recursive=False)
        # Chỉ tính file thực sự an toàn để dọn.
        safe = [f for f in files if f.get("risk") == "safe_delete"]
        return {
            "count": len(safe),
            "total_size": sum(f.get("size", 0) for f in safe),
            "scanned": str(DOWNLOADS_DIR),
        }
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        return {"count": 0, "total_size": 0, "error": str(exc)}


def _category_breakdown() -> list[dict[str, Any]]:
    """Dung lượng Downloads theo nhóm loại (read-only, không đệ quy)."""
    try:
        from pathlib import Path

        from tools.automation.download_organizer import DOWNLOADS_DIR, get_category

        sizes: dict[str, int] = {}
        root = Path(DOWNLOADS_DIR)
        if root.exists():
            for entry in root.iterdir():
                if not entry.is_file():
                    continue
                try:
                    category = get_category(entry.name)
                    group = _CATEGORY_GROUP.get(category, "other")
                    sizes[group] = sizes.get(group, 0) + entry.stat().st_size
                except (PermissionError, OSError):
                    continue
        items = [{"group": g, "size": s} for g, s in sizes.items() if s > 0]
        items.sort(key=lambda x: x["size"], reverse=True)
        return items
    except Exception:  # pragma: no cover
        return []


def _smart_snapshot() -> dict[str, Any]:
    try:
        from tools.storage.system_advisor import get_disk_health_snapshot

        smart = get_disk_health_snapshot().get("smart_health", {})
        return {
            "status": smart.get("status", "unavailable"),
            "device_count": smart.get("device_count", 0),
            "checked_count": smart.get("checked_count", 0),
        }
    except Exception:  # pragma: no cover
        return {"status": "unavailable", "device_count": 0, "checked_count": 0}


def _metrics_snapshot() -> dict[str, Any]:
    try:
        from tools.core.history_metrics import build_metrics

        return build_metrics(days=7)
    except Exception:  # pragma: no cover
        return {"moved_total": 0, "deleted_total": 0, "sessions": 0}


def get_dashboard_snapshot() -> dict[str, Any]:
    """Trả về toàn bộ số liệu cho màn Trang chủ. Read-only."""
    from tools.system.disk_checker import get_disk_info

    disks = get_disk_info()
    primary = _primary_disk(disks)

    return {
        "schema_version": DASHBOARD_SCHEMA,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "greeting": _greeting(),
        "disk_primary": primary,
        "disks": disks,
        "ram": _ram_snapshot(),
        "cpu_percent": _cpu_percent(),
        "junk": _junk_snapshot(),
        "categories": _category_breakdown(),
        "smart": _smart_snapshot(),
        "metrics": _metrics_snapshot(),
        "safety_contract": {
            "read_only": True,
            "delete_enabled": False,
            "move_enabled": False,
        },
    }


def get_clean_details(limit: int = 300) -> dict[str, Any]:
    """Danh sách file rác an toàn trong Downloads (read-only)."""
    from pathlib import Path as _P

    try:
        from tools.automation.download_organizer import DOWNLOADS_DIR
        from tools.system.junk_file_cleaner import scan_junk_files

        files = scan_junk_files(str(DOWNLOADS_DIR), recursive=False)
        safe = [f for f in files if f.get("risk") == "safe_delete"]
        items = [
            {"name": _P(f["path"]).name, "path": f["path"], "size": f.get("size", 0)}
            for f in safe[:limit]
        ]
        return {
            "items": items,
            "count": len(safe),
            "total_size": sum(f.get("size", 0) for f in safe),
            "folder": str(DOWNLOADS_DIR),
        }
    except Exception as exc:  # pragma: no cover
        return {"items": [], "count": 0, "total_size": 0, "error": str(exc)}


def get_organizer_overview() -> dict[str, Any]:
    """Tổng quan 3 tác vụ sắp xếp trên Downloads (read-only)."""
    try:
        from tools.automation.download_organizer import DOWNLOADS_DIR
        from tools.core.organizer_bridge import (
            scan_downloads,
            scan_duplicates,
            scan_empty_folders,
        )

        dl = scan_downloads()
        try:
            dup = scan_duplicates(DOWNLOADS_DIR)
        except Exception:
            dup = {"count": 0, "total_size": 0}
        try:
            empty = scan_empty_folders(DOWNLOADS_DIR)
        except Exception:
            empty = {"count": 0}
        return {
            "folder": str(DOWNLOADS_DIR),
            "downloads": {"count": dl.get("count", 0), "total_size": dl.get("total_size", 0)},
            "duplicates": {"count": dup.get("count", 0), "total_size": dup.get("total_size", 0)},
            "empty": {"count": empty.get("count", 0)},
            "categories": _category_breakdown(),
        }
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "downloads": {"count": 0}, "duplicates": {"count": 0}, "empty": {"count": 0}, "categories": []}


def get_history_overview() -> dict[str, Any]:
    """Lịch sử + hiệu quả 7 ngày (read-only)."""
    try:
        from tools.core.history_metrics import build_history, build_metrics

        return {"history": build_history(40), "metrics": build_metrics(7)}
    except Exception as exc:  # pragma: no cover
        return {"history": {"items": []}, "metrics": {}, "error": str(exc)}


if __name__ == "__main__":
    import json

    print(json.dumps(get_dashboard_snapshot(), ensure_ascii=False, indent=2))
