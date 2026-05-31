from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.core.assistant_logger import log_action
from tools.core.capability_registry import get_capability_by_id
from tools.core.report_manager import create_report, read_recent_report_index


SEVERITY_ORDER = {
    "critical": 0,
    "warning": 1,
    "info": 2,
}


def safe_read_report(report_path: str | Path) -> dict[str, Any] | None:
    path = Path(report_path)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def normalize_severity(value: Any, default: str = "info") -> str:
    text = str(value or "").strip().lower()
    return text if text in SEVERITY_ORDER else default


def infer_report_issue_severity(status: str) -> str:
    status = status.strip().lower()
    if status == "error":
        return "warning"
    if status == "warning":
        return "warning"
    return "info"


def enrich_suggested_tool(item: dict[str, Any]) -> dict[str, Any]:
    suggested_tool_id = item.get("suggested_tool_id")
    if not suggested_tool_id:
        return item

    capability = get_capability_by_id(str(suggested_tool_id))
    if capability is None:
        return item

    enriched = dict(item)
    if not enriched.get("suggested_tool_name"):
        enriched["suggested_tool_name"] = capability["name"]
    if not enriched.get("suggested_tool_risk"):
        enriched["suggested_tool_risk"] = capability["risk_level"]
    if enriched.get("suggested_tool_needs_confirmation") is None:
        enriched["suggested_tool_needs_confirmation"] = capability["needs_confirmation"]
    return enriched


def normalize_recommendation_item(
    item: Any,
    *,
    report_record: dict[str, Any],
    index: int,
) -> dict[str, Any] | None:
    report_path = report_record.get("report_path")
    report_tool = report_record.get("tool")
    report_created_at = report_record.get("created_at")

    if isinstance(item, dict):
        recommendation_id = str(item.get("id") or f"{report_tool}-recommendation-{index}")
        severity = normalize_severity(item.get("severity"))
        title = str(item.get("title") or "Recommendation")
        detail = str(item.get("detail") or item.get("message") or "")
        if not detail:
            return None

        normalized = {
            "id": recommendation_id,
            "severity": severity,
            "title": title,
            "detail": detail,
            "source": item.get("source") or report_tool,
            "suggested_tool_id": item.get("suggested_tool_id"),
            "suggested_tool_name": item.get("suggested_tool_name"),
            "suggested_tool_risk": item.get("suggested_tool_risk"),
            "suggested_tool_needs_confirmation": item.get("suggested_tool_needs_confirmation"),
            "suggestion_only": True,
            "report_tool": report_tool,
            "report_created_at": report_created_at,
            "report_path": report_path,
        }
        return enrich_suggested_tool(normalized)

    if isinstance(item, str) and item.strip():
        return {
            "id": f"{report_tool}-recommendation-{index}",
            "severity": "info",
            "title": "Recommendation",
            "detail": item.strip(),
            "source": report_tool,
            "suggested_tool_id": None,
            "suggested_tool_name": None,
            "suggested_tool_risk": None,
            "suggested_tool_needs_confirmation": None,
            "suggestion_only": True,
            "report_tool": report_tool,
            "report_created_at": report_created_at,
            "report_path": report_path,
        }

    return None


def extract_recommendations_from_report(
    report_data: dict[str, Any],
    report_record: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[Any] = []
    results = report_data.get("results", {})

    if report_data.get("tool") == "system_advisor" and isinstance(results, dict):
        structured = results.get("recommendations")
        if isinstance(structured, list):
            items.extend(structured)

    if not items and report_data.get("tool") in {"system_advisor", "audit_center"}:
        raw_recommendations = report_data.get("recommendations", [])
        if isinstance(raw_recommendations, list):
            items.extend(raw_recommendations)

    normalized = []
    for index, item in enumerate(items, start=1):
        recommendation = normalize_recommendation_item(
            item,
            report_record=report_record,
            index=index,
        )
        if recommendation is not None:
            normalized.append(recommendation)

    return normalized


def build_report_issue_recommendation(report_record: dict[str, Any]) -> dict[str, Any] | None:
    status = str(report_record.get("status") or "").strip().lower()
    if status not in {"warning", "error"}:
        return None

    tool_name = report_record.get("tool") or "unknown_tool"
    capability = get_capability_by_id("audit_center")
    return {
        "id": f"report-issue-{tool_name}-{report_record.get('created_at')}",
        "severity": infer_report_issue_severity(status),
        "title": "Report can xem lai",
        "detail": f"{tool_name} co report status {status}. Nen xem Audit Center truoc khi chay tiep.",
        "source": "audit_center",
        "suggested_tool_id": "audit_center",
        "suggested_tool_name": capability["name"] if capability else "Audit Center",
        "suggested_tool_risk": capability["risk_level"] if capability else "safe",
        "suggested_tool_needs_confirmation": capability["needs_confirmation"] if capability else False,
        "suggestion_only": True,
        "report_tool": tool_name,
        "report_created_at": report_record.get("created_at"),
        "report_path": report_record.get("report_path"),
    }


def dedupe_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []

    for item in recommendations:
        key = (
            item.get("id"),
            item.get("detail"),
            item.get("report_path"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def sort_recommendation_queue(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        queue,
        key=lambda item: (
            SEVERITY_ORDER.get(item.get("severity"), 99),
            str(item.get("report_created_at") or ""),
            str(item.get("id") or ""),
        ),
    )


def collect_recommendation_queue(
    *,
    report_limit: int = 80,
    include_report_issues: bool = True,
) -> list[dict[str, Any]]:
    report_records = read_recent_report_index(limit=report_limit)
    queue = []

    for report_record in report_records:
        report_data = safe_read_report(str(report_record.get("report_path") or ""))
        if report_data is not None:
            queue.extend(extract_recommendations_from_report(report_data, report_record))

        if include_report_issues:
            issue = build_report_issue_recommendation(report_record)
            if issue is not None:
                queue.append(issue)

    return sort_recommendation_queue(dedupe_recommendations(queue))


def summarize_recommendation_queue(queue: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total": len(queue),
        "critical_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "suggested_tool_count": 0,
        "needs_confirmation_count": 0,
    }

    for item in queue:
        severity_key = f"{item.get('severity')}_count"
        if severity_key in summary:
            summary[severity_key] += 1
        if item.get("suggested_tool_id"):
            summary["suggested_tool_count"] += 1
        if item.get("suggested_tool_needs_confirmation"):
            summary["needs_confirmation_count"] += 1

    return summary


def filter_recommendations_by_severity(
    queue: list[dict[str, Any]],
    severity: str,
) -> list[dict[str, Any]]:
    severity = normalize_severity(severity, default="")
    if not severity:
        return []
    return [item for item in queue if item.get("severity") == severity]


def recommendation_to_line(item: dict[str, Any], index: int) -> str:
    tool_name = item.get("suggested_tool_name") or "-"
    tool_risk = item.get("suggested_tool_risk") or "-"
    return (
        f"{index:>2}. [{str(item.get('severity')).upper()}] "
        f"{item.get('title')} | Tool: {tool_name} ({tool_risk})\n"
        f"    {item.get('detail')}\n"
        f"    Report: {item.get('report_path')}"
    )


def print_recommendation_queue(queue: list[dict[str, Any]]) -> None:
    if not queue:
        print("Khong co recommendation trong report gan day.")
        return

    print("\n========== RECOMMENDATION QUEUE ==========")
    for index, item in enumerate(queue, start=1):
        print(recommendation_to_line(item, index))


def export_recommendation_queue(report_limit: int = 120) -> dict[str, Any]:
    queue = collect_recommendation_queue(report_limit=report_limit)
    summary = summarize_recommendation_queue(queue)
    status = "success" if queue else "empty"

    report = create_report(
        tool_name="recommendation_center",
        action="export_queue",
        status=status,
        risk_level="safe",
        input_data={
            "report_limit": report_limit,
        },
        results={
            "summary": summary,
            "queue": queue,
        },
        recommendations=[
            "Review critical recommendations first.",
            "Recommendation Center is read-only and does not execute cleanup tools.",
            "Run System Advisor v2 again if the queue looks stale.",
        ],
        summary={
            **summary,
            "undo_available": False,
        },
        undo_available=False,
        tags=["recommendations", "queue", "read_only"],
    )

    log_action(
        "recommendation_center",
        "export_recommendation_queue",
        status,
        {
            "report": str(report),
            "queue_count": len(queue),
            "critical_count": summary["critical_count"],
            "warning_count": summary["warning_count"],
        },
    )

    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "summary": summary,
        "queue": queue,
    }


def run_recommendation_center() -> None:
    while True:
        print("""
========== RECOMMENDATION CENTER ==========
1. Xem summary queue
2. Xem tat ca recommendation
3. Loc theo severity
4. Xuat report queue
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            queue = collect_recommendation_queue()
            print(summarize_recommendation_queue(queue))

        elif choice == "2":
            queue = collect_recommendation_queue()
            print_recommendation_queue(queue)

        elif choice == "3":
            severity = input("Nhap severity critical/warning/info: ").strip()
            queue = filter_recommendations_by_severity(
                collect_recommendation_queue(),
                severity,
            )
            print_recommendation_queue(queue)

        elif choice == "4":
            raw_limit = input("Doc bao nhieu report gan day? [120]: ").strip()
            report_limit = int(raw_limit) if raw_limit.isdigit() else 120
            export_recommendation_queue(report_limit=report_limit)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_recommendation_center()
