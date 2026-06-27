from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.core.bot_controller import build_selection_session, iter_selection_items
from tools.core.cleanup_rules import get_cleanup_recommendation
from tools.core.risk_classifier import SAFE_DELETE, classify_file_risk
from tools.core.safety_utils import format_size


ONE_CLICK_CLEANUP_SCHEMA = "one_click_cleanup_plan_v1"


def normalize_path_key(path: str | Path) -> str:
    try:
        resolved = Path(path).resolve(strict=False)
    except OSError:
        resolved = Path(path).absolute()
    return str(resolved).replace("\\", "/").rstrip("/").lower()


def build_one_click_cleanup_plan(
    *,
    selection_session: dict[str, Any] | None = None,
    bot_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only plan for the UI's one-click cleanup confirmation."""
    session = selection_session
    if session is None:
        session = build_selection_session(
            bot_result=bot_result,
            include_items=True,
        )
    files = []
    excluded_count = 0
    seen_paths: set[str] = set()

    for item in iter_selection_items(session):
        if item.get("locked"):
            excluded_count += 1
            continue
        if item.get("recommended_decision") != "delete_candidate":
            excluded_count += 1
            continue
        if "delete_candidate" not in item.get("allowed_decisions", []):
            excluded_count += 1
            continue

        raw_path = item.get("path")
        if not raw_path:
            excluded_count += 1
            continue
        file_path = Path(raw_path)
        try:
            is_file = file_path.is_file()
        except OSError:
            is_file = False
        if not is_file:
            excluded_count += 1
            continue

        path_key = normalize_path_key(file_path)
        if path_key in seen_paths:
            excluded_count += 1
            continue

        risk_result = classify_file_risk(file_path)
        cleanup_recommendation = get_cleanup_recommendation(risk_result)
        if (
            risk_result.get("risk") != SAFE_DELETE
            or cleanup_recommendation.get("recommended_decision") != "delete_candidate"
            or cleanup_recommendation.get("can_recommend_delete") is not True
        ):
            excluded_count += 1
            continue

        try:
            current_size = file_path.stat().st_size
        except OSError:
            excluded_count += 1
            continue

        seen_paths.add(path_key)
        files.append({
            "selection_id": item.get("selection_id"),
            "path": str(file_path),
            "name": item.get("name") or file_path.name,
            "size": current_size,
            "size_text": format_size(current_size),
            "risk": risk_result["risk"],
            "risk_category": risk_result.get("category"),
            "matched_rule": risk_result.get("matched_rule"),
            "recommended_decision": cleanup_recommendation["recommended_decision"],
            "reason_text": cleanup_recommendation["reason_text"],
        })

    total_size = sum(int(item["size"]) for item in files)
    count = len(files)
    if count:
        summary_text = (
            f"AI de nghi don {count} file rac an toan ({format_size(total_size)}). "
            "Ban van phai xem preview va xac nhan truoc khi dua vao Recycle Bin."
        )
        severity = "warning"
    else:
        summary_text = "AI chua tim thay file safe_delete nao du dieu kien don 1 cham."
        severity = "info"

    return {
        "schema": ONE_CLICK_CLEANUP_SCHEMA,
        "status": "ready" if files else "empty",
        "files": files,
        "count": count,
        "total_size": total_size,
        "total_size_text": format_size(total_size),
        "summary_text": summary_text,
        "severity": severity,
        "selection_decisions": {
            item["selection_id"]: "delete_candidate"
            for item in files
            if item.get("selection_id")
        },
        "excluded_count": excluded_count,
        "source_selection_schema": session.get("schema"),
        "safety_contract": {
            "read_only": True,
            "executes_file_operations": False,
            "only_safe_delete_files": True,
            "uses_cleanup_rule_registry": True,
            "requires_selection_decision_report": True,
            "requires_dry_run": True,
            "requires_final_delete_token": True,
            "uses_recycle_bin": True,
            "delete_enabled": False,
            "move_enabled": False,
        },
    }
