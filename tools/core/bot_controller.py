from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.core.action_planner import build_action_plan
from tools.core.action_policy import build_action_policy_health
from tools.core.assistant_logger import log_action
from tools.core.candidate_review import build_candidate_review
from tools.core.feed_readiness import build_feed_readiness_result
from tools.core.guided_action_runner import build_action_contexts
from tools.core.recommendation_center import (
    DEFAULT_VISIBLE_STATES,
    collect_recommendation_queue,
    summarize_recommendation_queue,
)
from tools.core.report_manager import create_report, read_recent_report_index


BOT_CONTROLLER_TOOL = "bot_controller"
BOT_DECISIONS = {"ok", "select", "cancel", "details"}
LATEST_REPORT_TOOLS = {
    "system_advisor",
    "recommendation_center",
    "action_policy",
    "candidate_review",
    "action_planner",
    "feed_readiness",
    "full_system_tester",
}


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
        "schema": "bot_controller_v1",
        "status": status,
        "mode": "latest_reports_orchestrator",
        "summary": {
            "visible_recommendation_count": len(queue),
            "all_recommendation_count": len(all_queue),
            "safe_to_execute_count": group_summary["safe_to_execute_count"],
            "needs_selection_count": group_summary["needs_selection_count"],
            "do_not_touch_count": group_summary["do_not_touch_count"],
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
        return {
            "status": "selection_required",
            "executed": False,
            "decision": decision,
            "items": result["action_plan"]["groups"]["needs_selection"],
            "message": "Manual selection UI is not implemented yet; use Candidate Review report for now.",
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
            "message": "Bot Controller v1 found safe items but execution is not enabled in this milestone.",
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
            "Bot Controller v1 scans and plans, but does not execute cleanup automatically.",
            "Use OK only when safe_to_execute_count is greater than zero.",
            "Use selection flow for manual_only, needs_backup and move_later items.",
        ],
        summary=result["summary"],
        undo_available=False,
        tags=["bot_controller", "auto_check", "orchestrator", "read_only"],
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
    print("\n========== AI BOT CONTROLLER V1 ==========")
    print(f"Status: {result['status']}")
    print(f"Recommendations: {summary['visible_recommendation_count']} visible / {summary['all_recommendation_count']} total")
    print(f"Safe to execute: {summary['safe_to_execute_count']}")
    print(f"Need selection: {summary['needs_selection_count']}")
    print(f"Do not touch: {summary['do_not_touch_count']}")
    print(f"Candidates: {summary['candidate_count']}")
    print(f"Readiness: {summary['readiness_status']}")
    print("\nDecisions:")
    for key, item in result["decision_screen"].items():
        enabled = "enabled" if item["enabled"] else "disabled"
        print(f"- {key}: {item['label']} [{enabled}]")


def run_bot_controller() -> None:
    while True:
        print("""
========== AI BOT CONTROLLER V1 ==========
1. Auto check summary
2. Export bot report
3. OK - run safe-only decision
4. Lua chon - show manual selection result
5. Huy - cancel decision
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
            print(decision)

        elif choice == "5":
            decision = execute_bot_decision("cancel")
            print(decision)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_bot_controller()
