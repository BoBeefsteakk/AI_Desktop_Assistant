from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.core.action_policy import (
    classify_path_context,
    get_primary_policy_for_path,
)
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report, read_recent_report_index


CANDIDATE_REVIEW_TOOL = "candidate_review"


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


def get_latest_step3_report(limit: int = 500) -> dict[str, Any] | None:
    records = read_recent_report_index(limit=limit)
    for record in reversed(records):
        if record.get("tool") == "step3_deferred_storage_review":
            return record
    return None


def load_step3_report(source_report_path: str | Path | None = None) -> tuple[dict[str, Any] | None, str | None]:
    if source_report_path:
        report = safe_read_report(source_report_path)
        return report, str(source_report_path)

    latest = get_latest_step3_report()
    if latest is None:
        return None, None

    path = latest.get("report_path")
    if not path:
        return None, None
    return safe_read_report(path), str(path)


def policy_decision_to_candidate_action(decision: str | None) -> str:
    return {
        "ignore_forever": "keep_ignore",
        "keep": "keep",
        "manual_only": "manual_review",
        "needs_backup": "backup_first",
        "move_later": "move_when_destination_selected",
        "delete_candidate": "delete_after_exact_confirm",
    }.get(str(decision or ""), "review_unknown")


def extract_step3_items(report_data: dict[str, Any]) -> list[dict[str, Any]]:
    results = report_data.get("results", {})
    if not isinstance(results, dict):
        return []

    groups = [
        ("archive", results.get("archive_review", {})),
        ("video", results.get("video_review", {})),
    ]
    items: list[dict[str, Any]] = []
    for group_name, group_data in groups:
        if not isinstance(group_data, dict):
            continue
        for raw_item in group_data.get("items", []) or []:
            if isinstance(raw_item, dict) and raw_item.get("path"):
                items.append({
                    **raw_item,
                    "candidate_group": group_name,
                })
    return items


def build_candidate_review(
    *,
    source_report_path: str | Path | None = None,
    policy_file: str | Path | None = None,
    include_items: bool = True,
) -> dict[str, Any]:
    report_data, report_path = load_step3_report(source_report_path)
    if report_data is None:
        return {
            "schema": "candidate_review_v1",
            "status": "missing_source_report",
            "source_report": report_path,
            "summary": {
                "total": 0,
                "covered_by_policy_count": 0,
                "uncovered_count": 0,
                "blocked_by_policy_count": 0,
                "manual_review_count": 0,
                "undo_available": False,
            },
            "items": [],
        }

    reviewed_items = []
    for item in extract_step3_items(report_data):
        path = item["path"]
        policy = get_primary_policy_for_path(path, policy_file=policy_file)
        decision = policy.get("decision") if policy else None
        candidate_action = policy_decision_to_candidate_action(decision)
        reviewed_items.append({
            "candidate_group": item.get("candidate_group"),
            "path": path,
            "name": item.get("name"),
            "extension": item.get("extension"),
            "size": item.get("size"),
            "size_text": item.get("size_text"),
            "exists": item.get("exists"),
            "risk": item.get("risk"),
            "risk_category": item.get("risk_category"),
            "context": item.get("context") or classify_path_context(path),
            "source_decision": item.get("decision"),
            "policy_decision": decision,
            "policy_id": policy.get("fingerprint") if policy else None,
            "policy_reason": policy.get("reason") if policy else None,
            "candidate_action": candidate_action,
            "requires_user_decision": candidate_action in {
                "manual_review",
                "backup_first",
                "move_when_destination_selected",
                "delete_after_exact_confirm",
                "review_unknown",
            },
            "can_auto_execute": False,
        })

    summary = {
        "total": len(reviewed_items),
        "covered_by_policy_count": sum(1 for item in reviewed_items if item["policy_decision"]),
        "uncovered_count": sum(1 for item in reviewed_items if not item["policy_decision"]),
        "blocked_by_policy_count": sum(
            1 for item in reviewed_items
            if item["policy_decision"] in {"ignore_forever", "keep"}
        ),
        "manual_review_count": sum(
            1 for item in reviewed_items
            if item["candidate_action"] in {"manual_review", "backup_first", "review_unknown"}
        ),
        "auto_execute_count": sum(1 for item in reviewed_items if item["can_auto_execute"]),
        "by_group": {},
        "by_policy_decision": {},
        "by_candidate_action": {},
        "undo_available": False,
    }
    for item in reviewed_items:
        group = item["candidate_group"] or "unknown"
        decision = item["policy_decision"] or "none"
        action = item["candidate_action"]
        summary["by_group"][group] = summary["by_group"].get(group, 0) + 1
        summary["by_policy_decision"][decision] = summary["by_policy_decision"].get(decision, 0) + 1
        summary["by_candidate_action"][action] = summary["by_candidate_action"].get(action, 0) + 1

    return {
        "schema": "candidate_review_v1",
        "status": "success",
        "source_report": report_path,
        "source_summary": report_data.get("summary", {}),
        "summary": summary,
        "items": reviewed_items if include_items else [],
    }


def export_candidate_review_report(
    *,
    source_report_path: str | Path | None = None,
    policy_file: str | Path | None = None,
) -> dict[str, Any]:
    review = build_candidate_review(
        source_report_path=source_report_path,
        policy_file=policy_file,
        include_items=True,
    )
    status = "success" if review["status"] == "success" else "warning"
    report = create_report(
        tool_name=CANDIDATE_REVIEW_TOOL,
        action="export_candidate_review",
        status=status,
        risk_level="safe",
        input_data={
            "source_report_path": str(source_report_path) if source_report_path else None,
            "policy_file": str(policy_file) if policy_file else None,
        },
        results=review,
        recommendations=[
            "Candidate Review is read-only and does not execute cleanup.",
            "Items with manual_only, needs_backup or move_later require user decision before action.",
            "Items with ignore_forever should stay blocked from cleanup automation.",
        ],
        summary={
            **review["summary"],
            "source_report": review.get("source_report"),
        },
        undo_available=False,
        tags=["candidate_review", "read_only", "policy", "step3"],
    )
    log_action(
        CANDIDATE_REVIEW_TOOL,
        "export_candidate_review_report",
        status,
        {
            "report": str(report),
            "total": review["summary"]["total"],
            "uncovered_count": review["summary"]["uncovered_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "review": review,
    }


def print_candidate_review_summary(review: dict[str, Any]) -> None:
    summary = review["summary"]
    print("\n========== CANDIDATE REVIEW ==========")
    print(f"Status: {review['status']}")
    print(f"Source report: {review.get('source_report')}")
    print(f"Total: {summary['total']}")
    print(f"Covered by policy: {summary['covered_by_policy_count']}")
    print(f"Uncovered: {summary['uncovered_count']}")
    print(f"Auto execute: {summary['auto_execute_count']}")
    print(f"Actions: {summary.get('by_candidate_action', {})}")


def run_candidate_review() -> None:
    while True:
        print("""
========== CANDIDATE REVIEW ==========
1. Xem summary read-only
2. Xuat candidate review report
0. Thoat
""")
        choice = input("Chon: ").strip()
        if choice == "1":
            print_candidate_review_summary(build_candidate_review(include_items=False))
        elif choice == "2":
            export_candidate_review_report()
        elif choice == "0":
            break
        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_candidate_review()
