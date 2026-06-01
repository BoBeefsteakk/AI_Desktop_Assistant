from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import DATA_DIR
from tools.core.assistant_logger import log_action
from tools.core.capability_registry import get_capability_by_id
from tools.core.report_manager import create_report, read_recent_report_index


SEVERITY_ORDER = {
    "critical": 0,
    "warning": 1,
    "info": 2,
}
VALID_WORKFLOW_STATES = {"pending", "deferred", "handled", "ignored"}
DEFAULT_VISIBLE_STATES = ("pending", "deferred")
RECOMMENDATION_QUEUE_FILE = DATA_DIR / "recommendation_queue.jsonl"
TEST_REPORT_TAGS = {
    "behavior_test",
    "contract_test",
    "full_system",
    "natural_command_v3",
    "recommendation_workflow",
}
LATEST_ONLY_REPORT_TOOLS = {
    "system_advisor",
    "external_apps",
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


def is_test_report_record(report_record: dict[str, Any]) -> bool:
    report_data = safe_read_report(str(report_record.get("report_path") or ""))
    if not report_data:
        return False

    tags = {
        str(item).strip().lower()
        for item in report_data.get("tags", [])
        if str(item).strip()
    }
    if tags.intersection(TEST_REPORT_TAGS):
        return True

    action = str(report_data.get("action") or report_record.get("action") or "").lower()
    return action.endswith("_contract") or action in {
        "contract_warning",
        "workflow_state_test",
    }


def filter_report_records_for_queue(
    report_records: list[dict[str, Any]],
    *,
    include_test_reports: bool = False,
) -> list[dict[str, Any]]:
    filtered = [
        item for item in report_records
        if include_test_reports or not is_test_report_record(item)
    ]
    latest_snapshot_index = {}

    for index, item in enumerate(filtered):
        tool_name = str(item.get("tool") or "")
        status = str(item.get("status") or "")
        if tool_name not in LATEST_ONLY_REPORT_TOOLS or status != "success":
            continue

        key = (
            tool_name,
            str(item.get("action") or ""),
        )
        latest_snapshot_index[key] = index

    result = []
    for index, item in enumerate(filtered):
        tool_name = str(item.get("tool") or "")
        status = str(item.get("status") or "")
        if tool_name in LATEST_ONLY_REPORT_TOOLS and status == "success":
            key = (
                tool_name,
                str(item.get("action") or ""),
            )
            if latest_snapshot_index.get(key) != index:
                continue
        result.append(item)

    return result


def normalize_severity(value: Any, default: str = "info") -> str:
    text = str(value or "").strip().lower()
    return text if text in SEVERITY_ORDER else default


def normalize_workflow_state(value: Any, default: str = "pending") -> str:
    text = str(value or "").strip().lower()
    return text if text in VALID_WORKFLOW_STATES else default


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def make_recommendation_fingerprint(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("source") or ""),
        str(item.get("report_tool") or ""),
        str(item.get("title") or ""),
        str(item.get("detail") or ""),
        str(item.get("suggested_tool_id") or ""),
    ]
    payload = "\n".join(part.strip().lower() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def get_state_file(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else RECOMMENDATION_QUEUE_FILE


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


def read_recommendation_state_events(
    state_file: str | Path | None = None,
) -> list[dict[str, Any]]:
    path = get_state_file(state_file)
    if not path.exists():
        return []

    events = []
    try:
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(data, dict):
                    continue

                fingerprint = str(data.get("fingerprint") or "").strip()
                state = normalize_workflow_state(data.get("state"), default="")
                if not fingerprint or not state:
                    continue

                events.append({
                    "fingerprint": fingerprint,
                    "state": state,
                    "note": str(data.get("note") or ""),
                    "updated_at": str(data.get("updated_at") or ""),
                    "recommendation_id": data.get("recommendation_id"),
                    "title": data.get("title"),
                })
    except OSError:
        return []

    return events


def get_recommendation_state_map(
    state_file: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    state_map = {}
    for event in read_recommendation_state_events(state_file):
        state_map[event["fingerprint"]] = event
    return state_map


def append_recommendation_state_event(
    fingerprint: str,
    state: str,
    *,
    note: str = "",
    recommendation: dict[str, Any] | None = None,
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    state = normalize_workflow_state(state)
    path = get_state_file(state_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "fingerprint": fingerprint,
        "state": state,
        "note": note,
        "updated_at": now_iso(),
        "recommendation_id": recommendation.get("id") if recommendation else None,
        "title": recommendation.get("title") if recommendation else None,
    }

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


def update_recommendation_state(
    fingerprint: str,
    state: str,
    *,
    note: str = "",
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    fingerprint = str(fingerprint or "").strip()
    if not fingerprint:
        raise ValueError("fingerprint is required")

    return append_recommendation_state_event(
        fingerprint,
        state,
        note=note,
        state_file=state_file,
    )


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

    if isinstance(results, dict):
        structured = results.get("recommendations")
        if isinstance(structured, list):
            items.extend(structured)

    if not items and report_data.get("tool") in {"system_advisor", "audit_center", "external_apps"}:
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
    deduped_by_key = {}

    for item in recommendations:
        key = (
            item.get("id"),
            item.get("detail"),
            item.get("suggested_tool_id"),
        )
        deduped_by_key[key] = item

    return list(deduped_by_key.values())


def attach_workflow_state(
    queue: list[dict[str, Any]],
    *,
    state_file: str | Path | None = None,
) -> list[dict[str, Any]]:
    state_map = get_recommendation_state_map(state_file)
    enriched = []

    for item in queue:
        fingerprint = make_recommendation_fingerprint(item)
        state_event = state_map.get(fingerprint)
        workflow_state = state_event["state"] if state_event else "pending"

        enriched.append({
            **item,
            "fingerprint": fingerprint,
            "workflow_state": workflow_state,
            "workflow_note": state_event.get("note", "") if state_event else "",
            "workflow_updated_at": state_event.get("updated_at", "") if state_event else "",
        })

    return enriched


def persist_new_pending_recommendations(
    queue: list[dict[str, Any]],
    *,
    state_file: str | Path | None = None,
) -> int:
    state_map = get_recommendation_state_map(state_file)
    created = 0

    for item in queue:
        fingerprint = item.get("fingerprint") or make_recommendation_fingerprint(item)
        if fingerprint in state_map:
            continue

        event = append_recommendation_state_event(
            fingerprint,
            "pending",
            recommendation=item,
            note="Auto-added from recent reports.",
            state_file=state_file,
        )
        state_map[fingerprint] = event
        created += 1

    return created


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
    include_test_reports: bool = False,
    state_file: str | Path | None = None,
    states: set[str] | list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    report_records = filter_report_records_for_queue(
        read_recent_report_index(limit=report_limit),
        include_test_reports=include_test_reports,
    )
    queue = []

    for report_record in report_records:
        report_data = safe_read_report(str(report_record.get("report_path") or ""))
        if report_data is not None:
            queue.extend(extract_recommendations_from_report(report_data, report_record))

        if include_report_issues:
            issue = build_report_issue_recommendation(report_record)
            if issue is not None:
                queue.append(issue)

    queue = attach_workflow_state(
        sort_recommendation_queue(dedupe_recommendations(queue)),
        state_file=state_file,
    )

    if states is not None:
        wanted_states = {
            normalize_workflow_state(state)
            for state in states
        }
        queue = [
            item for item in queue
            if item.get("workflow_state") in wanted_states
        ]

    return queue


def sync_recommendation_queue(
    *,
    report_limit: int = 80,
    include_report_issues: bool = True,
    include_test_reports: bool = False,
    state_file: str | Path | None = None,
    states: set[str] | list[str] | tuple[str, ...] | None = DEFAULT_VISIBLE_STATES,
) -> dict[str, Any]:
    all_queue = collect_recommendation_queue(
        report_limit=report_limit,
        include_report_issues=include_report_issues,
        include_test_reports=include_test_reports,
        state_file=state_file,
        states=None,
    )
    created_count = persist_new_pending_recommendations(
        all_queue,
        state_file=state_file,
    )
    visible_queue = collect_recommendation_queue(
        report_limit=report_limit,
        include_report_issues=include_report_issues,
        include_test_reports=include_test_reports,
        state_file=state_file,
        states=states,
    )

    return {
        "created_count": created_count,
        "queue": visible_queue,
        "all_queue": collect_recommendation_queue(
            report_limit=report_limit,
            include_report_issues=include_report_issues,
            include_test_reports=include_test_reports,
            state_file=state_file,
            states=None,
        ),
        "state_file": str(get_state_file(state_file)),
    }


def summarize_recommendation_queue(queue: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total": len(queue),
        "critical_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "suggested_tool_count": 0,
        "needs_confirmation_count": 0,
        "pending_count": 0,
        "deferred_count": 0,
        "handled_count": 0,
        "ignored_count": 0,
    }

    for item in queue:
        severity_key = f"{item.get('severity')}_count"
        if severity_key in summary:
            summary[severity_key] += 1
        state_key = f"{item.get('workflow_state', 'pending')}_count"
        if state_key in summary:
            summary[state_key] += 1
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


def filter_recommendations_by_state(
    queue: list[dict[str, Any]],
    state: str,
) -> list[dict[str, Any]]:
    state = normalize_workflow_state(state, default="")
    if not state:
        return []
    return [item for item in queue if item.get("workflow_state") == state]


def recommendation_to_line(item: dict[str, Any], index: int) -> str:
    tool_name = item.get("suggested_tool_name") or "-"
    tool_risk = item.get("suggested_tool_risk") or "-"
    workflow_state = item.get("workflow_state") or "pending"
    return (
        f"{index:>2}. [{str(item.get('severity')).upper()}] "
        f"{item.get('title')} | State: {workflow_state} | Tool: {tool_name} ({tool_risk})\n"
        f"    {item.get('detail')}\n"
        f"    ID: {item.get('fingerprint')}\n"
        f"    Report: {item.get('report_path')}"
    )


def print_recommendation_queue(queue: list[dict[str, Any]]) -> None:
    if not queue:
        print("Khong co recommendation trong report gan day.")
        return

    print("\n========== RECOMMENDATION QUEUE ==========")
    for index, item in enumerate(queue, start=1):
        print(recommendation_to_line(item, index))


def choose_recommendation_from_queue(queue: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not queue:
        print("Queue dang rong.")
        return None

    print_recommendation_queue(queue)
    raw_index = input("Nhap so thu tu recommendation muon doi trang thai: ").strip()
    if not raw_index.isdigit():
        print("Lua chon khong hop le.")
        return None

    index = int(raw_index) - 1
    if not 0 <= index < len(queue):
        print("So thu tu khong hop le.")
        return None

    return queue[index]


def update_recommendation_from_menu(
    *,
    report_limit: int = 120,
    state_file: str | Path | None = None,
) -> dict[str, Any] | None:
    sync_result = sync_recommendation_queue(
        report_limit=report_limit,
        state_file=state_file,
        states=None,
    )
    recommendation = choose_recommendation_from_queue(sync_result["all_queue"])
    if recommendation is None:
        return None

    print("Trang thai hop le: pending, deferred, handled, ignored")
    state = normalize_workflow_state(input("Nhap trang thai moi: ").strip(), default="")
    if not state:
        print("Trang thai khong hop le.")
        return None

    note = input("Ghi chu ngan [optional]: ").strip()
    event = append_recommendation_state_event(
        recommendation["fingerprint"],
        state,
        note=note,
        recommendation=recommendation,
        state_file=state_file,
    )

    log_action(
        "recommendation_center",
        "update_recommendation_state",
        "success",
        {
            "fingerprint": recommendation["fingerprint"],
            "state": state,
            "state_file": str(get_state_file(state_file)),
        },
    )

    print(f"Da cap nhat {recommendation['fingerprint']} -> {state}")
    return event


def export_recommendation_queue(
    report_limit: int = 120,
    *,
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    sync_result = sync_recommendation_queue(
        report_limit=report_limit,
        state_file=state_file,
        states=None,
    )
    queue = sync_result["all_queue"]
    summary = summarize_recommendation_queue(queue)
    status = "success" if queue else "empty"

    report = create_report(
        tool_name="recommendation_center",
        action="export_queue",
        status=status,
        risk_level="safe",
        input_data={
            "report_limit": report_limit,
            "state_file": sync_result["state_file"],
        },
        results={
            "summary": summary,
            "queue": queue,
            "state_file": sync_result["state_file"],
            "created_count": sync_result["created_count"],
        },
        recommendations=[
            "Review critical recommendations first.",
            "Recommendation Center is read-only and does not execute cleanup tools.",
            "Use pending/deferred/handled/ignored states to avoid repeating the same recommendation.",
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
1. Sync + xem summary queue
2. Xem pending/deferred recommendation
3. Xem tat ca recommendation
4. Loc theo severity
5. Loc theo state
6. Doi trang thai recommendation
7. Xuat report queue
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            sync_result = sync_recommendation_queue()
            print(summarize_recommendation_queue(sync_result["all_queue"]))
            print(f"State file: {sync_result['state_file']}")
            print(f"New pending added: {sync_result['created_count']}")

        elif choice == "2":
            sync_result = sync_recommendation_queue(states=DEFAULT_VISIBLE_STATES)
            print_recommendation_queue(sync_result["queue"])

        elif choice == "3":
            sync_result = sync_recommendation_queue(states=None)
            print_recommendation_queue(sync_result["all_queue"])

        elif choice == "4":
            severity = input("Nhap severity critical/warning/info: ").strip()
            queue = filter_recommendations_by_severity(
                sync_recommendation_queue(states=None)["all_queue"],
                severity,
            )
            print_recommendation_queue(queue)

        elif choice == "5":
            state = input("Nhap state pending/deferred/handled/ignored: ").strip()
            queue = filter_recommendations_by_state(
                sync_recommendation_queue(states=None)["all_queue"],
                state,
            )
            print_recommendation_queue(queue)

        elif choice == "6":
            update_recommendation_from_menu()

        elif choice == "7":
            raw_limit = input("Doc bao nhieu report gan day? [120]: ").strip()
            report_limit = int(raw_limit) if raw_limit.isdigit() else 120
            export_recommendation_queue(report_limit=report_limit)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_recommendation_center()
