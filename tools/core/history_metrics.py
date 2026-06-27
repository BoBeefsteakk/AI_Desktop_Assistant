"""History & Metrics — tổng hợp "AI đã làm gì" để hiển thị trong UI (Phase 9).

Đọc `reports/report_index.jsonl` (read-only) và tổng hợp các hành động thật sự
tác động tới file (dọn rác, sắp xếp, xóa trùng, xóa folder rỗng) thành:
- Lịch sử gần đây (mỗi dòng: thời gian + mô tả tiếng Việt + số lượng).
- Hiệu quả (đếm theo N ngày: tổng file đã dọn/sắp xếp, số phiên).

Hoàn toàn read-only — không xóa/move/đụng file.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR

_INDEX = BASE_DIR / "reports" / "report_index.jsonl"

# tool -> (động từ tiếng Việt, khóa đếm trong summary)
_ACTION_TOOLS: dict[str, tuple[str, str]] = {
    "download_organizer": ("Sắp xếp Downloads", "moved_count"),
    "organize_by_type": ("Sắp xếp theo loại", "moved_count"),
    "media_organizer": ("Gom media", "moved_count"),
    "duplicate_finder": ("Xóa file trùng", "deleted"),
    "empty_folder_finder": ("Xóa folder rỗng", "deleted"),
    "safe_delete_adapter": ("Dọn file rác", "deleted"),
}


def _read_index() -> list[dict[str, Any]]:
    if not _INDEX.exists():
        return []
    rows = []
    with open(_INDEX, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _entry_count(row: dict[str, Any], key: str) -> int:
    summary = row.get("summary") or {}
    for k in (key, "moved_count", "deleted", "deleted_count"):
        val = summary.get(k)
        if isinstance(val, int):
            return val
    return 0


# Chỉ tính các hành động THẬT do user bấm trong UI (tab Sắp xếp / Dọn 1 chạm).
# Report do test/CLI sinh ra trong index trông y hệt nên ta lọc theo action UI
# riêng — đây là nguồn chân lý cho "user đã làm gì qua app".
_UI_ACTIONS = {
    "ui_organize_by_type",
    "ui_delete_duplicates",
    "ui_delete_empty_folders",
}


def _is_real_action(row: dict[str, Any]) -> bool:
    tool = row.get("tool", "")
    if tool not in _ACTION_TOOLS:
        return False
    action = str(row.get("action", ""))
    inp = row.get("input") or row.get("input_data") or {}
    preview = str(inp.get("preview_report", "")) if isinstance(inp, dict) else ""
    is_ui = action in _UI_ACTIONS or preview == "ui_organizer"
    if not is_ui:
        return False
    return _entry_count(row, _ACTION_TOOLS[tool][1]) > 0


def build_history(limit: int = 50) -> dict[str, Any]:
    """Lịch sử các hành động thật (mới nhất trước)."""
    rows = [r for r in _read_index() if _is_real_action(r)]
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    items = []
    for r in rows[:limit]:
        tool = r["tool"]
        verb, key = _ACTION_TOOLS[tool]
        count = _entry_count(r, key)
        ts = str(r.get("created_at", "")).replace("T", " ")[:19]
        items.append({
            "time": ts,
            "tool": tool,
            "text": f"{verb}: {count} mục",
            "count": count,
        })
    return {"schema_version": "history_v1", "items": items, "count": len(items),
            "safety_contract": {"read_only": True}}


def build_metrics(days: int = 7) -> dict[str, Any]:
    """Tổng hợp hiệu quả trong N ngày gần nhất."""
    cutoff = datetime.now() - timedelta(days=days)
    rows = [r for r in _read_index() if _is_real_action(r)]
    moved = deleted = sessions = 0
    by_tool: dict[str, int] = {}
    for r in rows:
        try:
            when = datetime.fromisoformat(str(r.get("created_at", "")))
        except ValueError:
            continue
        if when < cutoff:
            continue
        tool = r["tool"]
        verb, key = _ACTION_TOOLS[tool]
        count = _entry_count(r, key)
        sessions += 1
        by_tool[verb] = by_tool.get(verb, 0) + count
        if key == "moved_count":
            moved += count
        else:
            deleted += count
    return {
        "schema_version": "metrics_v1",
        "days": days,
        "moved_total": moved,
        "deleted_total": deleted,
        "sessions": sessions,
        "by_tool": by_tool,
        "safety_contract": {"read_only": True},
    }


def run_history_metrics() -> dict[str, Any]:
    """Entry point CLI: in nhanh metrics + vài dòng lịch sử."""
    metrics = build_metrics()
    history = build_history(limit=10)
    print(f"7 ngày qua: sắp xếp {metrics['moved_total']} file, "
          f"dọn/xóa {metrics['deleted_total']} mục, {metrics['sessions']} phiên.")
    for it in history["items"]:
        print(f"  {it['time']}  {it['text']}")
    return {"metrics": metrics, "history": history}


if __name__ == "__main__":
    run_history_metrics()
