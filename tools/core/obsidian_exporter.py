from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from tools.core.action_policy import build_action_policy_health, get_active_policies
from tools.core.assistant_logger import log_action
from tools.core.capability_registry import (
    get_capabilities,
    summarize_capabilities,
    validate_capability_registry,
)
from tools.core.external_apps import build_external_apps_health
from tools.core.feed_readiness import build_feed_readiness_result
from tools.core.recommendation_center import (
    collect_recommendation_queue,
    summarize_recommendation_queue,
)
from tools.core.report_manager import create_report, read_recent_report_index


OBSIDIAN_EXPORTER_TOOL = "obsidian_exporter"
OBSIDIAN_EXPORT_SCHEMA = "obsidian_export_v1"
DEFAULT_VAULT_DIR = BASE_DIR / "obsidian_vault"


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_vault_root(vault_root: str | Path | None = None) -> Path:
    return Path(vault_root) if vault_root is not None else DEFAULT_VAULT_DIR


def escape_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    text = text.replace("\r", " ").replace("\n", " ")
    return text.replace("|", "\\|")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_No items._"

    header_line = "| " + " | ".join(escape_cell(item) for item in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = [
        "| " + " | ".join(escape_cell(item) for item in row) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator, *row_lines])


def make_obsidian_link(path: str) -> str:
    return f"[[{path}]]"


def make_file_link(path: str | Path | None) -> str:
    if not path:
        return ""

    target = Path(path)
    text = str(target)
    try:
        uri = target.resolve().as_uri()
    except ValueError:
        return text
    return f"[{target.name}]({uri})"


def merge_report_tags(base_tags: list[str], extra_tags: list[str] | None = None) -> list[str]:
    tags: list[str] = []
    for tag in [*base_tags, *(extra_tags or [])]:
        text = str(tag).strip()
        if text and text not in tags:
            tags.append(text)
    return tags


def latest_reports_by_tool(limit: int = 300) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in read_recent_report_index(limit=limit):
        tool_name = str(record.get("tool") or "")
        if tool_name:
            latest[tool_name] = record
    return latest


def get_recent_reports(limit: int = 80) -> list[dict[str, Any]]:
    return list(reversed(read_recent_report_index(limit=limit)))


def build_index_note(snapshot: dict[str, Any]) -> str:
    generated_at = snapshot["generated_at"]
    summary = snapshot["summary"]
    return f"""---
type: ai_desktop_assistant_index
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {generated_at}
---

# AI Desktop Assistant Map

Generated: `{generated_at}`

## Current Snapshot

{md_table(
    ["Metric", "Value"],
    [
        ["Feed readiness", summary["feed_readiness_status"]],
        ["Capability count", summary["capability_count"]],
        ["Recommendation queue", f"{summary['recommendation_pending_count']} pending / {summary['recommendation_total_count']} total"],
        ["External apps", f"{summary['external_apps_available']} available / {summary['external_apps_total']} total"],
        ["Latest Full System", summary["latest_full_system_status"]],
    ],
)}

## Maps

- {make_obsidian_link("10_System_Map/System Overview")}
- {make_obsidian_link("10_System_Map/System Flow")}
- {make_obsidian_link("20_Tools/Capability Map")}
- {make_obsidian_link("30_File_Database/Recommendation Queue")}
- {make_obsidian_link("30_File_Database/Action Policies")}
- {make_obsidian_link("40_Reports/Latest Reports")}
- {make_obsidian_link("50_Decisions/Safety Contract")}

## Rule

Obsidian is a read/review layer. Real file operations still go through Bot Controller, Selection Decision, File Operation Adapter, final token, report, manifest and Undo Manager.
"""


def build_system_overview_note(snapshot: dict[str, Any]) -> str:
    feed_summary = snapshot["feed_readiness"].get("summary", {})
    capability_summary = snapshot["capability_summary"]
    queue_summary = snapshot["recommendation_summary"]
    external_summary = snapshot["external_apps"].get("summary", {})
    action_policy_summary = snapshot["action_policy"].get("summary", {})
    latest_reports = snapshot["latest_reports"]

    rows = [
        ["Feed readiness", feed_summary.get("readiness_status"), f"{feed_summary.get('pass_count')} pass / {feed_summary.get('warn_count')} warn / {feed_summary.get('fail_count')} fail"],
        ["Capabilities", capability_summary.get("total"), json.dumps(capability_summary.get("by_risk", {}), ensure_ascii=False)],
        ["Recommendation queue", queue_summary.get("total"), f"{queue_summary.get('pending_count')} pending / {queue_summary.get('deferred_count')} deferred"],
        ["Action policy", action_policy_summary.get("total"), json.dumps(action_policy_summary.get("by_decision", {}), ensure_ascii=False)],
        ["External apps", external_summary.get("total"), f"{external_summary.get('available')} available / {external_summary.get('missing')} missing"],
    ]

    latest_rows = []
    for tool_name in [
        "full_system_tester",
        "tool_tester",
        "feed_readiness",
        "bot_controller",
        "file_operation_adapter",
        "system_advisor",
    ]:
        record = latest_reports.get(tool_name)
        if not record:
            latest_rows.append([tool_name, "-", "-", ""])
            continue
        latest_rows.append([
            tool_name,
            record.get("status"),
            record.get("created_at"),
            make_file_link(record.get("report_path")),
        ])

    return f"""---
type: system_overview
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
---

# System Overview

## Health

{md_table(["Area", "Value", "Detail"], rows)}

## Latest Core Reports

{md_table(["Tool", "Status", "Created", "Report"], latest_rows)}
"""


def build_system_flow_note(snapshot: dict[str, Any]) -> str:
    return f"""---
type: system_flow
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
---

# System Flow

```mermaid
flowchart TD
    A[System Advisor] --> B[Recommendation Center]
    B --> C[Action Policy]
    C --> D[Candidate Review]
    D --> E[Dry-run Action Planner]
    E --> F[AI Bot Controller]
    F --> G{{User Decision}}
    G -->|OK safe-only| H[Execution Adapter v1]
    G -->|Select| I[Selection UI]
    I -->|move_later| J[File Operation Adapter]
    J --> K[Dry-run Report]
    K -->|MOVE_SELECTION_V1| L[Move + Manifest]
    L --> M[Undo Manager]
    F --> N[Feed Readiness]
    B --> O[Obsidian Exporter]
    N --> O
```

Obsidian Exporter only documents the state. It does not approve, delete, move or clean files.
"""


def build_capability_note(snapshot: dict[str, Any]) -> str:
    capabilities = snapshot["capabilities"]
    rows = [
        [
            item["id"],
            item["category"],
            item["risk_level"],
            "yes" if item["mutates_files"] else "no",
            "yes" if item["needs_confirmation"] else "no",
            ",".join(item["external_apps"]) or "-",
            item["summary"],
        ]
        for item in capabilities
    ]
    return f"""---
type: capability_map
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
---

# Capability Map

{md_table(["ID", "Category", "Risk", "Mutates", "Confirm", "External Apps", "Summary"], rows)}
"""


def build_recommendation_note(snapshot: dict[str, Any], max_items: int = 80) -> str:
    queue = snapshot["recommendation_queue"][:max_items]
    rows = [
        [
            index,
            item.get("workflow_state"),
            item.get("severity"),
            item.get("id"),
            item.get("suggested_tool_id"),
            item.get("action_policy_decision") or "-",
            item.get("detail"),
        ]
        for index, item in enumerate(queue, start=1)
    ]
    return f"""---
type: recommendation_queue
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
---

# Recommendation Queue

{md_table(["#", "State", "Severity", "ID", "Tool", "Policy", "Detail"], rows)}
"""


def build_action_policy_note(snapshot: dict[str, Any], max_items: int = 120) -> str:
    policies = snapshot["policies"][:max_items]
    rows = [
        [
            index,
            item.get("decision"),
            item.get("target_type"),
            item.get("target"),
            item.get("reason"),
            item.get("source"),
        ]
        for index, item in enumerate(policies, start=1)
    ]
    return f"""---
type: action_policy
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
---

# Action Policies

{md_table(["#", "Decision", "Target Type", "Target", "Reason", "Source"], rows)}
"""


def build_latest_reports_note(snapshot: dict[str, Any], max_items: int = 80) -> str:
    rows = [
        [
            index,
            item.get("created_at"),
            item.get("tool"),
            item.get("action"),
            item.get("status"),
            item.get("risk_level"),
            make_file_link(item.get("report_path")),
        ]
        for index, item in enumerate(snapshot["recent_reports"][:max_items], start=1)
    ]
    return f"""---
type: latest_reports
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
---

# Latest Reports

{md_table(["#", "Created", "Tool", "Action", "Status", "Risk", "Report"], rows)}
"""


def build_safety_contract_note(snapshot: dict[str, Any]) -> str:
    return f"""---
type: safety_contract
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
---

# Safety Contract

- Advisor, Recommendation Center and Obsidian Exporter are review layers only.
- `OK` in Bot Controller must not auto-move or auto-delete unsafe items.
- `move_later` requires selected item, destination folder, dry-run and final token `MOVE_SELECTION_V1`.
- `delete_candidate` is still disabled for automated execution.
- File moves must use File Operation Adapter, `safe_move`, manifest and Undo Manager.
- Game data, app-managed folders, backups and guarded paths must stay manual/review-only unless user changes policy.
"""


def build_canvas(snapshot: dict[str, Any]) -> str:
    nodes = [
        {"id": "advisor", "type": "text", "text": "System Advisor", "x": 0, "y": 0, "width": 240, "height": 80},
        {"id": "queue", "type": "text", "text": "Recommendation Center", "x": 320, "y": 0, "width": 260, "height": 80},
        {"id": "policy", "type": "text", "text": "Action Policy", "x": 660, "y": 0, "width": 240, "height": 80},
        {"id": "bot", "type": "text", "text": "AI Bot Controller", "x": 980, "y": 0, "width": 260, "height": 80},
        {"id": "adapter", "type": "text", "text": "File Operation Adapter", "x": 1300, "y": 0, "width": 280, "height": 80},
        {"id": "undo", "type": "text", "text": "Undo Manager", "x": 1640, "y": 0, "width": 220, "height": 80},
        {"id": "obsidian", "type": "text", "text": "Obsidian Exporter\\nreview-only map", "x": 660, "y": 180, "width": 280, "height": 100},
    ]
    edges = [
        {"id": "e1", "fromNode": "advisor", "fromSide": "right", "toNode": "queue", "toSide": "left"},
        {"id": "e2", "fromNode": "queue", "fromSide": "right", "toNode": "policy", "toSide": "left"},
        {"id": "e3", "fromNode": "policy", "fromSide": "right", "toNode": "bot", "toSide": "left"},
        {"id": "e4", "fromNode": "bot", "fromSide": "right", "toNode": "adapter", "toSide": "left"},
        {"id": "e5", "fromNode": "adapter", "fromSide": "right", "toNode": "undo", "toSide": "left"},
        {"id": "e6", "fromNode": "queue", "fromSide": "bottom", "toNode": "obsidian", "toSide": "top"},
        {"id": "e7", "fromNode": "bot", "fromSide": "bottom", "toNode": "obsidian", "toSide": "right"},
    ]
    return json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2)


def build_export_snapshot(max_items: int = 80) -> dict[str, Any]:
    queue = collect_recommendation_queue(report_limit=max(max_items, 80), states=None)
    external_apps = build_external_apps_health()
    latest_reports = latest_reports_by_tool()
    return {
        "generated_at": now_text(),
        "capabilities": get_capabilities(),
        "capability_summary": summarize_capabilities(),
        "capability_validation": validate_capability_registry(),
        "recommendation_queue": queue,
        "recommendation_summary": summarize_recommendation_queue(queue),
        "action_policy": build_action_policy_health(),
        "policies": get_active_policies(),
        "feed_readiness": build_feed_readiness_result(),
        "external_apps": external_apps,
        "latest_reports": latest_reports,
        "recent_reports": get_recent_reports(limit=max_items),
    }


def build_snapshot_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    feed_summary = snapshot["feed_readiness"].get("summary", {})
    queue_summary = snapshot["recommendation_summary"]
    external_summary = snapshot["external_apps"].get("summary", {})
    latest_full_system = snapshot["latest_reports"].get("full_system_tester", {})
    return {
        "feed_readiness_status": feed_summary.get("readiness_status"),
        "capability_count": snapshot["capability_summary"].get("total", 0),
        "recommendation_total_count": queue_summary.get("total", 0),
        "recommendation_pending_count": queue_summary.get("pending_count", 0),
        "external_apps_total": external_summary.get("total", 0),
        "external_apps_available": external_summary.get("available", 0),
        "latest_full_system_status": latest_full_system.get("status") or "-",
    }


def build_notes(snapshot: dict[str, Any], max_items: int = 80) -> dict[str, str]:
    return {
        "00_Index.md": build_index_note(snapshot),
        "10_System_Map/System Overview.md": build_system_overview_note(snapshot),
        "10_System_Map/System Flow.md": build_system_flow_note(snapshot),
        "10_System_Map/System Flow.canvas": build_canvas(snapshot),
        "20_Tools/Capability Map.md": build_capability_note(snapshot),
        "30_File_Database/Recommendation Queue.md": build_recommendation_note(snapshot, max_items=max_items),
        "30_File_Database/Action Policies.md": build_action_policy_note(snapshot, max_items=max_items),
        "40_Reports/Latest Reports.md": build_latest_reports_note(snapshot, max_items=max_items),
        "50_Decisions/Safety Contract.md": build_safety_contract_note(snapshot),
    }


def write_note(vault_root: Path, relative_path: str, content: str) -> dict[str, Any]:
    path = vault_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)

    previous = None
    if path.exists():
        try:
            previous = path.read_text(encoding="utf-8")
        except OSError:
            previous = None

    if previous == content:
        status = "unchanged"
    else:
        path.write_text(content, encoding="utf-8")
        status = "updated" if previous is not None else "created"

    return {
        "path": str(path),
        "relative_path": relative_path,
        "status": status,
        "size": path.stat().st_size if path.exists() else 0,
    }


def build_obsidian_export_result(
    *,
    vault_root: str | Path | None = None,
    max_items: int = 80,
    write_files: bool = True,
) -> dict[str, Any]:
    vault = normalize_vault_root(vault_root)
    snapshot = build_export_snapshot(max_items=max_items)
    snapshot["summary"] = build_snapshot_summary(snapshot)
    notes = build_notes(snapshot, max_items=max_items)

    written_files = []
    if write_files:
        vault.mkdir(parents=True, exist_ok=True)
        for relative_path, content in notes.items():
            written_files.append(write_note(vault, relative_path, content))

    statuses: dict[str, int] = {}
    for item in written_files:
        status = item["status"]
        statuses[status] = statuses.get(status, 0) + 1

    summary = {
        "vault_root": str(vault),
        "schema": OBSIDIAN_EXPORT_SCHEMA,
        "note_count": len(notes),
        "written_count": len(written_files),
        "created_count": statuses.get("created", 0),
        "updated_count": statuses.get("updated", 0),
        "unchanged_count": statuses.get("unchanged", 0),
        "recommendation_count": snapshot["recommendation_summary"].get("total", 0),
        "pending_recommendation_count": snapshot["recommendation_summary"].get("pending_count", 0),
        "capability_count": snapshot["capability_summary"].get("total", 0),
        "feed_readiness_status": snapshot["feed_readiness"].get("summary", {}).get("readiness_status"),
        "external_apps_available": snapshot["external_apps"].get("summary", {}).get("available", 0),
    }

    return {
        "schema": OBSIDIAN_EXPORT_SCHEMA,
        "status": "success",
        "vault_root": str(vault),
        "summary": summary,
        "files": written_files,
        "safety_contract": {
            "read_only_source_data": True,
            "writes_only_vault_files": True,
            "executes_file_operations": False,
            "deletes_files": False,
            "moves_user_files": False,
            "default_vault_root": str(DEFAULT_VAULT_DIR),
        },
    }


def export_obsidian_vault(
    *,
    vault_root: str | Path | None = None,
    max_items: int = 80,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    result = build_obsidian_export_result(
        vault_root=vault_root,
        max_items=max_items,
        write_files=True,
    )
    report = create_report(
        tool_name=OBSIDIAN_EXPORTER_TOOL,
        action="export_vault",
        status=result["status"],
        risk_level="safe",
        input_data={
            "vault_root": result["vault_root"],
            "max_items": max_items,
        },
        results=result,
        recommendations=[
            "Open the vault_root folder in Obsidian to view the generated map.",
            "Use Obsidian as a review layer only; run file actions through the assistant adapters.",
        ],
        summary=result["summary"],
        undo_available=False,
        tags=merge_report_tags(["obsidian", "export", "read_only_map"], extra_tags),
    )
    log_action(
        OBSIDIAN_EXPORTER_TOOL,
        "export_obsidian_vault",
        result["status"],
        {
            "report": str(report),
            "vault_root": result["vault_root"],
            "written_count": result["summary"]["written_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": result["status"],
        "report": str(report),
        "result": result,
    }


def print_export_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== OBSIDIAN EXPORTER ==========")
    print(f"Vault: {summary['vault_root']}")
    print(f"Notes: {summary['note_count']}")
    print(f"Created: {summary['created_count']}")
    print(f"Updated: {summary['updated_count']}")
    print(f"Unchanged: {summary['unchanged_count']}")
    print(f"Recommendations: {summary['recommendation_count']}")
    print(f"Pending recommendations: {summary['pending_recommendation_count']}")
    print(f"Feed readiness: {summary['feed_readiness_status']}")


def run_obsidian_exporter() -> None:
    while True:
        print("""
========== OBSIDIAN EXPORTER ==========
1. Preview export summary
2. Export default vault
3. Export custom vault
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            result = build_obsidian_export_result(write_files=False)
            print_export_summary(result)

        elif choice == "2":
            exported = export_obsidian_vault()
            print_export_summary(exported["result"])

        elif choice == "3":
            raw = input("Nhap folder vault Obsidian: ").strip().strip('"')
            max_items_raw = input("So item toi da moi bang [80]: ").strip()
            max_items = int(max_items_raw) if max_items_raw else 80
            exported = export_obsidian_vault(vault_root=raw, max_items=max_items)
            print_export_summary(exported["result"])

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_obsidian_exporter()
