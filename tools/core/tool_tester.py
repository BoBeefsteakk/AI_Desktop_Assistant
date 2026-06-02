from __future__ import annotations

import importlib
from pathlib import Path

from tools.core.report_manager import create_report


TOOLS_TO_TEST = [
    {"name": "Disk Checker", "module": "tools.system.disk_checker", "function": "check_disk", "risk": "safe"},
    {"name": "Process Monitor", "module": "tools.system.process_monitor", "function": "show_top_process", "risk": "safe"},
    {"name": "Recycle Bin Cleaner", "module": "tools.system.recycle_bin_cleaner", "function": "clear_recycle_bin", "risk": "dangerous"},
    {"name": "Junk File Cleaner", "module": "tools.system.junk_file_cleaner", "function": "run_junk_cleaner", "risk": "dangerous"},
    {"name": "Duplicate Finder", "module": "tools.storage.duplicate_finder", "function": "run_duplicate_finder", "risk": "dangerous"},
    {"name": "Temp Cleaner", "module": "tools.storage.temp_cleaner", "function": "run_temp_cleaner", "risk": "dangerous"},
    {"name": "Media Organizer", "module": "tools.storage.media_organizer", "function": "run_media_organizer", "risk": "medium"},
    {"name": "Empty Folder Finder", "module": "tools.storage.empty_folder_finder", "function": "run_empty_folder_finder", "risk": "dangerous"},
    {"name": "File Indexer", "module": "tools.search.file_indexer", "function": "run_file_indexer", "risk": "safe"},
    {"name": "Startup Launcher", "module": "tools.automation.startup_launcher", "function": "run_startup_launcher", "risk": "medium"},
    {"name": "Download Organizer", "module": "tools.automation.download_organizer", "function": "run_download_organizer", "risk": "medium"},
    {"name": "Download Watcher", "module": "tools.automation.download_watcher", "function": "run_download_watcher", "risk": "medium"},
    {"name": "Browser Cache Cleaner", "module": "tools.system.browser_cache_cleaner", "function": "run_browser_cache_cleaner", "risk": "dangerous"},
    {"name": "Game Booster", "module": "tools.system.game_booster", "function": "run_game_booster", "risk": "medium"},
    {"name": "Natural Command", "module": "tools.search.natural_command", "function": "run_natural_command", "risk": "safe"},
    {"name": "Folder Size Analyzer", "module": "tools.storage.folder_size_analyzer", "function": "run_folder_size_analyzer", "risk": "safe"},
    {"name": "Large File Finder", "module": "tools.storage.large_file_finder", "function": "run_large_file_finder", "risk": "safe"},
    {"name": "System Advisor", "module": "tools.storage.system_advisor", "function": "run_system_advisor", "risk": "safe"},
    {"name": "Assistant Logger", "module": "tools.core.assistant_logger", "function": "run_assistant_logger", "risk": "safe"},
    {"name": "Audit Center", "module": "tools.core.audit_center", "function": "run_audit_center", "risk": "safe"},
    {"name": "Behavior Tester", "module": "tools.core.behavior_tester", "function": "run_behavior_tester", "risk": "safe"},
    {"name": "Config Manager", "module": "tools.core.config_manager", "function": "run_config_manager", "risk": "safe"},
    {"name": "Undo Manager", "module": "tools.core.undo_manager", "function": "run_undo_manager", "risk": "medium"},
    {"name": "Full System Tester", "module": "tools.core.full_system_tester", "function": "run_full_system_tester", "risk": "safe"},
    {"name": "WizTree Adapter", "module": "tools.storage.wiztree_adapter", "function": "run_wiztree_adapter", "risk": "safe"},
    {"name": "External Apps Manager", "module": "tools.core.external_apps", "function": "run_external_apps_manager", "risk": "safe"},
    {"name": "Capability Registry", "module": "tools.core.capability_registry", "function": "run_capability_registry", "risk": "safe"},
    {"name": "Recommendation Center", "module": "tools.core.recommendation_center", "function": "run_recommendation_center", "risk": "safe"},
    {"name": "Guided Action Runner", "module": "tools.core.guided_action_runner", "function": "run_guided_action_runner", "risk": "medium"},
    {"name": "Feed Assistant Readiness", "module": "tools.core.feed_readiness", "function": "run_feed_readiness", "risk": "safe"},
    {"name": "Scenario Tester", "module": "tools.core.scenario_tester", "function": "run_scenario_tester", "risk": "safe"},
    {"name": "Action Policy Manager", "module": "tools.core.action_policy", "function": "run_action_policy_manager", "risk": "safe"},
    {"name": "File Location Opener", "module": "tools.core.file_location_opener", "function": "open_file_location", "risk": "safe"},
]


def save_test_report(results: list[dict]) -> Path:
    data = {
        "total": len(results),
        "passed": sum(1 for item in results if item["status"] == "pass"),
        "failed": sum(1 for item in results if item["status"] == "fail"),
        "results": results,
    }

    return create_report(
        tool_name="tool_tester",
        status="success" if data["failed"] == 0 else "error",
        input_data={},
        results=data,
        recommendations=[
            "Fix failed imports before running risky tools.",
        ],
    )


def test_tool_imports() -> list[dict]:
    results = []

    print("\n========== TOOL TESTER ==========\n")

    for tool in TOOLS_TO_TEST:
        name = tool["name"]
        module_name = tool["module"]
        function_name = tool["function"]

        result = {
            "name": name,
            "module": module_name,
            "function": function_name,
            "risk": tool["risk"],
            "status": "pass",
            "error": None,
        }

        try:
            module = importlib.import_module(module_name)

            if not hasattr(module, function_name):
                raise AttributeError(f"Function not found: {function_name}")

            print(f"[PASS] {name}")

        except Exception as error:
            result["status"] = "fail"
            result["error"] = str(error)
            print(f"[FAIL] {name} -> {error}")

        results.append(result)

    return results


def show_summary(results: list[dict], report_path: Path) -> None:
    passed = sum(1 for item in results if item["status"] == "pass")
    failed = sum(1 for item in results if item["status"] == "fail")

    print("\n========== TEST SUMMARY ==========")
    print(f"Total : {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Report: {report_path}")

    if failed > 0:
        print("\nCac tool bi loi:")
        for item in results:
            if item["status"] == "fail":
                print(f"- {item['name']}: {item['error']}")


def run_tool_tester() -> None:
    results = test_tool_imports()
    report_path = save_test_report(results)
    show_summary(results, report_path)


if __name__ == "__main__":
    run_tool_tester()
