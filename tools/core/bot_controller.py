from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.core.action_planner import build_action_plan
from tools.core.action_policy import build_action_policy_health
from tools.core.assistant_logger import log_action
from tools.core.candidate_review import build_candidate_review
from tools.core.feed_readiness import build_feed_readiness_result
from tools.core.file_operation_adapter import (
    FINAL_MOVE_TOKEN,
    export_file_operation_adapter_report,
    print_operation_summary,
)
from tools.core.guided_action_runner import build_action_contexts
from tools.core.recommendation_center import (
    DEFAULT_VISIBLE_STATES,
    collect_recommendation_queue,
    summarize_recommendation_queue,
)
from tools.core.report_manager import create_report, read_recent_report_index


BOT_CONTROLLER_TOOL = "bot_controller"
BOT_DECISIONS = {"ok", "select", "move_later", "cancel", "details"}
BOT_CONTROLLER_SCHEMA = "bot_controller_v2"
BOT_SELECTION_UI_SCHEMA = "bot_selection_ui_v2"
BOT_SELECTION_DECISION_SCHEMA = "bot_selection_decision_v2"
BOT_MOVE_LATER_FLOW_SCHEMA = "bot_move_later_flow_v1"
SELECTION_DECISIONS = {
    "keep",
    "manual_review",
    "needs_backup",
    "move_later",
    "delete_candidate",
    "skip",
}
LATEST_REPORT_TOOLS = {
    "system_advisor",
    "recommendation_center",
    "action_policy",
    "candidate_review",
    "action_planner",
    "feed_readiness",
    "full_system_tester",
    "file_operation_adapter",
}


def merge_report_tags(base_tags: list[str], extra_tags: list[str] | None = None) -> list[str]:
    tags: list[str] = []
    for tag in [*base_tags, *(extra_tags or [])]:
        text = str(tag).strip()
        if text and text not in tags:
            tags.append(text)
    return tags


def safe_read_report(path: str | Path) -> dict[str, Any] | None:
    report_path = Path(path)
    if not report_path.exists():
        return None
    try:
        with report_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def latest_reports_by_tool(limit: int = 500) -> dict[str, dict[str, Any] | None]:
    latest: dict[str, dict[str, Any] | None] = {
        tool_name: None for tool_name in LATEST_REPORT_TOOLS
    }
    for record in read_recent_report_index(limit=limit):
        tool_name = str(record.get("tool") or "")
        if tool_name in latest:
            latest[tool_name] = record
    return latest


def summarize_latest_report(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    data = safe_read_report(str(record.get("report_path") or ""))
    return {
        "tool": record.get("tool"),
        "action": record.get("action"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
        "report_path": record.get("report_path"),
        "readable": data is not None,
        "summary": data.get("summary", {}) if data else {},
        "tags": data.get("tags", []) if data else [],
    }


def group_plan_items(plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    groups = {
        "safe_to_execute": [],
        "needs_selection": [],
        "do_not_touch": [],
        "review_only": [],
    }
    for item in plan.get("items", []):
        slim_item = {
            "path": item.get("path"),
            "name": item.get("name"),
            "size": item.get("size"),
            "size_text": item.get("size_text"),
            "candidate_group": item.get("candidate_group"),
            "context": item.get("context"),
            "policy_decision": item.get("policy_decision"),
            "plan_action": item.get("plan_action"),
            "plan_status": item.get("plan_status"),
            "reason": item.get("reason"),
            "can_execute_now": item.get("can_execute_now"),
            "requires_user_input": item.get("requires_user_input"),
        }
        if item.get("can_execute_now"):
            groups["safe_to_execute"].append(slim_item)
        elif item.get("plan_status") in {"blocked_by_policy", "kept_by_policy"}:
            groups["do_not_touch"].append(slim_item)
        elif item.get("requires_user_input"):
            groups["needs_selection"].append(slim_item)
        else:
            groups["review_only"].append(slim_item)
    return groups


def summarize_grouped_plan(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "safe_to_execute_count": len(groups["safe_to_execute"]),
        "needs_selection_count": len(groups["needs_selection"]),
        "do_not_touch_count": len(groups["do_not_touch"]),
        "review_only_count": len(groups["review_only"]),
    }


def count_items_allowing_decision(session: dict[str, Any], decision: str) -> int:
    count = 0
    for item in iter_selection_items(session):
        if decision in item.get("allowed_decisions", []):
            count += 1
    return count


def count_grouped_items_allowing_decision(
    groups: dict[str, list[dict[str, Any]]],
    decision: str,
) -> int:
    count = 0
    for group_name, items in groups.items():
        for item in items:
            if decision in get_allowed_selection_decisions(item, group_name):
                count += 1
    return count


def get_allowed_selection_decisions(item: dict[str, Any], group_name: str) -> list[str]:
    if group_name == "do_not_touch":
        return ["keep"]

    plan_action = str(item.get("plan_action") or "")
    mapping = {
        "keep": ["keep"],
        "manual_review": ["keep", "manual_review", "move_later", "delete_candidate", "skip"],
        "backup_first": ["keep", "needs_backup", "manual_review", "skip"],
        "move_later": ["keep", "move_later", "skip"],
        "delete_candidate": ["keep", "delete_candidate", "skip"],
        "review_unknown": ["keep", "manual_review", "skip"],
    }
    return mapping.get(plan_action, ["keep", "manual_review", "skip"])


def get_recommended_selection_decision(item: dict[str, Any], group_name: str) -> str:
    if group_name == "do_not_touch":
        return "keep"

    plan_action = str(item.get("plan_action") or "")
    mapping = {
        "manual_review": "manual_review",
        "backup_first": "needs_backup",
        "move_later": "move_later",
        "delete_candidate": "delete_candidate",
        "keep": "keep",
    }
    return mapping.get(plan_action, "manual_review")


def make_selection_item(
    item: dict[str, Any],
    *,
    selection_id: str,
    group_name: str,
) -> dict[str, Any]:
    allowed_decisions = get_allowed_selection_decisions(item, group_name)
    return {
        **item,
        "selection_id": selection_id,
        "selection_group": group_name,
        "allowed_decisions": allowed_decisions,
        "recommended_decision": get_recommended_selection_decision(item, group_name),
        "locked": group_name == "do_not_touch",
        "execution_enabled": False,
    }


def build_selection_session_from_groups(
    groups: dict[str, list[dict[str, Any]]],
    *,
    include_items: bool = True,
) -> dict[str, Any]:
    prefixes = {
        "safe_to_execute": "S",
        "needs_selection": "M",
        "do_not_touch": "D",
        "review_only": "R",
    }
    selection_groups: dict[str, list[dict[str, Any]]] = {}

    for group_name, items in groups.items():
        prefix = prefixes.get(group_name, "X")
        selection_groups[group_name] = [
            make_selection_item(
                item,
                selection_id=f"{prefix}{index:03d}",
                group_name=group_name,
            )
            for index, item in enumerate(items, start=1)
        ]

    summary = {
        "safe_to_execute_count": len(selection_groups["safe_to_execute"]),
        "needs_selection_count": len(selection_groups["needs_selection"]),
        "do_not_touch_count": len(selection_groups["do_not_touch"]),
        "review_only_count": len(selection_groups["review_only"]),
        "selectable_count": (
            len(selection_groups["safe_to_execute"])
            + len(selection_groups["needs_selection"])
            + len(selection_groups["review_only"])
        ),
        "locked_count": len(selection_groups["do_not_touch"]),
        "execution_enabled": False,
    }

    return {
        "schema": BOT_SELECTION_UI_SCHEMA,
        "status": "ready" if summary["selectable_count"] or summary["locked_count"] else "empty",
        "summary": summary,
        "groups": selection_groups if include_items else {
            key: [] for key in selection_groups
        },
        "decision_contract": {
            "valid_decisions": sorted(SELECTION_DECISIONS),
            "locked_group": "do_not_touch",
            "decision_report_only": True,
            "executes_file_operations": False,
        },
    }


def build_selection_session(
    *,
    bot_result: dict[str, Any] | None = None,
    include_items: bool = True,
) -> dict[str, Any]:
    result = bot_result or build_bot_controller_result(include_items=True)
    groups = result["action_plan"]["groups"]
    if not any(groups.values()) and (
        result["summary"]["safe_to_execute_count"] > 0
        or result["summary"]["needs_selection_count"] > 0
        or result["summary"]["do_not_touch_count"] > 0
    ):
        result = build_bot_controller_result(include_items=True)
        groups = result["action_plan"]["groups"]
    return build_selection_session_from_groups(groups, include_items=include_items)


def iter_selection_items(session: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for group_items in session.get("groups", {}).values():
        items.extend(group_items)
    return items


def build_selection_decision(
    decisions: dict[str, str],
    *,
    session: dict[str, Any] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    selection_session = session or build_selection_session(include_items=True)
    item_by_id = {
        item["selection_id"]: item
        for item in iter_selection_items(selection_session)
    }
    normalized_decisions = {
        str(selection_id).strip().upper(): str(decision).strip().lower()
        for selection_id, decision in (decisions or {}).items()
        if str(selection_id).strip()
    }

    selected = []
    skipped = []
    blocked = []
    invalid = []
    unselected = []

    for selection_id, decision in normalized_decisions.items():
        item = item_by_id.get(selection_id)
        if item is None:
            invalid.append({
                "selection_id": selection_id,
                "decision": decision,
                "reason": "Unknown selection id.",
            })
            continue

        if decision not in SELECTION_DECISIONS:
            invalid.append({
                "selection_id": selection_id,
                "path": item.get("path"),
                "decision": decision,
                "allowed_decisions": item["allowed_decisions"],
                "reason": "Unknown decision.",
            })
            continue

        if item["locked"] and decision != "keep":
            blocked.append({
                "selection_id": selection_id,
                "path": item.get("path"),
                "decision": decision,
                "allowed_decisions": item["allowed_decisions"],
                "reason": "Item is locked by policy and can only be kept.",
            })
            continue

        if decision not in item["allowed_decisions"]:
            invalid.append({
                "selection_id": selection_id,
                "path": item.get("path"),
                "decision": decision,
                "allowed_decisions": item["allowed_decisions"],
                "reason": "Decision is not allowed for this item.",
            })
            continue

        record = {
            "selection_id": selection_id,
            "path": item.get("path"),
            "name": item.get("name"),
            "size_text": item.get("size_text"),
            "selection_group": item.get("selection_group"),
            "policy_decision": item.get("policy_decision"),
            "plan_action": item.get("plan_action"),
            "decision": decision,
            "execution_enabled": False,
        }
        if decision == "skip":
            skipped.append(record)
        else:
            selected.append(record)

    explicitly_seen = set(normalized_decisions)
    for selection_id, item in item_by_id.items():
        if item["locked"] or selection_id in explicitly_seen:
            continue
        unselected.append({
            "selection_id": selection_id,
            "path": item.get("path"),
            "name": item.get("name"),
            "recommended_decision": item.get("recommended_decision"),
            "allowed_decisions": item.get("allowed_decisions"),
        })

    by_decision: dict[str, int] = {}
    for item in selected:
        decision = item["decision"]
        by_decision[decision] = by_decision.get(decision, 0) + 1

    status = "ready"
    if invalid or blocked:
        status = "needs_fix"
    elif not selected and not skipped:
        status = "empty_selection"

    return {
        "schema": BOT_SELECTION_DECISION_SCHEMA,
        "status": status,
        "summary": {
            "input_decision_count": len(normalized_decisions),
            "selected_count": len(selected),
            "skipped_count": len(skipped),
            "blocked_count": len(blocked),
            "invalid_count": len(invalid),
            "unselected_count": len(unselected),
            "by_decision": by_decision,
            "execution_enabled": False,
            "undo_available": False,
        },
        "note": note,
        "selected": selected,
        "skipped": skipped,
        "blocked": blocked,
        "invalid": invalid,
        "unselected": unselected,
        "selection_session_summary": selection_session["summary"],
        "safety_contract": {
            "decision_report_only": True,
            "executes_file_operations": False,
            "requires_execution_adapter": True,
            "requires_manifest_for_move": True,
            "delete_candidate_is_not_delete": True,
        },
    }


def export_selection_decision_report(
    decisions: dict[str, str],
    *,
    session: dict[str, Any] | None = None,
    note: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    decision_report = build_selection_decision(decisions, session=session, note=note)
    status = "success" if decision_report["status"] != "needs_fix" else "warning"
    report = create_report(
        tool_name=BOT_CONTROLLER_TOOL,
        action="export_selection_decision",
        status=status,
        risk_level="safe",
        input_data={
            "decision_count": len(decisions or {}),
            "note": note,
        },
        results=decision_report,
        recommendations=[
            "This is a decision report only; it does not delete or move files.",
            "Blocked or invalid items must be fixed before any future execution adapter can use them.",
            "delete_candidate means user intent only, not immediate deletion.",
        ],
        summary=decision_report["summary"],
        undo_available=False,
        tags=merge_report_tags(
            ["bot_controller", "selection", "decision_report", "read_only"],
            extra_tags,
        ),
    )
    log_action(
        BOT_CONTROLLER_TOOL,
        "export_selection_decision_report",
        status,
        {
            "report": str(report),
            "selected_count": decision_report["summary"]["selected_count"],
            "invalid_count": decision_report["summary"]["invalid_count"],
            "blocked_count": decision_report["summary"]["blocked_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "decision": decision_report,
    }


def summarize_move_later_flow(
    decision_export: dict[str, Any],
    operation_export: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = decision_export.get("decision", {})
    decision_summary = decision.get("summary", {}) if isinstance(decision, dict) else {}
    operation = operation_export.get("operation", {}) if isinstance(operation_export, dict) else {}
    operation_summary = operation.get("summary", {}) if isinstance(operation, dict) else {}

    return {
        "decision_report": decision_export.get("report"),
        "operation_report": operation_export.get("report") if operation_export else None,
        "selection_status": decision.get("status"),
        "selected_count": decision_summary.get("selected_count", 0),
        "blocked_count": decision_summary.get("blocked_count", 0),
        "invalid_count": decision_summary.get("invalid_count", 0),
        "move_requested_count": operation_summary.get("move_requested_count", 0),
        "movable_count": operation_summary.get("movable_count", 0),
        "moved_count": operation_summary.get("moved_count", 0),
        "operation_blocked_count": operation_summary.get("blocked_count", 0),
        "operation_error_count": operation_summary.get("error_count", 0),
        "file_operations_executed": operation_summary.get("file_operations_executed", False),
        "manifest": operation.get("manifest") or operation_summary.get("manifest"),
        "undo_available": bool(operation.get("undo_available") or operation_summary.get("undo_available")),
    }


def export_move_later_selection_flow_report(
    decisions: dict[str, str],
    *,
    destination_root: str | Path,
    mode: str = "dry_run",
    final_token: str | None = None,
    session: dict[str, Any] | None = None,
    note: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    decision_export = export_selection_decision_report(
        decisions,
        session=session,
        note=note,
        extra_tags=extra_tags,
    )
    decision = decision_export["decision"]
    operation_export: dict[str, Any] | None = None

    if decision["status"] == "ready":
        operation_export = export_file_operation_adapter_report(
            source_report_path=decision_export["report"],
            destination_root=destination_root,
            mode=mode,
            final_token=final_token,
            extra_tags=extra_tags,
        )

    summary = summarize_move_later_flow(decision_export, operation_export)
    if decision["status"] != "ready":
        flow_status = "decision_report_not_ready"
    elif operation_export:
        flow_status = operation_export["operation"]["status"]
    else:
        flow_status = "operation_not_started"

    report_status = "success"
    if flow_status in {"decision_report_not_ready", "destination_invalid", "requires_final_confirmation"}:
        report_status = "warning"
    elif flow_status in {"completed_with_errors", "invalid_decision_report", "missing_source_report"}:
        report_status = "error"

    result = {
        "schema": BOT_MOVE_LATER_FLOW_SCHEMA,
        "status": flow_status,
        "mode": str(mode or "dry_run").strip().lower(),
        "destination_root": str(destination_root),
        "decision_report": decision_export,
        "operation_report": operation_export,
        "summary": summary,
        "safety_contract": {
            "requires_selection_decision": True,
            "requires_destination_root": True,
            "requires_final_move_token": True,
            "final_move_token": FINAL_MOVE_TOKEN,
            "file_operations_limited_to_move_later": True,
            "delete_enabled": False,
            "uses_file_operation_adapter": True,
            "undo_strategy": "manifest_restore",
        },
    }

    report = create_report(
        tool_name=BOT_CONTROLLER_TOOL,
        action="move_later_selection_flow",
        status=report_status,
        risk_level="medium",
        input_data={
            "decision_count": len(decisions or {}),
            "destination_root": str(destination_root),
            "mode": mode,
            "final_token_provided": bool(final_token),
            "note": note,
        },
        results=result,
        recommendations=[
            "This flow only moves items explicitly selected as move_later.",
            "Review the File Operation Adapter report before trusting any move result.",
            "Use Undo Manager with the manifest if moved files need to be restored.",
            "delete_candidate remains disabled.",
        ],
        summary=summary,
        manifest=summary.get("manifest"),
        undo_available=summary.get("undo_available", False),
        tags=merge_report_tags(
            ["bot_controller", "move_later_flow", "file_operation_adapter", "selection_ui_v2"],
            extra_tags,
        ),
    )
    log_action(
        BOT_CONTROLLER_TOOL,
        "export_move_later_selection_flow_report",
        report_status,
        {
            "report": str(report),
            "flow_status": flow_status,
            "decision_report": decision_export.get("report"),
            "operation_report": operation_export.get("report") if operation_export else None,
            "manifest": summary.get("manifest"),
            "file_operations_executed": summary["file_operations_executed"],
        },
    )
    print(f"Bot flow report: {report}")

    return {
        "status": report_status,
        "report": str(report),
        "flow": result,
    }


def summarize_guided_contexts(contexts: list[dict[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_policy: dict[str, int] = {}
    for context in contexts:
        status = str(context.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        policy = (context.get("policy_gate") or {}).get("decision") or "none"
        by_policy[policy] = by_policy.get(policy, 0) + 1
    return {
        "total": len(contexts),
        "ready_count": by_status.get("ready", 0),
        "blocked_count": len(contexts) - by_status.get("ready", 0),
        "by_status": by_status,
        "by_policy": by_policy,
    }


def build_bot_controller_result(
    *,
    include_items: bool = True,
    report_limit: int = 120,
) -> dict[str, Any]:
    queue = collect_recommendation_queue(
        report_limit=report_limit,
        states=DEFAULT_VISIBLE_STATES,
    )
    all_queue = collect_recommendation_queue(
        report_limit=report_limit,
        states=None,
    )
    contexts = build_action_contexts(queue)
    candidate_review = build_candidate_review(include_items=include_items)
    action_plan = build_action_plan(include_items=True)
    grouped_plan = group_plan_items(action_plan)
    group_summary = summarize_grouped_plan(grouped_plan)
    selection_ui = build_selection_session_from_groups(
        grouped_plan,
        include_items=include_items,
    )
    move_later_selectable_count = count_grouped_items_allowing_decision(grouped_plan, "move_later")
    readiness = build_feed_readiness_result()
    action_policy = build_action_policy_health()
    latest_reports = {
        tool_name: summarize_latest_report(record)
        for tool_name, record in latest_reports_by_tool().items()
    }

    decision_screen = {
        "ok": {
            "label": "OK - run safe-only actions",
            "enabled": group_summary["safe_to_execute_count"] > 0,
            "effect": (
                "Execute only items already marked can_execute_now."
                if group_summary["safe_to_execute_count"] > 0
                else "No safe executable item is currently available."
            ),
        },
        "select": {
            "label": "Lua chon - review files manually",
            "enabled": group_summary["needs_selection_count"] > 0,
            "effect": "Open/review candidate list before any action.",
        },
        "move_later": {
            "label": "Move selected move_later items",
            "enabled": move_later_selectable_count > 0,
            "effect": "Create a selection decision report, require a destination, then use File Operation Adapter.",
        },
        "cancel": {
            "label": "Huy - do nothing",
            "enabled": True,
            "effect": "No file operation will run.",
        },
        "details": {
            "label": "Xem chi tiet",
            "enabled": True,
            "effect": "Show reports and grouped plan details.",
        },
    }

    status = "ready"
    if readiness["summary"]["fail_count"] > 0:
        status = "needs_attention"
    elif not queue and not action_plan.get("items"):
        status = "no_current_actions"

    return {
        "schema": BOT_CONTROLLER_SCHEMA,
        "status": status,
        "mode": "latest_reports_orchestrator",
        "summary": {
            "visible_recommendation_count": len(queue),
            "all_recommendation_count": len(all_queue),
            "safe_to_execute_count": group_summary["safe_to_execute_count"],
            "needs_selection_count": group_summary["needs_selection_count"],
            "do_not_touch_count": group_summary["do_not_touch_count"],
            "move_later_selectable_count": move_later_selectable_count,
            "candidate_count": candidate_review["summary"]["total"],
            "policy_count": action_policy["summary"]["total"],
            "readiness_status": readiness["summary"]["readiness_status"],
            "undo_available": False,
        },
        "decision_screen": decision_screen,
        "recommendation_queue": {
            "summary": summarize_recommendation_queue(all_queue),
            "visible_items": queue,
        },
        "guided_actions": {
            "summary": summarize_guided_contexts(contexts),
            "contexts": contexts if include_items else [],
        },
        "candidate_review": {
            "summary": candidate_review["summary"],
            "source_report": candidate_review.get("source_report"),
            "items": candidate_review.get("items", []) if include_items else [],
        },
        "action_plan": {
            "summary": action_plan["summary"],
            "source_report": action_plan.get("source_report"),
            "groups": grouped_plan if include_items else {
                key: [] for key in grouped_plan
            },
            "safety_contract": action_plan["safety_contract"],
        },
        "selection_ui": selection_ui,
        "action_policy": action_policy,
        "feed_readiness": {
            "summary": readiness["summary"],
            "checks": [
                {
                    "id": item["id"],
                    "status": item["status"],
                    "title": item["title"],
                    "detail": item["detail"],
                }
                for item in readiness["checks"]
            ],
        },
        "latest_reports": latest_reports,
        "safety_contract": {
            "bot_autonomy": "scan_and_plan_only_v1",
            "executes_file_operations": False,
            "safe_ok_requires_can_execute_now": True,
            "selection_required_for_manual_items": True,
            "selection_ui_schema": BOT_SELECTION_UI_SCHEMA,
            "selection_decision_schema": BOT_SELECTION_DECISION_SCHEMA,
            "selection_report_only": True,
            "move_later_uses_file_operation_adapter": True,
            "delete_candidate_enabled": False,
            "never_touch_policy_decisions": ["ignore_forever", "keep"],
        },
    }


def execute_bot_decision(
    decision: str,
    *,
    bot_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = str(decision or "").strip().lower()
    if decision not in BOT_DECISIONS:
        return {
            "status": "invalid_decision",
            "executed": False,
            "decision": decision,
        }

    result = bot_result or build_bot_controller_result(include_items=True)
    if decision in {"ok", "select"} and not any(
        result["action_plan"]["groups"].values()
    ) and (
        result["summary"]["safe_to_execute_count"] > 0
        or result["summary"]["needs_selection_count"] > 0
    ):
        result = build_bot_controller_result(include_items=True)
    safe_items = result["action_plan"]["groups"]["safe_to_execute"]

    if decision == "cancel":
        return {
            "status": "cancelled",
            "executed": False,
            "decision": decision,
            "message": "User cancelled; no action executed.",
        }

    if decision == "details":
        return {
            "status": "details_only",
            "executed": False,
            "decision": decision,
            "summary": result["summary"],
            "reports": result["latest_reports"],
        }

    if decision == "select":
        selection_session = build_selection_session(bot_result=result, include_items=True)
        return {
            "status": "selection_required",
            "executed": False,
            "decision": decision,
            "selection_ui": selection_session,
            "message": "Selection UI is ready; export a decision report before any future execution.",
        }

    if decision == "move_later":
        selection_session = build_selection_session(bot_result=result, include_items=True)
        return {
            "status": "move_later_selection_required",
            "executed": False,
            "decision": decision,
            "selection_ui": selection_session,
            "final_move_token": FINAL_MOVE_TOKEN,
            "message": "Select move_later items and destination, then File Operation Adapter will dry-run before apply.",
        }

    if decision == "ok":
        if not safe_items:
            return {
                "status": "no_safe_actions",
                "executed": False,
                "decision": decision,
                "message": "No item is marked can_execute_now, so Bot Controller did not run cleanup.",
            }
        return {
            "status": "execution_not_enabled_v1",
            "executed": False,
            "decision": decision,
            "safe_item_count": len(safe_items),
            "message": "Bot Controller v2 found safe items but execution is not enabled in this milestone.",
        }

    return {
        "status": "unhandled_decision",
        "executed": False,
        "decision": decision,
    }


def export_bot_controller_report(*, include_items: bool = True) -> dict[str, Any]:
    result = build_bot_controller_result(include_items=include_items)
    status = "success" if result["status"] in {"ready", "no_current_actions"} else "warning"
    report = create_report(
        tool_name=BOT_CONTROLLER_TOOL,
        action="auto_check_system",
        status=status,
        risk_level="safe",
        input_data={
            "include_items": include_items,
            "mode": result["mode"],
        },
        results=result,
        recommendations=[
            "Bot Controller v2 scans, plans and exports selection decisions, but does not execute cleanup automatically.",
            "Use OK only when safe_to_execute_count is greater than zero.",
            "Use selection flow to create a decision report for manual_only, needs_backup and move_later items.",
        ],
        summary=result["summary"],
        undo_available=False,
        tags=["bot_controller", "auto_check", "orchestrator", "read_only", "selection_ui_v2"],
    )
    log_action(
        BOT_CONTROLLER_TOOL,
        "export_bot_controller_report",
        status,
        {
            "report": str(report),
            "safe_to_execute_count": result["summary"]["safe_to_execute_count"],
            "needs_selection_count": result["summary"]["needs_selection_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "bot": result,
    }


def print_bot_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== AI BOT CONTROLLER V2 ==========")
    print(f"Status: {result['status']}")
    print(f"Recommendations: {summary['visible_recommendation_count']} visible / {summary['all_recommendation_count']} total")
    print(f"Safe to execute: {summary['safe_to_execute_count']}")
    print(f"Need selection: {summary['needs_selection_count']}")
    print(f"Move-later selectable: {summary['move_later_selectable_count']}")
    print(f"Do not touch: {summary['do_not_touch_count']}")
    print(f"Candidates: {summary['candidate_count']}")
    print(f"Readiness: {summary['readiness_status']}")
    print(f"Selection UI: {result['selection_ui']['schema']}")
    print("\nDecisions:")
    for key, item in result["decision_screen"].items():
        enabled = "enabled" if item["enabled"] else "disabled"
        print(f"- {key}: {item['label']} [{enabled}]")


def print_selection_session(session: dict[str, Any], *, limit: int = 80) -> None:
    print("\n========== SELECTION UI V2 ==========")
    summary = session["summary"]
    print(f"Selectable: {summary['selectable_count']}")
    print(f"Needs selection: {summary['needs_selection_count']}")
    print(f"Locked/do not touch: {summary['locked_count']}")
    print("Allowed input example: M001=keep, M002=move_later, M003=delete_candidate")

    shown = 0
    for group_name, items in session["groups"].items():
        if not items:
            continue
        print(f"\n[{group_name}]")
        for item in items:
            shown += 1
            locked = " locked" if item["locked"] else ""
            allowed = "/".join(item["allowed_decisions"])
            print(
                f"{item['selection_id']}{locked} | {item.get('size_text') or '-'} | "
                f"{item.get('plan_action')} | {item.get('path')}"
            )
            print(f"  allowed: {allowed}; recommended: {item['recommended_decision']}")
            if shown >= limit:
                print(f"... truncated at {limit} items")
                return


def parse_selection_input(raw_text: str) -> dict[str, str]:
    decisions: dict[str, str] = {}
    for chunk in raw_text.replace(";", ",").split(","):
        part = chunk.strip()
        if not part:
            continue
        if "=" not in part:
            continue
        selection_id, decision = part.split("=", 1)
        selection_id = selection_id.strip().upper()
        decision = decision.strip().lower()
        if selection_id:
            decisions[selection_id] = decision
    return decisions


def run_bot_controller() -> None:
    while True:
        print("""
========== AI BOT CONTROLLER V2 ==========
1. Auto check summary
2. Export bot report
3. OK - run safe-only decision
4. Preview selection UI v2
5. Export selection decision report
6. Move selected move_later with destination
7. Huy - cancel decision
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_bot_summary(build_bot_controller_result(include_items=False))

        elif choice == "2":
            export_bot_controller_report(include_items=True)

        elif choice == "3":
            decision = execute_bot_decision("ok")
            print(decision)

        elif choice == "4":
            decision = execute_bot_decision("select")
            print_selection_session(decision["selection_ui"])

        elif choice == "5":
            session = build_selection_session(include_items=True)
            print_selection_session(session)
            raw_text = input("Nhap decision (vd M001=keep, M002=move_later), bo trong neu chua chon: ").strip()
            decisions = parse_selection_input(raw_text)
            note = input("Ghi chu report (bo trong neu khong co): ").strip() or None
            export_selection_decision_report(decisions, session=session, note=note)

        elif choice == "6":
            session = build_selection_session(include_items=True)
            print_selection_session(session)
            raw_text = input("Nhap item can move (vd M001=move_later): ").strip()
            decisions = parse_selection_input(raw_text)
            destination = input("Nhap folder dich da ton tai: ").strip().strip('"')
            note = input("Ghi chu report (bo trong neu khong co): ").strip() or None

            dry_run = export_move_later_selection_flow_report(
                decisions,
                destination_root=destination,
                mode="dry_run",
                session=session,
                note=note,
            )
            operation_report = dry_run["flow"].get("operation_report")
            if operation_report:
                print_operation_summary(operation_report["operation"])

            if dry_run["flow"]["summary"].get("movable_count", 0) <= 0:
                print("Khong co item nao san sang move.")
                continue

            print(f"Final move token required: {FINAL_MOVE_TOKEN}")
            token = input("Nhap final move token de apply, bo trong de huy: ").strip()
            if not token:
                print("Da huy apply move.")
                continue

            applied = export_move_later_selection_flow_report(
                decisions,
                destination_root=destination,
                mode="apply",
                final_token=token,
                session=session,
                note=note,
            )
            applied_operation = applied["flow"].get("operation_report")
            if applied_operation:
                print_operation_summary(applied_operation["operation"])

        elif choice == "7":
            decision = execute_bot_decision("cancel")
            print(decision)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_bot_controller()
