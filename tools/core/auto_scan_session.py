from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import DEFAULT_LARGE_FILE_MB, DEFAULT_RESULT_LIMIT, DEFAULT_SCAN_FOLDER
from tools.core.assistant_logger import log_action
from tools.core.audit_center import get_audit_snapshot
from tools.core.external_apps import get_external_apps_status
from tools.core.report_manager import create_report
from tools.core.safety_utils import format_size
from tools.storage.folder_size_analyzer import analyze_top_folders
from tools.storage.large_file_finder import find_large_files
from tools.storage.system_advisor import build_system_advisor_result, get_disk_health_snapshot
from tools.storage.wiztree_adapter import is_wiztree_available, scan_storage_with_wiztree
from tools.system.process_monitor import get_top_processes


AUTO_SCAN_SESSION_TOOL = "auto_scan_session"
AUTO_SCAN_SESSION_SCHEMA = "auto_scan_session_v1"
STORAGE_MODES = {"light", "python", "wiztree", "provided"}


def normalize_storage_mode(storage_mode: str | None) -> str:
    mode = str(storage_mode or "light").strip().lower()
    return mode if mode in STORAGE_MODES else "light"


def collect_storage_snapshot(
    root_drive: str | Path,
    *,
    storage_mode: str = "light",
    large_file_mb: int = DEFAULT_LARGE_FILE_MB,
    result_limit: int = DEFAULT_RESULT_LIMIT,
) -> dict[str, Any]:
    mode = normalize_storage_mode(storage_mode)

    if mode == "light":
        return {
            "provider": "skipped",
            "wiztree_status": "not_requested",
            "storage_scan_report": None,
            "top_folders": [],
            "large_files": [],
            "status": "skipped",
            "reason": "Light mode only reads disk/process/app/audit snapshots.",
        }

    if mode == "wiztree":
        if not is_wiztree_available():
            return {
                "provider": "wiztree",
                "wiztree_status": "unavailable",
                "storage_scan_report": None,
                "top_folders": [],
                "large_files": [],
                "status": "unavailable",
                "reason": "WizTree executable is not available.",
            }

        wiztree_result = scan_storage_with_wiztree(
            root_drive,
            min_size_mb=large_file_mb,
            limit=result_limit,
            create_tool_report=True,
        )
        return {
            "provider": "wiztree",
            "wiztree_status": wiztree_result["status"],
            "storage_scan_report": wiztree_result.get("report"),
            "top_folders": wiztree_result.get("top_folders", []),
            "large_files": wiztree_result.get("large_files", []),
            "status": wiztree_result["status"],
            "reason": "WizTree scan finished." if wiztree_result["status"] == "success" else "WizTree scan did not finish successfully.",
        }

    top_folders = analyze_top_folders(str(root_drive), limit=result_limit)
    large_files = find_large_files(
        str(root_drive),
        min_size_mb=large_file_mb,
        limit=result_limit,
    )
    return {
        "provider": "python",
        "wiztree_status": "not_used",
        "storage_scan_report": None,
        "top_folders": top_folders,
        "large_files": large_files,
        "status": "success",
        "reason": "Python storage scan finished.",
    }


def summarize_auto_scan_result(result: dict[str, Any]) -> dict[str, Any]:
    snapshot = result["snapshot"]
    storage = snapshot["storage"]
    disk = snapshot["disk"]
    processes = snapshot["processes"]
    external_apps = snapshot["external_apps"]
    recommendations = result["advisor"]["recommendations"]
    by_severity: dict[str, int] = {}
    for item in recommendations:
        severity = str(item.get("severity") or "unknown")
        by_severity[severity] = by_severity.get(severity, 0) + 1

    return {
        "status": result["status"],
        "root_drive": snapshot["root_drive"],
        "storage_provider": storage["provider"],
        "top_folder_count": storage["top_folder_count"],
        "large_file_count": storage["large_file_count"],
        "disk_count": len(disk.get("disks", [])),
        "process_count": processes["process_count"],
        "system_memory_percent": processes.get("system_memory_percent"),
        "external_apps_available": external_apps.get("available", 0),
        "external_apps_total": external_apps.get("total", 0),
        "recommendation_count": len(recommendations),
        "recommendations_by_severity": by_severity,
        "file_operations_executed": False,
        "undo_available": False,
    }


def build_auto_scan_session_result(
    *,
    root_drive: str | Path = DEFAULT_SCAN_FOLDER,
    storage_mode: str = "light",
    large_file_mb: int = DEFAULT_LARGE_FILE_MB,
    result_limit: int = DEFAULT_RESULT_LIMIT,
    top_folders: list[dict[str, Any]] | None = None,
    large_files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root_text = str(root_drive)
    mode = "provided" if top_folders is not None or large_files is not None else normalize_storage_mode(storage_mode)

    if mode == "provided":
        storage = {
            "provider": "provided",
            "wiztree_status": "not_used",
            "storage_scan_report": None,
            "top_folders": top_folders or [],
            "large_files": large_files or [],
            "status": "success",
            "reason": "Storage data was supplied by caller.",
        }
    else:
        storage = collect_storage_snapshot(
            root_text,
            storage_mode=mode,
            large_file_mb=large_file_mb,
            result_limit=result_limit,
        )

    disk_snapshot = get_disk_health_snapshot()
    processes = get_top_processes(limit=10, sort_by="ram")
    external_apps = get_external_apps_status(include_versions=False)
    audit_snapshot = get_audit_snapshot(limit=20)

    advisor = build_system_advisor_result(
        root_drive=root_text,
        storage_provider=storage["provider"],
        wiztree_status=storage["wiztree_status"],
        storage_scan_report=storage["storage_scan_report"],
        top_folders=storage["top_folders"],
        large_files=storage["large_files"],
        processes=processes,
        disk_snapshot=disk_snapshot,
        external_apps=external_apps,
        audit_snapshot=audit_snapshot,
    )

    status = "success"
    if storage["status"] in {"error", "timeout"}:
        status = "warning"

    result = {
        "schema": AUTO_SCAN_SESSION_SCHEMA,
        "status": status,
        "mode": mode,
        "root_drive": root_text,
        "large_file_mb": large_file_mb,
        "result_limit": result_limit,
        "snapshot": advisor["snapshot"],
        "advisor": advisor,
        "storage_status": {
            "status": storage["status"],
            "provider": storage["provider"],
            "wiztree_status": storage["wiztree_status"],
            "reason": storage["reason"],
        },
        "safety_contract": {
            "read_only": True,
            "executes_file_operations": False,
            "changes_files": False,
            "delete_enabled": False,
            "move_enabled": False,
            "storage_mode": mode,
        },
    }
    result["summary"] = summarize_auto_scan_result(result)
    return result


def export_auto_scan_session_report(
    *,
    root_drive: str | Path = DEFAULT_SCAN_FOLDER,
    storage_mode: str = "light",
    large_file_mb: int = DEFAULT_LARGE_FILE_MB,
    result_limit: int = DEFAULT_RESULT_LIMIT,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    result = build_auto_scan_session_result(
        root_drive=root_drive,
        storage_mode=storage_mode,
        large_file_mb=large_file_mb,
        result_limit=result_limit,
    )
    report_status = "success" if result["status"] == "success" else "warning"
    report = create_report(
        tool_name=AUTO_SCAN_SESSION_TOOL,
        action="auto_scan",
        status=report_status,
        risk_level="safe",
        input_data={
            "root_drive": str(root_drive),
            "storage_mode": storage_mode,
            "large_file_mb": large_file_mb,
            "result_limit": result_limit,
        },
        results=result,
        recommendations=[
            "Auto Scan Session is read-only; use Issue Classifier to turn findings into selectable issues.",
            "Use light mode for fast periodic checks; use wiztree/python mode when storage detail is needed.",
        ],
        summary=result["summary"],
        undo_available=False,
        tags=["auto_scan_session", "auto_scan", "read_only", *(extra_tags or [])],
    )
    log_action(
        AUTO_SCAN_SESSION_TOOL,
        "export_auto_scan_session_report",
        report_status,
        {
            "report": str(report),
            "mode": result["mode"],
            "recommendation_count": result["summary"]["recommendation_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": report_status,
        "report": str(report),
        "scan": result,
    }


def print_auto_scan_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== AUTO SCAN SESSION V1 ==========")
    print(f"Status: {result['status']}")
    print(f"Root: {summary['root_drive']}")
    print(f"Storage: {summary['storage_provider']} | folders={summary['top_folder_count']} | files={summary['large_file_count']}")
    print(f"Disk count: {summary['disk_count']}")
    print(f"Process count: {summary['process_count']} | RAM={summary.get('system_memory_percent')}")
    print(f"External apps: {summary['external_apps_available']}/{summary['external_apps_total']}")
    print(f"Recommendations: {summary['recommendation_count']} {summary['recommendations_by_severity']}")

    storage = result["snapshot"]["storage"]
    if storage["large_files"]:
        print("\nLarge files:")
        for item in storage["large_files"][:10]:
            print(f"- {format_size(item.get('size', 0))} | {item.get('path')}")


def run_auto_scan_session() -> None:
    while True:
        print("""
========== AUTO SCAN SESSION V1 ==========
1. Fast read-only scan summary
2. Export fast read-only scan report
3. Export storage-aware scan report
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_auto_scan_summary(build_auto_scan_session_result(storage_mode="light"))

        elif choice == "2":
            export_auto_scan_session_report(storage_mode="light")

        elif choice == "3":
            root = input("Nhap root can scan (bo trong = default): ").strip().strip('"') or DEFAULT_SCAN_FOLDER
            mode = input("Storage mode [wiztree/python/light]: ").strip().lower() or "wiztree"
            result = export_auto_scan_session_report(root_drive=root, storage_mode=mode)
            print_auto_scan_summary(result["scan"])

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_auto_scan_session()
