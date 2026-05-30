from __future__ import annotations

import json
from typing import Any

from config.settings import (
    DEFAULT_DOWNLOAD_FOLDER,
    DEFAULT_SCAN_FOLDER,
    USER_SETTINGS_FILE,
    get_config_snapshot,
    validate_user_settings,
)
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report


def get_config_status() -> dict[str, Any]:
    validation = validate_user_settings()
    snapshot = get_config_snapshot()

    return {
        "validation": validation,
        "snapshot": snapshot,
    }


def show_config_summary() -> None:
    status = get_config_status()
    validation = status["validation"]
    snapshot = status["snapshot"]

    print("\n========== CONFIG SUMMARY ==========")
    print(f"Config file      : {USER_SETTINGS_FILE}")
    print(f"Status           : {validation['status']}")
    print(f"Base dir         : {snapshot['base_dir']}")
    print(f"Reports dir      : {snapshot['reports_dir']}")
    print(f"Logs dir         : {snapshot['logs_dir']}")
    print(f"Backups dir      : {snapshot['backups_dir']}")
    print(f"Default scan     : {DEFAULT_SCAN_FOLDER}")
    print(f"Downloads        : {DEFAULT_DOWNLOAD_FOLDER}")
    print(f"Protected folders: {snapshot['protected_dir_count']}")
    print(f"Browser templates: {snapshot['browser_cache_path_count']}")

    if validation["issues"]:
        print("\nIssues:")
        for issue in validation["issues"]:
            print(f"- {issue}")

    if validation["warnings"]:
        print("\nWarnings:")
        for warning in validation["warnings"]:
            print(f"- {warning}")


def export_config_report() -> dict[str, Any]:
    status = get_config_status()
    validation = status["validation"]

    report = create_report(
        tool_name="config_manager",
        status=validation["status"],
        input_data={
            "config_file": str(USER_SETTINGS_FILE),
        },
        results=status,
        recommendations=[
            "Edit config/user_settings.json to change paths, thresholds, and safety lists.",
            "Keep disk_warning_percent lower than disk_critical_percent.",
        ],
    )

    log_action(
        "config_manager",
        "export_config_report",
        validation["status"],
        {
            "config_file": str(USER_SETTINGS_FILE),
            "issues": len(validation["issues"]),
            "warnings": len(validation["warnings"]),
            "report": str(report),
        },
    )

    print(f"Report: {report}")
    return {
        "status": validation["status"],
        "report": str(report),
    }


def print_full_config() -> None:
    status = get_config_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


def run_config_manager() -> None:
    while True:
        print("""
========== CONFIG MANAGER ==========
1. Xem config summary
2. Xuat config report
3. In full config snapshot
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            show_config_summary()

        elif choice == "2":
            export_config_report()

        elif choice == "3":
            print_full_config()

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_config_manager()
