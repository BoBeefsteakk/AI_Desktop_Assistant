from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR, DATA_DIR, USER_SETTINGS_FILE
from tools.core.action_planner import build_action_plan
from tools.core.action_policy import build_action_policy_health
from tools.core.assistant_logger import log_action
from tools.core.candidate_review import build_candidate_review
from tools.core.capability_registry import summarize_capabilities, validate_capability_registry
from tools.core.feed_readiness import DOC_FEED_SOURCES, build_feed_readiness_result
from tools.core.recommendation_center import (
    collect_recommendation_queue,
    summarize_recommendation_queue,
)
from tools.core.report_manager import create_report, read_recent_report_index


PRE_FEED_BUNDLE_TOOL = "pre_feed_bundle"
BUNDLE_DIR = DATA_DIR / "feed_bundles"
LATEST_REPORT_TOOLS = [
    "full_system_tester",
    "tool_tester",
    "system_advisor",
    "external_apps",
    "capability_registry",
    "recommendation_center",
    "action_policy",
    "candidate_review",
    "action_planner",
    "feed_readiness",
]


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def read_doc_source(relative_path: str, *, include_content: bool) -> dict[str, Any]:
    path = BASE_DIR / relative_path
    item: dict[str, Any] = {
        "path": str(path),
        "relative_path": relative_path,
        "exists": path.exists(),
    }
    if not path.exists():
        return item

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        item["read_error"] = True
        return item

    item["sha256"] = sha256_text(content)
    item["length"] = len(content)
    if include_content:
        item["content"] = content
    return item


def latest_report_records_by_tool(limit: int = 500) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in read_recent_report_index(limit=limit):
        tool_name = str(record.get("tool") or "")
        if tool_name in LATEST_REPORT_TOOLS:
            latest[tool_name] = record
    return latest


def sanitize_report_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    report_data = safe_read_json(str(record.get("report_path") or ""))
    sanitized = {
        "tool": record.get("tool"),
        "action": record.get("action"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
        "report_path": record.get("report_path"),
    }
    if report_data is None:
        sanitized["readable"] = False
        return sanitized

    sanitized.update({
        "readable": True,
        "risk_level": report_data.get("risk_level"),
        "summary": report_data.get("summary", {}),
        "recommendations": report_data.get("recommendations", []),
        "tags": report_data.get("tags", []),
    })
    return sanitized


def build_pre_feed_bundle(*, include_doc_content: bool = True) -> dict[str, Any]:
    queue = collect_recommendation_queue(report_limit=120, states=None)
    feed_readiness = build_feed_readiness_result()
    candidate_review = build_candidate_review(include_items=False)
    action_plan = build_action_plan(include_items=False)
    latest_reports = latest_report_records_by_tool()

    return {
        "schema": "pre_feed_bundle_v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "scope": "curated_tool_context_before_feed",
        "safety_contract": {
            "read_only": True,
            "no_raw_backups": True,
            "no_raw_logs": True,
            "no_user_file_contents": True,
            "no_cleanup_execution": True,
        },
        "docs": [
            read_doc_source(relative_path, include_content=include_doc_content)
            for relative_path in DOC_FEED_SOURCES
        ],
        "config": {
            "path": str(USER_SETTINGS_FILE),
            "exists": USER_SETTINGS_FILE.exists(),
        },
        "capability_registry": {
            "summary": summarize_capabilities(),
            "validation": validate_capability_registry(),
        },
        "recommendation_queue": {
            "summary": summarize_recommendation_queue(queue),
            "items": queue,
        },
        "action_policy": build_action_policy_health(),
        "candidate_review": {
            "summary": candidate_review["summary"],
            "source_report": candidate_review.get("source_report"),
            "status": candidate_review["status"],
        },
        "action_plan": {
            "summary": action_plan["summary"],
            "source_report": action_plan.get("source_report"),
            "status": action_plan["status"],
            "safety_contract": action_plan["safety_contract"],
        },
        "feed_readiness": {
            "summary": feed_readiness["summary"],
            "checks": [
                {
                    "id": item["id"],
                    "status": item["status"],
                    "title": item["title"],
                    "detail": item["detail"],
                }
                for item in feed_readiness["checks"]
            ],
        },
        "latest_reports": {
            tool_name: sanitize_report_record(latest_reports.get(tool_name))
            for tool_name in LATEST_REPORT_TOOLS
        },
    }


def write_pre_feed_bundle(bundle: dict[str, Any]) -> Path:
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    path = BUNDLE_DIR / f"pre_feed_bundle_{now_stamp()}.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_pre_feed_bundle(*, include_doc_content: bool = True) -> dict[str, Any]:
    bundle = build_pre_feed_bundle(include_doc_content=include_doc_content)
    path = write_pre_feed_bundle(bundle)
    docs_present = sum(1 for item in bundle["docs"] if item["exists"])
    report = create_report(
        tool_name=PRE_FEED_BUNDLE_TOOL,
        action="export_bundle",
        status="success",
        risk_level="safe",
        input_data={
            "include_doc_content": include_doc_content,
        },
        results={
            "bundle_path": str(path),
            "bundle_schema": bundle["schema"],
            "safety_contract": bundle["safety_contract"],
            "doc_count": len(bundle["docs"]),
            "docs_present": docs_present,
            "latest_report_tools": LATEST_REPORT_TOOLS,
        },
        recommendations=[
            "Feed this bundle only as curated context; do not include raw backups or user file contents.",
            "Rebuild the bundle after major tool/report/policy changes.",
            "Use Feed Readiness and Full System Tester before enabling assistant automation.",
        ],
        summary={
            "bundle_path": str(path),
            "doc_count": len(bundle["docs"]),
            "docs_present": docs_present,
            "queue_total": bundle["recommendation_queue"]["summary"]["total"],
            "policy_count": bundle["action_policy"]["summary"]["total"],
            "readiness_status": bundle["feed_readiness"]["summary"]["readiness_status"],
            "undo_available": False,
        },
        undo_available=False,
        tags=["pre_feed_bundle", "assistant", "curated_context", "read_only"],
    )
    log_action(
        PRE_FEED_BUNDLE_TOOL,
        "export_pre_feed_bundle",
        "success",
        {
            "bundle_path": str(path),
            "report": str(report),
            "doc_count": len(bundle["docs"]),
        },
    )
    print(f"Bundle: {path}")
    print(f"Report: {report}")
    return {
        "status": "success",
        "bundle_path": str(path),
        "report": str(report),
        "bundle": bundle,
    }


def print_pre_feed_bundle_summary(bundle: dict[str, Any]) -> None:
    print("\n========== PRE-FEED BUNDLE ==========")
    print(f"Schema: {bundle['schema']}")
    print(f"Docs: {sum(1 for item in bundle['docs'] if item['exists'])}/{len(bundle['docs'])}")
    print(f"Queue: {bundle['recommendation_queue']['summary']}")
    print(f"Policy count: {bundle['action_policy']['summary']['total']}")
    print(f"Action plan: {bundle['action_plan']['summary']}")
    print(f"Readiness: {bundle['feed_readiness']['summary']['readiness_status']}")


def run_pre_feed_bundle() -> None:
    while True:
        print("""
========== PRE-FEED BUNDLE ==========
1. Xem bundle summary
2. Xuat pre-feed bundle
0. Thoat
""")
        choice = input("Chon: ").strip()
        if choice == "1":
            print_pre_feed_bundle_summary(build_pre_feed_bundle(include_doc_content=False))
        elif choice == "2":
            export_pre_feed_bundle(include_doc_content=True)
        elif choice == "0":
            break
        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_pre_feed_bundle()
