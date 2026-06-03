from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.core.assistant_logger import log_action
from tools.core.candidate_review import build_candidate_review
from tools.core.report_manager import create_report


ACTION_PLANNER_TOOL = "action_planner"


def candidate_action_to_plan_step(candidate_action: str) -> dict[str, Any]:
    mapping = {
        "keep_ignore": {
            "plan_action": "keep",
            "plan_status": "blocked_by_policy",
            "requires_user_input": False,
            "can_execute_now": False,
            "reason": "Policy says ignore/keep; do not open cleanup.",
        },
        "keep": {
            "plan_action": "keep",
            "plan_status": "kept_by_policy",
            "requires_user_input": False,
            "can_execute_now": False,
            "reason": "Policy says keep.",
        },
        "manual_review": {
            "plan_action": "manual_review",
            "plan_status": "needs_manual_choice",
            "requires_user_input": True,
            "can_execute_now": False,
            "reason": "User must choose exact keep/move/delete action.",
        },
        "backup_first": {
            "plan_action": "backup_first",
            "plan_status": "needs_backup_decision",
            "requires_user_input": True,
            "can_execute_now": False,
            "reason": "Backup/keep decision is required before cleanup.",
        },
        "move_when_destination_selected": {
            "plan_action": "move_later",
            "plan_status": "needs_destination",
            "requires_user_input": True,
            "can_execute_now": False,
            "reason": "Destination folder must be selected before moving.",
        },
        "delete_after_exact_confirm": {
            "plan_action": "delete_candidate",
            "plan_status": "needs_exact_confirm",
            "requires_user_input": True,
            "can_execute_now": False,
            "reason": "Exact file and final delete confirmation are required.",
        },
    }
    return mapping.get(candidate_action, {
        "plan_action": "review_unknown",
        "plan_status": "needs_review",
        "requires_user_input": True,
        "can_execute_now": False,
        "reason": "No safe automatic action is available.",
    })


def build_action_plan(
    *,
    source_report_path: str | Path | None = None,
    policy_file: str | Path | None = None,
    include_items: bool = True,
) -> dict[str, Any]:
    review = build_candidate_review(
        source_report_path=source_report_path,
        policy_file=policy_file,
        include_items=True,
    )
    plan_items = []
    for item in review.get("items", []):
        step = candidate_action_to_plan_step(str(item.get("candidate_action") or ""))
        plan_items.append({
            "path": item.get("path"),
            "name": item.get("name"),
            "candidate_group": item.get("candidate_group"),
            "size": item.get("size"),
            "size_text": item.get("size_text"),
            "context": item.get("context"),
            "policy_decision": item.get("policy_decision"),
            "policy_reason": item.get("policy_reason"),
            "candidate_action": item.get("candidate_action"),
            **step,
        })

    summary = {
        "total": len(plan_items),
        "can_execute_now_count": sum(1 for item in plan_items if item["can_execute_now"]),
        "requires_user_input_count": sum(1 for item in plan_items if item["requires_user_input"]),
        "blocked_by_policy_count": sum(
            1 for item in plan_items
            if item["plan_status"] in {"blocked_by_policy", "kept_by_policy"}
        ),
        "delete_candidate_count": sum(1 for item in plan_items if item["plan_action"] == "delete_candidate"),
        "move_later_count": sum(1 for item in plan_items if item["plan_action"] == "move_later"),
        "by_plan_action": {},
        "by_plan_status": {},
        "undo_available": False,
    }
    for item in plan_items:
        action = item["plan_action"]
        status = item["plan_status"]
        summary["by_plan_action"][action] = summary["by_plan_action"].get(action, 0) + 1
        summary["by_plan_status"][status] = summary["by_plan_status"].get(status, 0) + 1

    return {
        "schema": "action_plan_v1",
        "status": "success" if review["status"] == "success" else "warning",
        "source_review_status": review["status"],
        "source_report": review.get("source_report"),
        "summary": summary,
        "items": plan_items if include_items else [],
        "safety_contract": {
            "dry_run_only": True,
            "auto_delete_enabled": False,
            "auto_move_enabled": False,
            "requires_exact_user_confirmation": True,
        },
    }


def export_action_plan_report(
    *,
    source_report_path: str | Path | None = None,
    policy_file: str | Path | None = None,
) -> dict[str, Any]:
    plan = build_action_plan(
        source_report_path=source_report_path,
        policy_file=policy_file,
        include_items=True,
    )
    status = "success" if plan["status"] == "success" else "warning"
    report = create_report(
        tool_name=ACTION_PLANNER_TOOL,
        action="dry_run_plan",
        status=status,
        risk_level="safe",
        input_data={
            "source_report_path": str(source_report_path) if source_report_path else None,
            "policy_file": str(policy_file) if policy_file else None,
        },
        results=plan,
        recommendations=[
            "This plan is dry-run only and does not execute cleanup.",
            "No delete or move operation is enabled until the user chooses exact files and confirms.",
            "Use Candidate Review before changing any policy from manual_only or needs_backup.",
        ],
        summary={
            **plan["summary"],
            "source_report": plan.get("source_report"),
        },
        undo_available=False,
        tags=["action_plan", "dry_run", "read_only", "policy"],
    )
    log_action(
        ACTION_PLANNER_TOOL,
        "export_action_plan_report",
        status,
        {
            "report": str(report),
            "total": plan["summary"]["total"],
            "can_execute_now_count": plan["summary"]["can_execute_now_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "plan": plan,
    }


def print_action_plan_summary(plan: dict[str, Any]) -> None:
    summary = plan["summary"]
    print("\n========== DRY-RUN ACTION PLAN ==========")
    print(f"Status: {plan['status']}")
    print(f"Source report: {plan.get('source_report')}")
    print(f"Total: {summary['total']}")
    print(f"Can execute now: {summary['can_execute_now_count']}")
    print(f"Requires user input: {summary['requires_user_input_count']}")
    print(f"Blocked by policy: {summary['blocked_by_policy_count']}")
    print(f"Actions: {summary['by_plan_action']}")


def run_action_planner() -> None:
    while True:
        print("""
========== DRY-RUN ACTION PLANNER ==========
1. Xem action plan summary
2. Xuat dry-run action plan report
0. Thoat
""")
        choice = input("Chon: ").strip()
        if choice == "1":
            print_action_plan_summary(build_action_plan(include_items=False))
        elif choice == "2":
            export_action_plan_report()
        elif choice == "0":
            break
        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_action_planner()
