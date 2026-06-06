from __future__ import annotations

import json
import re
import hashlib
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
from tools.core.safe_executor import delete_managed_generated_file, remove_empty_managed_dirs


OBSIDIAN_EXPORTER_TOOL = "obsidian_exporter"
OBSIDIAN_EXPORT_SCHEMA = "obsidian_export_v1"
DEFAULT_VAULT_DIR = BASE_DIR / "obsidian_vault"
GRAPH_NODE_DIR = "60_Graph_Nodes"
WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:\\")
INVALID_FILENAME_CHARS = r'<>:"/\|?*'
GENERATED_GRAPH_TYPE_MARKERS = {
    "type: tool",
    "type: external_app",
    "type: report",
    "type: policy",
    "type: recommendation",
    "type: decision",
    "type: file_node",
    "type: folder_node",
    "type: graph_hub",
}


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


def make_obsidian_alias_link(path: str, alias: str | None = None) -> str:
    return f"[[{path}|{alias or Path(path).name}]]"


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


def short_hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:10]


def safe_filename(value: Any, *, fallback: str = "node", max_length: int = 90) -> str:
    text = str(value or "").strip() or fallback
    for char in INVALID_FILENAME_CHARS:
        text = text.replace(char, "_")
    text = re.sub(r"\s+", " ", text).strip(" .")
    if not text:
        text = fallback
    return text[:max_length]


def yaml_quote(value: Any) -> str:
    return "'" + str(value if value is not None else "").replace("'", "''") + "'"


def graph_note_path(kind: str, key: Any, label: str | None = None) -> str:
    name = safe_filename(label or key, fallback=kind)
    return f"{GRAPH_NODE_DIR}/{kind}/{name} - {short_hash(key)}"


def looks_like_windows_path(value: Any) -> bool:
    text = str(value or "").strip()
    if not WINDOWS_PATH_RE.match(text):
        return False
    return len(text) >= 4 and any(separator in text for separator in ("\\", "/"))


def iter_nested_strings(value: Any, *, depth: int = 0) -> list[str]:
    if depth > 8:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(iter_nested_strings(item, depth=depth + 1))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(iter_nested_strings(item, depth=depth + 1))
        return strings
    return []


def collect_path_values(value: Any, *, limit: int = 160) -> list[str]:
    paths: list[str] = []
    seen = set()
    for text in iter_nested_strings(value):
        cleaned = text.strip()
        if not looks_like_windows_path(cleaned) or cleaned in seen:
            continue
        seen.add(cleaned)
        paths.append(cleaned)
        if len(paths) >= limit:
            break
    return paths


def get_tool_node_path(tool_id: str) -> str:
    return graph_note_path("Tools", tool_id, tool_id)


def get_external_app_node_path(app_name: str) -> str:
    return graph_note_path("External Apps", app_name, app_name)


def get_decision_node_path(decision: str) -> str:
    return graph_note_path("Decisions", decision, f"decision {decision}")


def get_report_node_path(record: dict[str, Any]) -> str:
    key = record.get("report_path") or f"{record.get('tool')}-{record.get('created_at')}"
    label = f"{record.get('tool', 'report')} {record.get('created_at', '')}"
    return graph_note_path("Reports", key, label)


def get_recommendation_node_path(item: dict[str, Any]) -> str:
    key = item.get("fingerprint") or item.get("id") or item.get("detail")
    label = item.get("id") or item.get("title") or "recommendation"
    return graph_note_path("Recommendations", key, label)


def get_policy_node_path(item: dict[str, Any]) -> str:
    key = item.get("fingerprint") or f"{item.get('target_type')}:{item.get('target')}"
    label = f"{item.get('decision', 'policy')} {item.get('target_type', '')}"
    return graph_note_path("Policies", key, label)


def get_path_node_path(path_value: str) -> str:
    path = Path(path_value)
    kind = "Folders" if not path.suffix else "Files"
    label = path.name or path_value.replace("\\", "_")
    return graph_note_path(kind, path_value, label)


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
- {make_obsidian_link("10_System_Map/Graph View Guide")}
- {make_obsidian_link("60_Graph_Nodes/Graph Hub")}
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


def build_graph_view_guide_note(snapshot: dict[str, Any]) -> str:
    return f"""---
type: graph_view_guide
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
tags:
  - graph_guide
---

# Graph View Guide

Use this when you want the visual graph view, not the table notes.

1. Open {make_obsidian_link("60_Graph_Nodes/Graph Hub")}.
2. Open Obsidian Graph view or Local Graph.
3. Turn on arrows if you want relationship direction.
4. Group nodes with these filters:
   - `path:60_Graph_Nodes/Tools`
   - `path:60_Graph_Nodes/External Apps`
   - `path:60_Graph_Nodes/Reports`
   - `path:60_Graph_Nodes/Policies`
   - `path:60_Graph_Nodes/Files`
   - `path:60_Graph_Nodes/Folders`
   - `path:60_Graph_Nodes/Decisions`
5. If the global graph is too dense, use Local Graph from `Graph Hub`.

Important: these nodes are review-only. Real actions still go through Bot Controller and adapters.
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


def safe_read_report_data(report_path: str | Path | None) -> dict[str, Any] | None:
    if not report_path:
        return None
    path = Path(report_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def should_include_path_node(path_value: str) -> bool:
    text = str(path_value or "").strip()
    if not looks_like_windows_path(text):
        return False

    lower = text.lower()
    ignored_prefixes = [
        str(BASE_DIR / "reports").lower(),
        str(BASE_DIR / "backups").lower(),
        str(BASE_DIR / "obsidian_vault").lower(),
        str(BASE_DIR / "__pycache__").lower(),
        r"d:\_ai_desktop_assistant_scenario_tests".lower(),
    ]
    return not any(lower.startswith(prefix) for prefix in ignored_prefixes)


def build_path_graph_index(snapshot: dict[str, Any], max_items: int = 80) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}

    def add_path(path_value: str, source_link: str, source_label: str) -> None:
        if not should_include_path_node(path_value):
            return
        record = nodes.setdefault(path_value, {
            "path": path_value,
            "sources": [],
        })
        source = {
            "link": source_link,
            "label": source_label,
        }
        if source not in record["sources"]:
            record["sources"].append(source)

    for policy in snapshot["policies"]:
        target = str(policy.get("target") or "")
        if str(policy.get("target_type") or "").startswith("path"):
            add_path(target, get_policy_node_path(policy), "policy")

    for app in snapshot["external_apps"].get("apps", []):
        app_path = str(app.get("path") or "")
        add_path(app_path, get_external_app_node_path(str(app.get("name") or "")), "external_app")

    for report in snapshot["recent_reports"][:max_items]:
        report_data = safe_read_report_data(report.get("report_path"))
        if not report_data:
            continue
        report_link = get_report_node_path(report)
        for path_value in collect_path_values(report_data, limit=30):
            add_path(path_value, report_link, str(report.get("tool") or "report"))
            if len(nodes) >= max_items * 2:
                return nodes

    return nodes


def build_graph_hub_note(snapshot: dict[str, Any], graph_notes: dict[str, str]) -> str:
    links = [
        make_obsidian_link("00_Index"),
        make_obsidian_link("20_Tools/Capability Map"),
        make_obsidian_link("30_File_Database/Action Policies"),
        make_obsidian_link("40_Reports/Latest Reports"),
        make_obsidian_link("50_Decisions/Safety Contract"),
    ]
    for relative_path in sorted(graph_notes)[:120]:
        note_path = relative_path[:-3] if relative_path.endswith(".md") else relative_path
        links.append(make_obsidian_link(note_path))

    return f"""---
type: graph_hub
schema: {OBSIDIAN_EXPORT_SCHEMA}
generated_at: {snapshot["generated_at"]}
tags:
  - graph_hub
---

# Graph Hub

This note intentionally links graph nodes together so Obsidian Graph has a real network to render.

## Entry Links

{chr(10).join(f"- {link}" for link in links)}
"""


def build_tool_node(item: dict[str, Any], snapshot: dict[str, Any]) -> str:
    tool_id = item["id"]
    external_links = [
        make_obsidian_alias_link(get_external_app_node_path(app), app)
        for app in item.get("external_apps", [])
    ]
    latest_report = snapshot["latest_reports"].get(tool_id)
    report_link = (
        make_obsidian_alias_link(get_report_node_path(latest_report), "latest report")
        if latest_report else "-"
    )
    return f"""---
type: tool
tool_id: {tool_id}
category: {item["category"]}
risk: {item["risk_level"]}
mutates_files: {str(bool(item["mutates_files"])).lower()}
needs_confirmation: {str(bool(item["needs_confirmation"])).lower()}
tags:
  - tool
  - risk_{item["risk_level"]}
  - category_{item["category"]}
---

# {item["name"]}

Summary: {item["summary"]}

## Links

- Capability Map: {make_obsidian_link("20_Tools/Capability Map")}
- Safety Contract: {make_obsidian_link("50_Decisions/Safety Contract")}
- Latest report: {report_link}

## External Apps

{chr(10).join(f"- {link}" for link in external_links) if external_links else "_No external apps._"}
"""


def build_external_app_node(app: dict[str, Any], snapshot: dict[str, Any]) -> str:
    app_name = str(app.get("name") or "unknown_app")
    dependent_links = [
        make_obsidian_alias_link(get_tool_node_path(tool_id), tool_id)
        for tool_id in app.get("dependent_tools", [])
    ]
    path_link = ""
    app_path = str(app.get("path") or "")
    if should_include_path_node(app_path):
        path_link = make_obsidian_alias_link(get_path_node_path(app_path), Path(app_path).name)
    return f"""---
type: external_app
app_id: {app_name}
available: {str(bool(app.get("available"))).lower()}
tags:
  - external_app
  - app_state_{app.get("state", "unknown")}
---

# {app_name}

Path: `{app.get("path") or ""}`

Path node: {path_link or "-"}

Impact: {app.get("impact") or ""}

## Dependent Tools

{chr(10).join(f"- {link}" for link in dependent_links) if dependent_links else "_No direct dependent tools._"}
"""


def build_report_node(record: dict[str, Any], snapshot: dict[str, Any]) -> str:
    tool_name = str(record.get("tool") or "unknown_tool")
    tool = next((item for item in snapshot["capabilities"] if item["id"] == tool_name), None)
    tool_link = (
        make_obsidian_alias_link(get_tool_node_path(tool_name), tool_name)
        if tool else tool_name
    )
    report_path = str(record.get("report_path") or "")
    return f"""---
type: report
tool: {tool_name}
status: {record.get("status")}
risk: {record.get("risk_level")}
tags:
  - report
  - report_status_{record.get("status")}
---

# {tool_name} report

- Tool: {tool_link}
- Action: `{record.get("action")}`
- Created: `{record.get("created_at")}`
- Status: `{record.get("status")}`
- Local file: {make_file_link(report_path)}
"""


def build_policy_node(policy: dict[str, Any], snapshot: dict[str, Any]) -> str:
    decision = str(policy.get("decision") or "manual_only")
    target = str(policy.get("target") or "")
    path_link = ""
    if str(policy.get("target_type") or "").startswith("path") and should_include_path_node(target):
        path_link = make_obsidian_alias_link(get_path_node_path(target), Path(target).name or target)
    return f"""---
type: policy
decision: {decision}
target_type: {policy.get("target_type")}
tags:
  - policy
  - decision_{decision}
---

# Policy {decision}

- Decision: {make_obsidian_alias_link(get_decision_node_path(decision), decision)}
- Target type: `{policy.get("target_type")}`
- Target: `{target}`
- Target node: {path_link or "-"}
- Reason: {policy.get("reason") or ""}
- Source: `{policy.get("source") or ""}`
"""


def build_recommendation_node(item: dict[str, Any], snapshot: dict[str, Any]) -> str:
    tool_id = str(item.get("suggested_tool_id") or "")
    tool_link = (
        make_obsidian_alias_link(get_tool_node_path(tool_id), tool_id)
        if tool_id else "-"
    )
    policy_decision = str(item.get("action_policy_decision") or "")
    policy_link = (
        make_obsidian_alias_link(get_decision_node_path(policy_decision), policy_decision)
        if policy_decision else "-"
    )
    return f"""---
type: recommendation
state: {item.get("workflow_state")}
severity: {item.get("severity")}
tags:
  - recommendation
  - recommendation_state_{item.get("workflow_state")}
---

# {item.get("id") or item.get("title") or "Recommendation"}

- Suggested tool: {tool_link}
- Policy decision: {policy_link}
- Report: `{item.get("report_path") or ""}`

{item.get("detail") or ""}
"""


def build_decision_node(decision: str, snapshot: dict[str, Any]) -> str:
    return f"""---
type: decision
decision: {decision}
tags:
  - decision
  - decision_{decision}
---

# Decision: {decision}

Linked safety contract: {make_obsidian_link("50_Decisions/Safety Contract")}

This node groups policies and recommendation items that mention `{decision}`.
"""


def build_path_node(path_record: dict[str, Any], snapshot: dict[str, Any]) -> str:
    path_value = path_record["path"]
    path = Path(path_value)
    kind = "folder" if not path.suffix else "file"
    source_links = [
        make_obsidian_alias_link(source["link"], source["label"])
        for source in path_record.get("sources", [])
    ]
    parent_link = ""
    parent = str(path.parent)
    if parent != path_value and should_include_path_node(parent):
        parent_link = make_obsidian_alias_link(get_path_node_path(parent), Path(parent).name or parent)

    return f"""---
type: {kind}_node
path: {yaml_quote(path_value)}
tags:
  - file_database
  - {kind}_node
---

# {path.name or path_value}

Path: `{path_value}`

Parent: {parent_link or "-"}

## Sources

{chr(10).join(f"- {link}" for link in source_links) if source_links else "_No source links._"}
"""


def build_graph_notes(snapshot: dict[str, Any], max_items: int = 80) -> dict[str, str]:
    notes: dict[str, str] = {}

    for capability in snapshot["capabilities"]:
        notes[f"{get_tool_node_path(capability['id'])}.md"] = build_tool_node(capability, snapshot)

    for app in snapshot["external_apps"].get("apps", []):
        app_name = str(app.get("name") or "unknown_app")
        notes[f"{get_external_app_node_path(app_name)}.md"] = build_external_app_node(app, snapshot)

    for decision in ["keep", "manual_only", "needs_backup", "move_later", "delete_candidate", "ignore_forever", "skip"]:
        notes[f"{get_decision_node_path(decision)}.md"] = build_decision_node(decision, snapshot)

    for record in snapshot["recent_reports"][:max_items]:
        notes[f"{get_report_node_path(record)}.md"] = build_report_node(record, snapshot)

    for policy in snapshot["policies"][:max_items]:
        notes[f"{get_policy_node_path(policy)}.md"] = build_policy_node(policy, snapshot)

    for item in snapshot["recommendation_queue"][:max_items]:
        notes[f"{get_recommendation_node_path(item)}.md"] = build_recommendation_node(item, snapshot)

    path_index = build_path_graph_index(snapshot, max_items=max_items)
    for path_value, record in path_index.items():
        notes[f"{get_path_node_path(path_value)}.md"] = build_path_node(record, snapshot)

    notes[f"{GRAPH_NODE_DIR}/Graph Hub.md"] = build_graph_hub_note(snapshot, notes)
    return notes


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
    base_notes = {
        "00_Index.md": build_index_note(snapshot),
        "10_System_Map/System Overview.md": build_system_overview_note(snapshot),
        "10_System_Map/System Flow.md": build_system_flow_note(snapshot),
        "10_System_Map/Graph View Guide.md": build_graph_view_guide_note(snapshot),
        "10_System_Map/System Flow.canvas": build_canvas(snapshot),
        "20_Tools/Capability Map.md": build_capability_note(snapshot),
        "30_File_Database/Recommendation Queue.md": build_recommendation_note(snapshot, max_items=max_items),
        "30_File_Database/Action Policies.md": build_action_policy_note(snapshot, max_items=max_items),
        "40_Reports/Latest Reports.md": build_latest_reports_note(snapshot, max_items=max_items),
        "50_Decisions/Safety Contract.md": build_safety_contract_note(snapshot),
    }
    return {
        **base_notes,
        **build_graph_notes(snapshot, max_items=max_items),
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


def is_generated_obsidian_note(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8")[:500].lower()
    except OSError:
        return False
    return (
        f"schema: {OBSIDIAN_EXPORT_SCHEMA}".lower() in head
        or any(marker in head for marker in GENERATED_GRAPH_TYPE_MARKERS)
    )


def prune_stale_graph_notes(vault_root: Path, target_relative_paths: set[str]) -> list[dict[str, Any]]:
    graph_root = vault_root / GRAPH_NODE_DIR
    if not graph_root.exists():
        return []

    target_paths = {
        vault_root / relative_path
        for relative_path in target_relative_paths
        if relative_path.startswith(f"{GRAPH_NODE_DIR}/")
    }
    removed = []

    for path in graph_root.rglob("*.md"):
        if path in target_paths:
            continue
        if not is_generated_obsidian_note(path):
            continue

        delete_result = delete_managed_generated_file(
            path,
            allowed_root=graph_root,
            marker_check=is_generated_obsidian_note,
        )
        if delete_result["status"] in {"deleted", "error"}:
            removed.append(delete_result)

    remove_empty_managed_dirs(graph_root)
    return removed


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
    pruned_files = []
    if write_files:
        vault.mkdir(parents=True, exist_ok=True)
        pruned_files = prune_stale_graph_notes(vault, set(notes))
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
        "graph_node_count": sum(1 for path in notes if path.startswith(f"{GRAPH_NODE_DIR}/")),
        "written_count": len(written_files),
        "pruned_count": sum(1 for item in pruned_files if item["status"] == "deleted"),
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
        "pruned_files": pruned_files,
        "safety_contract": {
            "read_only_source_data": True,
            "writes_only_vault_files": True,
            "prunes_generated_graph_nodes": True,
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
    print(f"Graph nodes: {summary['graph_node_count']}")
    print(f"Pruned stale graph nodes: {summary['pruned_count']}")
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
