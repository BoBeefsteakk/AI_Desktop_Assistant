from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.core.assistant_logger import log_action
from tools.core.auto_scan_session import AUTO_SCAN_SESSION_SCHEMA, build_auto_scan_session_result
from tools.core.report_manager import create_report, read_recent_report_index
from tools.core.risk_classifier import PROTECTED, SAFE_DELETE, classify_file_risk
from tools.core.safety_utils import format_size
from tools.storage.system_advisor import (
    ARCHIVE_EXTENSIONS,
    INSTALLER_EXTENSIONS,
    PROJECT_EXTENSIONS,
    VIDEO_EXTENSIONS,
)


ISSUE_CLASSIFIER_TOOL = "issue_classifier"
ISSUE_CLASSIFIER_SCHEMA = "issue_classifier_v1"
ACTION_GROUPS = ("safe_to_execute", "needs_selection", "do_not_touch", "review_only")


def safe_read_json(path: str | Path) -> dict[str, Any] | None:
    report_path = Path(path)
    if not report_path.exists():
        return None
    try:
        with report_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def get_latest_auto_scan_report(limit: int = 500) -> dict[str, Any] | None:
    for record in reversed(read_recent_report_index(limit=limit)):
        if record.get("tool") == "auto_scan_session":
            return record
    return None


def load_auto_scan_result(
    source_report_path: str | Path | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    if source_report_path:
        report_data = safe_read_json(source_report_path)
        payload = report_data.get("results") if isinstance(report_data, dict) else None
        return payload if isinstance(payload, dict) else None, str(source_report_path)

    latest = get_latest_auto_scan_report()
    if latest is None:
        return None, None

    report_path = latest.get("report_path")
    if not report_path:
        return None, None

    report_data = safe_read_json(report_path)
    payload = report_data.get("results") if isinstance(report_data, dict) else None
    return payload if isinstance(payload, dict) else None, str(report_path)


def make_issue(
    *,
    index: int,
    severity: str,
    category: str,
    title: str,
    detail: str,
    source: str,
    path: str | None = None,
    name: str | None = None,
    size: int | None = None,
    risk: str | None = None,
    risk_category: str | None = None,
    matched_rule: str | None = None,
    recommended_decision: str = "manual_review",
    plan_action: str = "manual_review",
    plan_status: str = "requires_user_input",
    requires_user_input: bool = True,
    can_execute_now: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "issue_id": f"I{index:04d}",
        "severity": severity,
        "category": category,
        "title": title,
        "detail": detail,
        "source": source,
        "path": path,
        "name": name or (Path(path).name if path else None),
        "size": size,
        "size_text": format_size(size or 0) if size else None,
        "risk": risk,
        "risk_category": risk_category,
        "matched_rule": matched_rule,
        "recommended_decision": recommended_decision,
        "policy_decision": recommended_decision,
        "plan_action": plan_action,
        "plan_status": plan_status,
        "requires_user_input": requires_user_input,
        "can_execute_now": can_execute_now,
        "reason": reason or detail,
    }


def classify_large_file(file_item: dict[str, Any], *, index: int) -> dict[str, Any]:
    path = str(file_item.get("path") or "")
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    size = int(file_item.get("size") or 0)
    risk = classify_file_risk(path)

    if risk["risk"] == PROTECTED:
        return make_issue(
            index=index,
            severity="info",
            category="protected_file",
            title="File lon nam trong vung bao ve",
            detail="File nay khong duoc dua vao luong xoa/move tu dong.",
            source=file_item.get("source", "storage"),
            path=path,
            size=size,
            risk=risk["risk"],
            risk_category=risk["category"],
            matched_rule=risk["matched_rule"],
            recommended_decision="keep",
            plan_action="keep",
            plan_status="blocked_by_policy",
            requires_user_input=False,
            reason=risk["reason"],
        )

    if risk["risk"] == SAFE_DELETE:
        return make_issue(
            index=index,
            severity="warning",
            category="safe_delete_candidate",
            title="File co the xoa an toan neu ban chon ro",
            detail="Risk classifier danh dau safe_delete, nhung adapter van can selection va token.",
            source=file_item.get("source", "storage"),
            path=path,
            size=size,
            risk=risk["risk"],
            risk_category=risk["category"],
            matched_rule=risk["matched_rule"],
            recommended_decision="delete_candidate",
            plan_action="delete_candidate",
            plan_status="requires_user_input",
            requires_user_input=True,
            reason=risk["reason"],
        )

    if suffix in PROJECT_EXTENSIONS:
        return make_issue(
            index=index,
            severity="warning",
            category="large_project_file",
            title="File project/editing lon",
            detail="Nen backup hoac review ky, khong xoa truc tiep.",
            source=file_item.get("source", "storage"),
            path=path,
            size=size,
            risk=risk["risk"],
            risk_category=risk["category"],
            matched_rule=risk["matched_rule"],
            recommended_decision="needs_backup",
            plan_action="backup_first",
            plan_status="requires_user_input",
            requires_user_input=True,
            reason=risk["reason"],
        )

    if suffix in VIDEO_EXTENSIONS:
        return make_issue(
            index=index,
            severity="info",
            category="large_video_file",
            title="Video lon co the gom/chuyen sau",
            detail="Phu hop voi move_later neu ban muon gom media sang folder/drive rieng.",
            source=file_item.get("source", "storage"),
            path=path,
            size=size,
            risk=risk["risk"],
            risk_category=risk["category"],
            matched_rule=risk["matched_rule"],
            recommended_decision="move_later",
            plan_action="move_later",
            plan_status="requires_user_input",
            requires_user_input=True,
            reason=risk["reason"],
        )

    if suffix in ARCHIVE_EXTENSIONS or suffix in INSTALLER_EXTENSIONS:
        return make_issue(
            index=index,
            severity="warning",
            category="large_archive_or_installer",
            title="File nen/bo cai lon can review",
            detail="Chi xoa khi ban chac da giai nen/cai xong hoac da backup.",
            source=file_item.get("source", "storage"),
            path=path,
            size=size,
            risk=risk["risk"],
            risk_category=risk["category"],
            matched_rule=risk["matched_rule"],
            recommended_decision="manual_review",
            plan_action="manual_review",
            plan_status="requires_user_input",
            requires_user_input=True,
            reason=risk["reason"],
        )

    return make_issue(
        index=index,
        severity="info",
        category="large_file_review",
        title="File lon can review",
        detail="Chua du du kien de xoa tu dong; dua vao danh sach review.",
        source=file_item.get("source", "storage"),
        path=path,
        size=size,
        risk=risk["risk"],
        risk_category=risk["category"],
        matched_rule=risk["matched_rule"],
        recommended_decision="manual_review",
        plan_action="manual_review",
        plan_status="requires_user_input",
        requires_user_input=True,
        reason=risk["reason"],
    )


def build_issues(auto_scan: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    next_index = 1
    snapshot = auto_scan.get("snapshot", {})
    advisor = auto_scan.get("advisor", {})

    for recommendation in advisor.get("recommendations", []):
        severity = str(recommendation.get("severity") or "info")
        suggested_tool = recommendation.get("suggested_tool_id")
        issues.append(make_issue(
            index=next_index,
            severity=severity,
            category=f"recommendation:{recommendation.get('source') or 'advisor'}",
            title=str(recommendation.get("title") or "Recommendation"),
            detail=str(recommendation.get("detail") or ""),
            source=str(recommendation.get("source") or "system_advisor"),
            recommended_decision="manual_review",
            plan_action="manual_review" if suggested_tool else "review_unknown",
            plan_status="requires_user_input",
            requires_user_input=True,
            reason=f"Suggested tool: {suggested_tool or 'review'}",
        ))
        next_index += 1

    storage = snapshot.get("storage", {})
    for folder in storage.get("top_folders", [])[:20]:
        size = int(folder.get("size") or 0)
        path = str(folder.get("path") or "")
        issues.append(make_issue(
            index=next_index,
            severity="info",
            category="large_folder_review",
            title="Folder lon can review",
            detail=f"Folder nay dang chiem {format_size(size)}.",
            source=str(folder.get("source") or "storage"),
            path=path,
            size=size,
            recommended_decision="manual_review",
            plan_action="manual_review",
            plan_status="requires_user_input",
            requires_user_input=True,
            reason="Folder-level action can anh xa thu cong truoc khi move/xoa file ben trong.",
        ))
        next_index += 1

    for file_item in storage.get("large_files", [])[:50]:
        issues.append(classify_large_file(file_item, index=next_index))
        next_index += 1

    return issues


def issue_to_action_item(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": issue.get("path"),
        "name": issue.get("name"),
        "size": issue.get("size"),
        "size_text": issue.get("size_text"),
        "candidate_group": issue.get("category"),
        "context": issue.get("title"),
        "policy_decision": issue.get("policy_decision"),
        "plan_action": issue.get("plan_action"),
        "plan_status": issue.get("plan_status"),
        "reason": issue.get("reason"),
        "can_execute_now": False,
        "requires_user_input": issue.get("requires_user_input", True),
        "issue_id": issue.get("issue_id"),
        "issue_severity": issue.get("severity"),
        "risk": issue.get("risk"),
        "risk_category": issue.get("risk_category"),
    }


def group_issue(issue: dict[str, Any]) -> str:
    if issue.get("plan_status") in {"blocked_by_policy", "kept_by_policy"}:
        return "do_not_touch"
    if issue.get("plan_action") == "keep":
        return "do_not_touch"
    if issue.get("requires_user_input"):
        return "needs_selection"
    if issue.get("can_execute_now"):
        return "safe_to_execute"
    return "review_only"


def build_action_groups(issues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {key: [] for key in ACTION_GROUPS}
    for issue in issues:
        groups[group_issue(issue)].append(issue_to_action_item(issue))
    return groups


def summarize_issues(issues: list[dict[str, Any]], groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_plan_action: dict[str, int] = {}
    for issue in issues:
        severity = str(issue.get("severity") or "unknown")
        category = str(issue.get("category") or "unknown")
        plan_action = str(issue.get("plan_action") or "unknown")
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
        by_plan_action[plan_action] = by_plan_action.get(plan_action, 0) + 1

    return {
        "issue_count": len(issues),
        "by_severity": by_severity,
        "by_category": by_category,
        "by_plan_action": by_plan_action,
        "delete_candidate_count": by_plan_action.get("delete_candidate", 0),
        "move_later_count": by_plan_action.get("move_later", 0),
        "needs_backup_count": by_plan_action.get("backup_first", 0),
        "safe_to_execute_count": len(groups["safe_to_execute"]),
        "needs_selection_count": len(groups["needs_selection"]),
        "do_not_touch_count": len(groups["do_not_touch"]),
        "review_only_count": len(groups["review_only"]),
        "file_operations_executed": False,
        "undo_available": False,
    }


def build_issue_classifier_result(
    *,
    source_report_path: str | Path | None = None,
    auto_scan_result: dict[str, Any] | None = None,
    include_items: bool = True,
    create_fallback_scan: bool = False,
) -> dict[str, Any]:
    source_report = None
    auto_scan = auto_scan_result
    if auto_scan is None:
        auto_scan, source_report = load_auto_scan_result(source_report_path)

    if auto_scan is None and create_fallback_scan:
        auto_scan = build_auto_scan_session_result(storage_mode="light")
        source_report = None

    if not isinstance(auto_scan, dict) or auto_scan.get("schema") != AUTO_SCAN_SESSION_SCHEMA:
        empty_groups = {key: [] for key in ACTION_GROUPS}
        return {
            "schema": ISSUE_CLASSIFIER_SCHEMA,
            "status": "missing_source_report",
            "source_report": source_report,
            "summary": summarize_issues([], empty_groups),
            "issues": [],
            "action_groups": empty_groups,
            "safety_contract": build_safety_contract(),
        }

    issues = build_issues(auto_scan)
    groups = build_action_groups(issues)
    summary = summarize_issues(issues, groups)
    return {
        "schema": ISSUE_CLASSIFIER_SCHEMA,
        "status": "ready",
        "source_report": source_report,
        "summary": summary,
        "issues": issues if include_items else [],
        "action_groups": groups if include_items else {key: [] for key in groups},
        "safety_contract": build_safety_contract(),
    }


def build_safety_contract() -> dict[str, Any]:
    return {
        "read_only": True,
        "executes_file_operations": False,
        "delete_candidate_is_intent_only": True,
        "delete_requires_safe_delete_adapter": True,
        "delete_requires_user_selection": True,
        "delete_requires_final_token": True,
        "move_requires_file_operation_adapter": True,
        "safe_to_execute_count_expected": 0,
    }


def export_issue_classifier_report(
    *,
    source_report_path: str | Path | None = None,
    include_items: bool = True,
    create_fallback_scan: bool = False,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    result = build_issue_classifier_result(
        source_report_path=source_report_path,
        include_items=include_items,
        create_fallback_scan=create_fallback_scan,
    )
    report_status = "success" if result["status"] == "ready" else "warning"
    report = create_report(
        tool_name=ISSUE_CLASSIFIER_TOOL,
        action="classify_auto_scan_issues",
        status=report_status,
        risk_level="safe",
        input_data={
            "source_report_path": str(source_report_path) if source_report_path else None,
            "include_items": include_items,
            "create_fallback_scan": create_fallback_scan,
        },
        results=result,
        recommendations=[
            "Review needs_selection items in Bot Controller before any action.",
            "delete_candidate remains intent-only until Safe Delete Adapter dry-run and final token.",
        ],
        summary=result["summary"],
        undo_available=False,
        tags=["issue_classifier", "classifier", "read_only", *(extra_tags or [])],
    )
    log_action(
        ISSUE_CLASSIFIER_TOOL,
        "export_issue_classifier_report",
        report_status,
        {
            "report": str(report),
            "issue_count": result["summary"]["issue_count"],
            "delete_candidate_count": result["summary"]["delete_candidate_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": report_status,
        "report": str(report),
        "classifier": result,
    }


def print_issue_classifier_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== ISSUE CLASSIFIER V1 ==========")
    print(f"Status: {result['status']}")
    print(f"Issues: {summary['issue_count']}")
    print(f"Severity: {summary['by_severity']}")
    print(f"Plan actions: {summary['by_plan_action']}")
    print(f"Needs selection: {summary['needs_selection_count']}")
    print(f"Delete candidates: {summary['delete_candidate_count']}")
    for issue in result.get("issues", [])[:20]:
        print(f"- {issue['issue_id']} | {issue['plan_action']} | {issue.get('size_text') or '-'} | {issue.get('path') or issue['title']}")


def run_issue_classifier() -> None:
    while True:
        print("""
========== ISSUE CLASSIFIER V1 ==========
1. Preview latest auto-scan classification
2. Export latest auto-scan classification report
3. Export with fallback light scan if no auto-scan report
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_issue_classifier_summary(build_issue_classifier_result(include_items=True))

        elif choice == "2":
            result = export_issue_classifier_report(include_items=True)
            print_issue_classifier_summary(result["classifier"])

        elif choice == "3":
            result = export_issue_classifier_report(include_items=True, create_fallback_scan=True)
            print_issue_classifier_summary(result["classifier"])

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_issue_classifier()
