from __future__ import annotations

from typing import Any

from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report


REQUIRED_CAPABILITY_FIELDS = {
    "id",
    "name",
    "category",
    "module",
    "function",
    "risk_level",
    "mutates_files",
    "needs_confirmation",
    "undo_strategy",
    "creates_report",
    "logs_action",
    "external_apps",
    "tags",
    "summary",
}

ALLOWED_RISK_LEVELS = {"safe", "medium", "dangerous"}
ALLOWED_UNDO_STRATEGIES = {
    "none",
    "not_needed",
    "manifest_restore",
    "recycle_bin",
    "manual",
    "irreversible",
}


CAPABILITIES: list[dict[str, Any]] = [
    {
        "id": "disk_checker",
        "name": "Disk Checker",
        "category": "system",
        "module": "tools.system.disk_checker",
        "function": "check_disk",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": ["smartctl"],
        "tags": ["system", "disk", "smart"],
        "summary": "Read disk usage and SMART health when smartctl is available.",
    },
    {
        "id": "process_monitor",
        "name": "Process Monitor",
        "category": "system",
        "module": "tools.system.process_monitor",
        "function": "show_top_process",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": ["sysinternals_procexp", "sysinternals_handle", "sysinternals_rammap"],
        "tags": ["system", "process", "ram"],
        "summary": "Read top RAM/CPU processes and report diagnostic helper availability.",
    },
    {
        "id": "recycle_bin_cleaner",
        "name": "Recycle Bin Cleaner",
        "category": "system",
        "module": "tools.system.recycle_bin_cleaner",
        "function": "clear_recycle_bin",
        "risk_level": "dangerous",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "irreversible",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["cleanup", "recycle_bin", "dangerous"],
        "summary": "Preview and empty Recycle Bin with multi-step confirmation.",
    },
    {
        "id": "junk_file_cleaner",
        "name": "Junk File Cleaner",
        "category": "system",
        "module": "tools.system.junk_file_cleaner",
        "function": "run_junk_cleaner",
        "risk_level": "dangerous",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "recycle_bin",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["cleanup", "junk", "safe_executor"],
        "summary": "Scan junk files, classify risk, and send selected items to Recycle Bin.",
    },
    {
        "id": "duplicate_finder",
        "name": "Duplicate Finder",
        "category": "storage",
        "module": "tools.storage.duplicate_finder",
        "function": "run_duplicate_finder",
        "risk_level": "dangerous",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "recycle_bin",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["storage", "duplicates", "hash"],
        "summary": "Find duplicate files by SHA256 and delete selected duplicates through safety layer.",
    },
    {
        "id": "temp_cleaner",
        "name": "Temp Cleaner",
        "category": "storage",
        "module": "tools.storage.temp_cleaner",
        "function": "run_temp_cleaner",
        "risk_level": "dangerous",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "recycle_bin",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["cleanup", "temp", "safe_executor"],
        "summary": "Scan temp files, classify risk, and delete selected safe items.",
    },
    {
        "id": "media_organizer",
        "name": "Media Organizer",
        "category": "storage",
        "module": "tools.storage.media_organizer",
        "function": "run_media_organizer",
        "risk_level": "medium",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "manifest_restore",
        "creates_report": True,
        "logs_action": True,
        "external_apps": ["exiftool", "ffprobe"],
        "tags": ["storage", "media", "metadata", "manifest"],
        "summary": "Move selected media into a target folder with manifest restore; metadata mode is read-only.",
    },
    {
        "id": "empty_folder_finder",
        "name": "Empty Folder Finder",
        "category": "storage",
        "module": "tools.storage.empty_folder_finder",
        "function": "run_empty_folder_finder",
        "risk_level": "dangerous",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "recycle_bin",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["cleanup", "empty_folders", "safe_executor"],
        "summary": "Find empty folders and send selected folders to Recycle Bin.",
    },
    {
        "id": "file_indexer",
        "name": "File Indexer",
        "category": "search",
        "module": "tools.search.file_indexer",
        "function": "run_file_indexer",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": False,
        "external_apps": ["everything_cli"],
        "tags": ["search", "index", "everything"],
        "summary": "Build local file index or search quickly through Everything CLI with local fallback.",
    },
    {
        "id": "startup_launcher",
        "name": "Startup Launcher",
        "category": "automation",
        "module": "tools.automation.startup_launcher",
        "function": "run_startup_launcher",
        "risk_level": "medium",
        "mutates_files": True,
        "needs_confirmation": False,
        "undo_strategy": "manual",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["automation", "startup", "profile"],
        "summary": "Manage startup profiles and launch configured apps.",
    },
    {
        "id": "download_organizer",
        "name": "Download Organizer",
        "category": "automation",
        "module": "tools.automation.download_organizer",
        "function": "run_download_organizer",
        "risk_level": "medium",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "manifest_restore",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["automation", "downloads", "manifest"],
        "summary": "Move selected Downloads files into date/category folders with manifest restore.",
    },
    {
        "id": "download_watcher",
        "name": "Download Watcher",
        "category": "automation",
        "module": "tools.automation.download_watcher",
        "function": "run_download_watcher",
        "risk_level": "medium",
        "mutates_files": True,
        "needs_confirmation": False,
        "undo_strategy": "manifest_restore",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["automation", "downloads", "watcher"],
        "summary": "Watch Downloads and move completed files after stable-size checks.",
    },
    {
        "id": "browser_cache_cleaner",
        "name": "Browser Cache Cleaner",
        "category": "system",
        "module": "tools.system.browser_cache_cleaner",
        "function": "run_browser_cache_cleaner",
        "risk_level": "dangerous",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "recycle_bin",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["cleanup", "browser_cache", "safe_executor"],
        "summary": "Detect browser cache folders and clean selected cache entries through safety layer.",
    },
    {
        "id": "game_booster",
        "name": "Game Booster",
        "category": "system",
        "module": "tools.system.game_booster",
        "function": "run_game_booster",
        "risk_level": "medium",
        "mutates_files": False,
        "needs_confirmation": True,
        "undo_strategy": "manual",
        "creates_report": False,
        "logs_action": False,
        "external_apps": [],
        "tags": ["system", "process", "game"],
        "summary": "Tune process priority and optionally terminate selected background processes.",
    },
    {
        "id": "natural_command",
        "name": "Natural Command",
        "category": "search",
        "module": "tools.search.natural_command",
        "function": "run_natural_command",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": False,
        "logs_action": False,
        "external_apps": ["everything_cli"],
        "tags": ["command", "search"],
        "summary": "Route normalized natural-language commands through Capability Registry with risk confirmation.",
    },
    {
        "id": "folder_size_analyzer",
        "name": "Folder Size Analyzer",
        "category": "storage",
        "module": "tools.storage.folder_size_analyzer",
        "function": "run_folder_size_analyzer",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": ["wiztree"],
        "tags": ["storage", "folder_size"],
        "summary": "Analyze top folders by size; WizTree adapter can provide faster storage data elsewhere.",
    },
    {
        "id": "large_file_finder",
        "name": "Large File Finder",
        "category": "storage",
        "module": "tools.storage.large_file_finder",
        "function": "run_large_file_finder",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": ["wiztree"],
        "tags": ["storage", "large_files"],
        "summary": "Find large files and open file locations for manual review.",
    },
    {
        "id": "system_advisor",
        "name": "System Advisor",
        "category": "storage",
        "module": "tools.storage.system_advisor",
        "function": "run_system_advisor",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": ["wiztree", "smartctl"],
        "tags": ["advisor", "storage", "system"],
        "summary": "Build read-only system snapshots and structured recommendations with suggested next tools.",
    },
    {
        "id": "assistant_logger",
        "name": "Assistant Logger",
        "category": "core",
        "module": "tools.core.assistant_logger",
        "function": "run_assistant_logger",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": False,
        "logs_action": False,
        "external_apps": [],
        "tags": ["core", "logs"],
        "summary": "View assistant action logs.",
    },
    {
        "id": "audit_center",
        "name": "Audit Center",
        "category": "core",
        "module": "tools.core.audit_center",
        "function": "run_audit_center",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": False,
        "external_apps": [],
        "tags": ["core", "audit", "reports"],
        "summary": "Read action logs and report index, then export audit snapshots.",
    },
    {
        "id": "behavior_tester",
        "name": "Behavior Tester",
        "category": "core",
        "module": "tools.core.behavior_tester",
        "function": "run_behavior_tester",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": False,
        "external_apps": [],
        "tags": ["core", "tests", "sandbox"],
        "summary": "Run behavior tests in a sandbox without touching real user data.",
    },
    {
        "id": "config_manager",
        "name": "Config Manager",
        "category": "core",
        "module": "tools.core.config_manager",
        "function": "run_config_manager",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "config"],
        "summary": "Validate config and export config snapshots.",
    },
    {
        "id": "undo_manager",
        "name": "Undo Manager",
        "category": "core",
        "module": "tools.core.undo_manager",
        "function": "run_undo_manager",
        "risk_level": "medium",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "manual",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "undo", "manifest"],
        "summary": "Preview and restore move manifests from backups.",
    },
    {
        "id": "full_system_tester",
        "name": "Full System Tester",
        "category": "core",
        "module": "tools.core.full_system_tester",
        "function": "run_full_system_tester",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": False,
        "external_apps": [],
        "tags": ["core", "tests", "system"],
        "summary": "Run compile, import, config, safety, behavior and integration checks.",
    },
    {
        "id": "wiztree_adapter",
        "name": "WizTree Adapter",
        "category": "storage",
        "module": "tools.storage.wiztree_adapter",
        "function": "run_wiztree_adapter",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": True,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": ["wiztree"],
        "tags": ["storage", "wiztree", "read_only"],
        "summary": "Run WizTree read-only CSV scans and parse top folders/large files.",
    },
    {
        "id": "external_apps_manager",
        "name": "External Apps Manager",
        "category": "core",
        "module": "tools.core.external_apps",
        "function": "run_external_apps_manager",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "external_apps"],
        "summary": "Show external app status, versions and reports.",
    },
    {
        "id": "capability_registry",
        "name": "Capability Registry",
        "category": "core",
        "module": "tools.core.capability_registry",
        "function": "run_capability_registry",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "capabilities"],
        "summary": "List and validate the official tool capability map.",
    },
    {
        "id": "recommendation_center",
        "name": "Recommendation Center",
        "category": "core",
        "module": "tools.core.recommendation_center",
        "function": "run_recommendation_center",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "recommendations", "queue", "read_only"],
        "summary": "Collect read-only recommendations from Advisor and Audit reports into a review queue.",
    },
    {
        "id": "guided_action_runner",
        "name": "Guided Action Runner",
        "category": "core",
        "module": "tools.core.guided_action_runner",
        "function": "run_guided_action_runner",
        "risk_level": "medium",
        "mutates_files": False,
        "needs_confirmation": True,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "recommendations", "guided_action", "confirmation"],
        "summary": "Open suggested tools from recommendations with an explicit risk/confirmation gate.",
    },
    {
        "id": "feed_readiness",
        "name": "Feed Assistant Readiness",
        "category": "core",
        "module": "tools.core.feed_readiness",
        "function": "run_feed_readiness",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "assistant", "pre_feed", "read_only"],
        "summary": "Check whether reports, registry, external apps and queue state are ready for assistant feed.",
    },
    {
        "id": "scenario_tester",
        "name": "Scenario Tester",
        "category": "core",
        "module": "tools.core.scenario_tester",
        "function": "run_scenario_tester",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "tests", "sandbox", "fake_files", "scenarios"],
        "summary": "Run fake-file sandbox scenarios for Downloads, media, storage and cleanup guardrails.",
    },
    {
        "id": "action_policy",
        "name": "Action Policy Manager",
        "category": "core",
        "module": "tools.core.action_policy",
        "function": "run_action_policy_manager",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "policy", "decision_layer", "read_only"],
        "summary": "Manage read-only action policies for keep/move/delete/manual decisions before automation.",
    },
    {
        "id": "candidate_review",
        "name": "Candidate Review",
        "category": "core",
        "module": "tools.core.candidate_review",
        "function": "run_candidate_review",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "review", "policy", "read_only"],
        "summary": "Review deferred archive/video candidates with action policy coverage before planning actions.",
    },
    {
        "id": "action_planner",
        "name": "Dry-run Action Planner",
        "category": "core",
        "module": "tools.core.action_planner",
        "function": "run_action_planner",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "planner", "dry_run", "read_only"],
        "summary": "Build a dry-run plan from candidate review and action policy without executing cleanup.",
    },
    {
        "id": "pre_feed_bundle",
        "name": "Pre-feed Bundle",
        "category": "core",
        "module": "tools.core.pre_feed_bundle",
        "function": "run_pre_feed_bundle",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "assistant", "pre_feed", "read_only"],
        "summary": "Export curated docs, summaries, policy, queue and readiness context for assistant feed preparation.",
    },
    {
        "id": "bot_controller",
        "name": "AI Bot Controller",
        "category": "core",
        "module": "tools.core.bot_controller",
        "function": "run_bot_controller",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "bot", "orchestrator", "auto_check", "read_only"],
        "summary": "Single entrypoint that orchestrates recommendations, policy gates, candidate review, action planning and selection decision reports.",
    },
    {
        "id": "execution_adapter",
        "name": "Execution Adapter",
        "category": "core",
        "module": "tools.core.execution_adapter",
        "function": "run_execution_adapter",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": True,
        "undo_strategy": "not_needed",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "execution", "adapter", "guarded_execution", "read_only_v1"],
        "summary": "Validate Selection Decision reports and record safe decisions while blocking file operations in v1.",
    },
    {
        "id": "file_operation_adapter",
        "name": "File Operation Adapter",
        "category": "core",
        "module": "tools.core.file_operation_adapter",
        "function": "run_file_operation_adapter",
        "risk_level": "medium",
        "mutates_files": True,
        "needs_confirmation": True,
        "undo_strategy": "manifest_restore",
        "creates_report": True,
        "logs_action": True,
        "external_apps": [],
        "tags": ["core", "file_operation", "move_later", "manifest_restore", "guarded_execution"],
        "summary": "Move selected move_later decisions to an explicit destination with safe_move, final token and manifest restore.",
    },
    {
        "id": "file_location_opener",
        "name": "File Location Opener",
        "category": "core",
        "module": "tools.core.file_location_opener",
        "function": "open_file_location",
        "risk_level": "safe",
        "mutates_files": False,
        "needs_confirmation": False,
        "undo_strategy": "not_needed",
        "creates_report": False,
        "logs_action": False,
        "external_apps": [],
        "tags": ["core", "explorer", "helper"],
        "summary": "Open Windows Explorer at a selected file location.",
    },
]


def get_capabilities() -> list[dict[str, Any]]:
    return [dict(item) for item in CAPABILITIES]


def get_capability_by_id(capability_id: str) -> dict[str, Any] | None:
    for capability in CAPABILITIES:
        if capability["id"] == capability_id:
            return dict(capability)
    return None


def find_capability_by_entrypoint(module: str, function: str) -> dict[str, Any] | None:
    for capability in CAPABILITIES:
        if capability["module"] == module and capability["function"] == function:
            return dict(capability)
    return None


def get_capabilities_by_category(category: str) -> list[dict[str, Any]]:
    category = category.strip().lower()
    return [
        dict(item)
        for item in CAPABILITIES
        if item["category"].lower() == category
    ]


def get_capabilities_by_risk(risk_level: str) -> list[dict[str, Any]]:
    risk_level = risk_level.strip().lower()
    return [
        dict(item)
        for item in CAPABILITIES
        if item["risk_level"].lower() == risk_level
    ]


def validate_capability_registry(expected_tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    issues = []
    ids = []
    entrypoints = []

    for capability in CAPABILITIES:
        missing = sorted(REQUIRED_CAPABILITY_FIELDS - set(capability))
        if missing:
            issues.append(f"{capability.get('id', '<missing id>')} missing fields: {missing}")

        capability_id = str(capability.get("id", ""))
        if capability_id in ids:
            issues.append(f"Duplicate capability id: {capability_id}")
        ids.append(capability_id)

        entrypoint = (capability.get("module"), capability.get("function"))
        if entrypoint in entrypoints:
            issues.append(f"Duplicate capability entrypoint: {entrypoint}")
        entrypoints.append(entrypoint)

        if capability.get("risk_level") not in ALLOWED_RISK_LEVELS:
            issues.append(f"{capability_id} has invalid risk_level: {capability.get('risk_level')}")

        if capability.get("undo_strategy") not in ALLOWED_UNDO_STRATEGIES:
            issues.append(f"{capability_id} has invalid undo_strategy: {capability.get('undo_strategy')}")

        if not isinstance(capability.get("external_apps"), list):
            issues.append(f"{capability_id} external_apps must be a list")

        if not isinstance(capability.get("tags"), list):
            issues.append(f"{capability_id} tags must be a list")

    missing_expected = []
    risk_mismatches = []
    if expected_tools is not None:
        for tool in expected_tools:
            capability = find_capability_by_entrypoint(tool["module"], tool["function"])
            if capability is None:
                missing_expected.append({
                    "name": tool["name"],
                    "module": tool["module"],
                    "function": tool["function"],
                })
                continue

            if capability["risk_level"] != tool["risk"]:
                risk_mismatches.append({
                    "name": tool["name"],
                    "tool_risk": tool["risk"],
                    "capability_risk": capability["risk_level"],
                })

        if missing_expected:
            issues.append(f"Missing capability entries for tool tester items: {missing_expected}")

        if risk_mismatches:
            issues.append(f"Capability risk mismatches: {risk_mismatches}")

    categories = sorted({item["category"] for item in CAPABILITIES})
    risks = sorted({item["risk_level"] for item in CAPABILITIES})

    return {
        "status": "valid" if not issues else "invalid",
        "issues": issues,
        "capability_count": len(CAPABILITIES),
        "categories": categories,
        "risks": risks,
        "missing_expected": missing_expected,
        "risk_mismatches": risk_mismatches,
    }


def summarize_capabilities() -> dict[str, Any]:
    summary: dict[str, Any] = {
        "total": len(CAPABILITIES),
        "by_category": {},
        "by_risk": {},
        "mutating_count": 0,
        "needs_confirmation_count": 0,
        "external_app_count": 0,
    }

    for capability in CAPABILITIES:
        category = capability["category"]
        risk = capability["risk_level"]
        summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
        summary["by_risk"][risk] = summary["by_risk"].get(risk, 0) + 1
        if capability["mutates_files"]:
            summary["mutating_count"] += 1
        if capability["needs_confirmation"]:
            summary["needs_confirmation_count"] += 1
        if capability["external_apps"]:
            summary["external_app_count"] += 1

    return summary


def print_capability_table(capabilities: list[dict[str, Any]]) -> None:
    if not capabilities:
        print("Khong co capability phu hop.")
        return

    print("\n========== CAPABILITY REGISTRY ==========")
    for item in capabilities:
        mutates = "mutates" if item["mutates_files"] else "read-only"
        external = ",".join(item["external_apps"]) if item["external_apps"] else "-"
        print(
            f"{item['id']:<28} | {item['category']:<10} | "
            f"{item['risk_level']:<9} | {mutates:<9} | {item['undo_strategy']:<16} | {external}"
        )
        print(f"  {item['summary']}")


def export_capability_report() -> dict[str, Any]:
    validation = validate_capability_registry()
    summary = summarize_capabilities()
    status = "success" if validation["status"] == "valid" else "error"
    report = create_report(
        tool_name="capability_registry",
        action="export",
        status=status,
        risk_level="safe",
        input_data={},
        results={
            "summary": summary,
            "validation": validation,
            "capabilities": CAPABILITIES,
        },
        recommendations=[
            "Every new tool should add one capability entry before being exposed in the menu.",
            "Keep risk_level and undo_strategy in sync with actual behavior.",
        ],
        summary={
            "total": summary["total"],
            "mutating_count": summary["mutating_count"],
            "needs_confirmation_count": summary["needs_confirmation_count"],
            "undo_available": False,
        },
        undo_available=False,
        tags=["capabilities", "registry", "safe"],
    )

    log_action(
        "capability_registry",
        "export_capability_report",
        status,
        {
            "capability_count": len(CAPABILITIES),
            "issue_count": len(validation["issues"]),
            "report": str(report),
        },
    )

    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "validation": validation,
        "summary": summary,
    }


def run_capability_registry() -> None:
    while True:
        print("""
========== CAPABILITY REGISTRY ==========
1. Xem summary
2. List tat ca capability
3. Loc theo category
4. Loc theo risk
5. Validate registry
6. Xuat report registry
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            summary = summarize_capabilities()
            print("\n========== CAPABILITY SUMMARY ==========")
            print(f"Total: {summary['total']}")
            print(f"Mutating tools: {summary['mutating_count']}")
            print(f"Need confirmation: {summary['needs_confirmation_count']}")
            print(f"Use external apps: {summary['external_app_count']}")
            print(f"By category: {summary['by_category']}")
            print(f"By risk: {summary['by_risk']}")

        elif choice == "2":
            print_capability_table(get_capabilities())

        elif choice == "3":
            category = input("Nhap category: ").strip()
            print_capability_table(get_capabilities_by_category(category))

        elif choice == "4":
            risk = input("Nhap risk safe/medium/dangerous: ").strip()
            print_capability_table(get_capabilities_by_risk(risk))

        elif choice == "5":
            validation = validate_capability_registry()
            print(validation)

        elif choice == "6":
            export_capability_report()

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_capability_registry()
