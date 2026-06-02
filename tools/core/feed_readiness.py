from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import BASE_DIR, USER_SETTINGS_FILE, validate_user_settings
from tools.core.action_policy import build_action_policy_health
from tools.core.assistant_logger import log_action
from tools.core.audit_center import get_audit_snapshot
from tools.core.capability_registry import (
    get_capabilities,
    summarize_capabilities,
    validate_capability_registry,
)
from tools.core.external_apps import (
    build_external_apps_health,
    load_external_apps_health_state,
)
from tools.core.recommendation_center import (
    collect_recommendation_queue,
    summarize_recommendation_queue,
)
from tools.core.report_manager import (
    REPORT_SCHEMA_VERSION,
    create_report,
    read_recent_report_index,
    validate_report_file,
)
from tools.core.tool_tester import TOOLS_TO_TEST


DOC_FEED_SOURCES = [
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/PROJECT_STATUS.md",
    "docs/ROADMAP.md",
    "docs/TOOL_MASTER_PLAN.md",
    "docs/EXTERNAL_APPS.md",
    "docs/CHANGELOG.md",
]


def make_check(
    check_id: str,
    status: str,
    title: str,
    detail: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "title": title,
        "detail": detail,
        "data": data or {},
    }


def get_latest_report_by_tool(
    tool_name: str,
    *,
    action: str | None = None,
    limit: int = 500,
) -> dict[str, Any] | None:
    records = read_recent_report_index(limit=limit)

    for record in reversed(records):
        if record.get("tool") != tool_name:
            continue
        if action is not None and record.get("action") != action:
            continue
        return record

    return None


def validate_recent_report_schemas(limit: int = 80) -> dict[str, Any]:
    records = read_recent_report_index(limit=limit)
    invalid = []
    missing = []

    for record in records:
        report_path = record.get("report_path")
        if not report_path:
            missing.append(record)
            continue

        validation = validate_report_file(report_path)
        if validation["status"] == "missing":
            missing.append({
                **record,
                "validation": validation,
            })
        elif validation["status"] != "valid":
            invalid.append({
                **record,
                "validation": validation,
            })

    return {
        "checked_count": len(records),
        "invalid_count": len(invalid),
        "missing_count": len(missing),
        "invalid": invalid[:10],
        "missing": missing[:10],
    }


def build_feed_sources() -> dict[str, Any]:
    doc_sources = []
    for relative_path in DOC_FEED_SOURCES:
        path = BASE_DIR / relative_path
        doc_sources.append({
            "path": str(path),
            "exists": path.exists(),
        })

    latest_reports = {}
    for tool_name in [
        "full_system_tester",
        "system_advisor",
        "external_apps",
        "capability_registry",
        "recommendation_center",
        "audit_center",
        "action_policy",
    ]:
        latest = get_latest_report_by_tool(tool_name)
        latest_reports[tool_name] = latest

    return {
        "docs": doc_sources,
        "config": {
            "path": str(USER_SETTINGS_FILE),
            "exists": USER_SETTINGS_FILE.exists(),
        },
        "latest_reports": latest_reports,
        "state_files": {
            "recommendation_queue": str(BASE_DIR / "data" / "recommendation_queue.jsonl"),
            "action_policy": str(BASE_DIR / "data" / "action_policy.jsonl"),
            "external_apps_health_state": str(BASE_DIR / "data" / "external_apps_health_state.json"),
        },
    }


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    pass_count = sum(1 for item in checks if item["status"] == "pass")
    warn_count = sum(1 for item in checks if item["status"] == "warn")
    fail_count = sum(1 for item in checks if item["status"] == "fail")
    return {
        "total": len(checks),
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "ready": fail_count == 0,
        "readiness_status": "ready" if fail_count == 0 else "needs_attention",
    }


def build_feed_readiness_result() -> dict[str, Any]:
    checks = []

    config_validation = validate_user_settings()
    config_status = "fail" if config_validation["status"] != "valid" else "pass"
    if config_status == "pass" and config_validation.get("warnings"):
        config_status = "warn"
    checks.append(make_check(
        "config",
        config_status,
        "Config health",
        "Config is valid." if config_status == "pass" else "Config needs review before feed.",
        config_validation,
    ))

    capability_validation = validate_capability_registry(expected_tools=TOOLS_TO_TEST)
    checks.append(make_check(
        "capability_registry",
        "pass" if capability_validation["status"] == "valid" else "fail",
        "Capability registry",
        "Every tested tool has a capability entry."
        if capability_validation["status"] == "valid"
        else "Capability registry has issues.",
        capability_validation,
    ))

    external_state = load_external_apps_health_state()
    external_health = build_external_apps_health(
        include_versions=False,
        previous_state=external_state,
    )
    external_summary = external_health["summary"]
    external_status = "pass"
    if external_health["missing"] > 0 or external_summary["warning_drift_count"] > 0:
        external_status = "fail"
    elif external_summary["drift_event_count"] > 0:
        external_status = "warn"
    checks.append(make_check(
        "external_apps",
        external_status,
        "External apps health",
        (
            f"{external_summary['available']}/{external_summary['total']} apps available, "
            f"{external_summary['drift_event_count']} drift events."
        ),
        {
            "summary": external_summary,
            "impacted_tool_ids": external_health["impacted_tool_ids"],
            "drift_events": external_health["drift_events"],
        },
    ))

    queue = collect_recommendation_queue(report_limit=120)
    queue_summary = summarize_recommendation_queue(queue)
    queue_status = "warn" if queue_summary["pending_count"] > 0 else "pass"
    checks.append(make_check(
        "recommendation_queue",
        queue_status,
        "Recommendation queue",
        (
            f"{queue_summary['pending_count']} pending recommendations. "
            "Pending items can be fed as context but should be reviewed before automation."
        ),
        {
            "summary": queue_summary,
            "items": queue[:20],
        },
    ))

    action_policy_health = build_action_policy_health()
    action_policy_validation = action_policy_health["validation"]
    action_policy_coverage = action_policy_health["step3_coverage"]
    action_policy_status = "pass"
    if action_policy_validation["status"] != "valid":
        action_policy_status = "fail"
    elif action_policy_coverage.get("uncovered_count", 0) > 0:
        action_policy_status = "warn"
    checks.append(make_check(
        "action_policy",
        action_policy_status,
        "Action policy",
        (
            f"{action_policy_health['summary']['total']} active policies, "
            f"{action_policy_coverage.get('uncovered_count', 0)} uncovered Step 3 items."
        ),
        action_policy_health,
    ))

    latest_full_system = get_latest_report_by_tool("full_system_tester")
    full_system_status = "fail"
    full_system_detail = "No Full System Tester report found."
    if latest_full_system:
        latest_status = str(latest_full_system.get("status") or "")
        full_system_status = "pass" if latest_status == "success" else "fail"
        full_system_detail = f"Latest Full System Tester report status: {latest_status}."
    checks.append(make_check(
        "full_system_tester",
        full_system_status,
        "Full System Tester",
        full_system_detail,
        {
            "latest_report": latest_full_system,
        },
    ))

    schema_validation = validate_recent_report_schemas(limit=100)
    schema_status = "pass"
    if schema_validation["invalid_count"] > 0:
        schema_status = "fail"
    elif schema_validation["missing_count"] > 0:
        schema_status = "warn"
    checks.append(make_check(
        "report_schema",
        schema_status,
        "Recent report schema",
        (
            f"Checked {schema_validation['checked_count']} reports, "
            f"{schema_validation['invalid_count']} invalid, "
            f"{schema_validation['missing_count']} missing."
        ),
        schema_validation,
    ))

    audit_snapshot = get_audit_snapshot(limit=80)
    checks.append(make_check(
        "audit_snapshot",
        "pass" if audit_snapshot["report_count"] > 0 else "warn",
        "Audit snapshot",
        (
            f"{audit_snapshot['report_count']} recent reports and "
            f"{audit_snapshot['log_count']} recent logs available."
        ),
        {
            "log_count": audit_snapshot["log_count"],
            "report_count": audit_snapshot["report_count"],
        },
    ))

    feed_sources = build_feed_sources()
    missing_docs = [item for item in feed_sources["docs"] if not item["exists"]]
    checks.append(make_check(
        "feed_sources",
        "pass" if not missing_docs and feed_sources["config"]["exists"] else "fail",
        "Feed source files",
        "Core docs and config are present." if not missing_docs else "Some feed source docs are missing.",
        {
            "missing_docs": missing_docs,
            "source_count": len(feed_sources["docs"]),
        },
    ))

    summary = summarize_checks(checks)
    capability_summary = summarize_capabilities()
    recommendations = []
    if summary["fail_count"] > 0:
        recommendations.append("Fix failed readiness checks before feeding assistant context.")
    if queue_summary["pending_count"] > 0:
        recommendations.append("Review pending recommendations before enabling any automated assistant action.")
    if external_health["missing"] == 0 and external_summary["drift_event_count"] == 0:
        recommendations.append("External app paths are stable for this readiness snapshot.")
    recommendations.append("Do not train/feed with raw backups, logs, or private user files; feed only curated reports/docs.")

    return {
        "schema": "feed_readiness_v1",
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "summary": summary,
        "checks": checks,
        "capability_summary": capability_summary,
        "external_apps_summary": external_summary,
        "recommendation_queue_summary": queue_summary,
        "action_policy_summary": action_policy_health["summary"],
        "action_policy_validation": action_policy_validation,
        "feed_sources": feed_sources,
        "recommendations": recommendations,
    }


def print_feed_readiness_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== FEED ASSISTANT READINESS ==========")
    print(f"Status: {summary['readiness_status']}")
    print(f"Checks: {summary['pass_count']} pass, {summary['warn_count']} warn, {summary['fail_count']} fail")

    print("\nChecks:")
    for check in result["checks"]:
        print(f"[{check['status'].upper():<4}] {check['title']}: {check['detail']}")

    print("\nFeed sources:")
    for item in result["feed_sources"]["docs"]:
        mark = "OK" if item["exists"] else "MISS"
        print(f"[{mark}] {item['path']}")

    print("\nRecommendations:")
    for item in result["recommendations"]:
        print(f"- {item}")


def export_feed_readiness_report() -> dict[str, Any]:
    result = build_feed_readiness_result()
    summary = result["summary"]
    status = "success" if summary["ready"] else "warning"

    report = create_report(
        tool_name="feed_readiness",
        action="pre_feed_check",
        status=status,
        risk_level="safe",
        input_data={
            "scope": "pre_feed_assistant",
            "read_only": True,
        },
        results=result,
        recommendations=result["recommendations"],
        summary={
            "ready": summary["ready"],
            "readiness_status": summary["readiness_status"],
            "check_count": summary["total"],
            "pass_count": summary["pass_count"],
            "warn_count": summary["warn_count"],
            "fail_count": summary["fail_count"],
            "pending_recommendation_count": result["recommendation_queue_summary"]["pending_count"],
            "action_policy_count": result["action_policy_summary"]["total"],
            "external_app_available_count": result["external_apps_summary"]["available"],
            "external_app_total": result["external_apps_summary"]["total"],
            "external_app_drift_count": result["external_apps_summary"]["drift_event_count"],
            "undo_available": False,
        },
        undo_available=False,
        tags=["feed_readiness", "assistant", "pre_feed", "read_only"],
    )

    log_action(
        "feed_readiness",
        "export_feed_readiness_report",
        status,
        {
            "ready": summary["ready"],
            "pass_count": summary["pass_count"],
            "warn_count": summary["warn_count"],
            "fail_count": summary["fail_count"],
            "report": str(report),
        },
    )

    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "readiness": result,
    }


def run_feed_readiness() -> None:
    while True:
        print("""
========== FEED ASSISTANT READINESS ==========
1. Xem readiness summary
2. Xuat readiness report
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_feed_readiness_summary(build_feed_readiness_result())

        elif choice == "2":
            export_feed_readiness_report()

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_feed_readiness()
