"""Startup Scan Orchestrator.

This is the boot entrypoint for the assistant: on each machine startup it can
run a full-drive read-only scan, classify findings into issues, and present a
single advisory screen where the user decides what to do with exactly three
simple choices for safe-delete candidates:

    1. Khong xoa gi
    2. Chon file de xoa
    3. Xoa tat ca file an toan duoc de xuat

It never deletes or moves anything by itself. Every real file operation is
routed through the existing guarded flows (Safe Delete Adapter via Bot
Controller), which keep dry-run + final token + Recycle Bin safety.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import (
    DEFAULT_LARGE_FILE_MB,
    DEFAULT_RESULT_LIMIT,
    DEFAULT_SCAN_FOLDER,
    STARTUP_SCAN_MODE,
)
from tools.core.assistant_logger import log_action
from tools.core.auto_scan_session import export_auto_scan_session_report
from tools.core.bot_controller import (
    FINAL_DELETE_TOKEN,
    build_bot_controller_result,
    build_selection_session,
    export_safe_delete_selection_flow_report,
    iter_selection_items,
    parse_selection_input,
    print_delete_summary,
    print_selection_session,
)
from tools.core.report_manager import create_report
from tools.core.safety_utils import format_size
from tools.storage.wiztree_adapter import is_wiztree_available


STARTUP_SCAN_TOOL = "startup_scan"
STARTUP_SCAN_SCHEMA = "startup_scan_v1"
RESOLVABLE_MODES = {"auto", "light", "python", "wiztree"}


def resolve_scan_mode(scan_mode: str | None = None) -> str:
    """Resolve the configured scan mode into a concrete auto-scan mode.

    "auto" prefers WizTree (fast full-drive scan) and falls back to the Python
    scanner when WizTree is not available.
    """
    mode = str(scan_mode or STARTUP_SCAN_MODE or "auto").strip().lower()
    if mode not in RESOLVABLE_MODES:
        mode = "auto"

    if mode == "auto":
        return "wiztree" if is_wiztree_available() else "python"
    return mode


def build_advisory(bot_result: dict[str, Any]) -> dict[str, Any]:
    """Build the user-facing advisory from a Bot Controller result."""
    summary = bot_result["summary"]
    issue_summary = bot_result["issue_classifier"]["summary"]
    session = build_selection_session(bot_result=bot_result, include_items=True)

    delete_candidate_ids = [
        item["selection_id"]
        for item in iter_selection_items(session)
        if "delete_candidate" in item.get("allowed_decisions", [])
    ]

    return {
        "issue_count": issue_summary["issue_count"],
        "by_plan_action": issue_summary.get("by_plan_action", {}),
        "delete_candidate_count": len(delete_candidate_ids),
        "delete_candidate_ids": delete_candidate_ids,
        "move_later_selectable_count": summary["move_later_selectable_count"],
        "needs_backup_selectable_count": summary["needs_backup_selectable_count"],
        "do_not_touch_count": summary["do_not_touch_count"],
        "needs_selection_count": summary["needs_selection_count"],
        "decision_options": {
            "skip": "Khong xoa gi - chi xem de xuat.",
            "select": "Chon file de xoa - ban tu chon tung file.",
            "delete_all_safe": "Xoa tat ca file an toan duoc de xuat (van qua dry-run + token + Recycle Bin).",
        },
    }


def build_startup_scan_result(
    *,
    root_drive: str | Path = DEFAULT_SCAN_FOLDER,
    scan_mode: str | None = None,
    large_file_mb: int = DEFAULT_LARGE_FILE_MB,
    result_limit: int = DEFAULT_RESULT_LIMIT,
    export_scan_report: bool = True,
) -> dict[str, Any]:
    resolved_mode = resolve_scan_mode(scan_mode)

    if export_scan_report:
        scan_export = export_auto_scan_session_report(
            root_drive=root_drive,
            storage_mode=resolved_mode,
            large_file_mb=large_file_mb,
            result_limit=result_limit,
            extra_tags=["startup_scan", "boot"],
        )
        auto_scan = scan_export["scan"]
        auto_scan_report = scan_export["report"]
    else:
        from tools.core.auto_scan_session import build_auto_scan_session_result

        auto_scan = build_auto_scan_session_result(
            root_drive=root_drive,
            storage_mode=resolved_mode,
            large_file_mb=large_file_mb,
            result_limit=result_limit,
        )
        auto_scan_report = None

    snapshot = auto_scan.get("snapshot", {})
    storage = snapshot.get("storage", {})
    processes = snapshot.get("processes", {})

    bot_result = build_bot_controller_result(include_items=True)
    advisory = build_advisory(bot_result)

    snapshot_summary = {
        "root_drive": auto_scan.get("root_drive"),
        "storage_provider": storage.get("provider"),
        "top_folder_count": storage.get("top_folder_count"),
        "large_file_count": storage.get("large_file_count"),
        "system_memory_percent": processes.get("system_memory_percent"),
        "process_count": processes.get("process_count"),
        "largest_files": [
            {
                "path": item.get("path"),
                "size": item.get("size"),
                "size_text": format_size(int(item.get("size") or 0)),
            }
            for item in storage.get("large_files", [])[:10]
        ],
    }

    return {
        "schema": STARTUP_SCAN_SCHEMA,
        "status": "ready",
        "scan_mode": resolved_mode,
        "root_drive": str(root_drive),
        "auto_scan_report": auto_scan_report,
        "snapshot_summary": snapshot_summary,
        "advisory": advisory,
        "bot_summary": bot_result["summary"],
        "decision_screen": bot_result["decision_screen"],
        "safety_contract": {
            "read_only": True,
            "executes_file_operations": False,
            "delete_requires_safe_delete_adapter": True,
            "delete_requires_final_token": True,
            "final_delete_token": FINAL_DELETE_TOKEN,
        },
    }


def export_startup_scan_report(
    *,
    root_drive: str | Path = DEFAULT_SCAN_FOLDER,
    scan_mode: str | None = None,
    large_file_mb: int = DEFAULT_LARGE_FILE_MB,
    result_limit: int = DEFAULT_RESULT_LIMIT,
) -> dict[str, Any]:
    result = build_startup_scan_result(
        root_drive=root_drive,
        scan_mode=scan_mode,
        large_file_mb=large_file_mb,
        result_limit=result_limit,
    )
    summary = {
        "scan_mode": result["scan_mode"],
        "issue_count": result["advisory"]["issue_count"],
        "delete_candidate_count": result["advisory"]["delete_candidate_count"],
        "move_later_selectable_count": result["advisory"]["move_later_selectable_count"],
        "needs_backup_selectable_count": result["advisory"]["needs_backup_selectable_count"],
        "do_not_touch_count": result["advisory"]["do_not_touch_count"],
        "file_operations_executed": False,
        "undo_available": False,
    }
    report = create_report(
        tool_name=STARTUP_SCAN_TOOL,
        action="startup_scan",
        status="success",
        risk_level="safe",
        input_data={
            "root_drive": str(root_drive),
            "scan_mode": result["scan_mode"],
            "large_file_mb": large_file_mb,
            "result_limit": result_limit,
        },
        results=result,
        recommendations=[
            "Startup scan is read-only and only advises; the user decides what to delete.",
            "Safe-delete candidates still require selection, dry-run and the final delete token.",
        ],
        summary=summary,
        undo_available=False,
        tags=["startup_scan", "boot", "advisor", "read_only"],
    )
    log_action(
        STARTUP_SCAN_TOOL,
        "export_startup_scan_report",
        "success",
        {
            "report": str(report),
            "scan_mode": result["scan_mode"],
            "delete_candidate_count": result["advisory"]["delete_candidate_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": "success",
        "report": str(report),
        "startup": result,
    }


def print_startup_advisory(result: dict[str, Any]) -> None:
    snapshot = result["snapshot_summary"]
    advisory = result["advisory"]

    print("\n========== TRO LY KHOI DONG - TINH TRANG MAY ==========")
    print(f"O quet: {snapshot['root_drive']} | che do: {result['scan_mode']}")
    print(
        f"RAM dang dung: {snapshot.get('system_memory_percent')}% | "
        f"so process: {snapshot.get('process_count')}"
    )
    print(
        f"Folder lon: {snapshot.get('top_folder_count')} | "
        f"file lon: {snapshot.get('large_file_count')}"
    )

    if snapshot["largest_files"]:
        print("\nFile lon nhat phat hien:")
        for item in snapshot["largest_files"]:
            print(f"- {item['size_text']:>10} | {item['path']}")

    print("\n---------- DE XUAT ----------")
    print(f"Tong van de phat hien: {advisory['issue_count']}")
    print(f"Theo hanh dong: {advisory['by_plan_action']}")
    print(f"File co the xoa an toan (de xuat): {advisory['delete_candidate_count']}")
    print(f"File nen chuyen cho khac (move): {advisory['move_later_selectable_count']}")
    print(f"File nen backup truoc: {advisory['needs_backup_selectable_count']}")
    print(f"Khong duoc dung toi: {advisory['do_not_touch_count']}")

    print("\n---------- BAN QUYET DINH ----------")
    print("1. Khong xoa gi")
    print("2. Chon file de xoa")
    print("3. Xoa tat ca file an toan duoc de xuat")


def run_safe_delete_decision(
    decisions: dict[str, str],
    *,
    note: str | None = None,
) -> None:
    """Run the guarded safe-delete flow: dry-run, then token-gated apply."""
    if not decisions:
        print("Khong co file nao duoc chon.")
        return

    session = build_selection_session(include_items=True)
    dry_run = export_safe_delete_selection_flow_report(
        decisions,
        mode="dry_run",
        session=session,
        note=note,
    )
    delete_report = dry_run["flow"].get("delete_report")
    if delete_report:
        print_delete_summary(delete_report["delete"])

    if dry_run["flow"]["summary"].get("deletable_count", 0) <= 0:
        print("Khong co item nao du dieu kien safe_delete sau dry-run.")
        return

    print(f"\nFinal delete token required: {FINAL_DELETE_TOKEN}")
    token = input("Nhap final delete token de xoa, bo trong de huy: ").strip()
    if not token:
        print("Da huy. Khong xoa gi.")
        return

    applied = export_safe_delete_selection_flow_report(
        decisions,
        mode="apply",
        final_token=token,
        session=session,
        note=note,
    )
    applied_delete = applied["flow"].get("delete_report")
    if applied_delete:
        print_delete_summary(applied_delete["delete"])


def run_startup_scan(
    *,
    root_drive: str | Path = DEFAULT_SCAN_FOLDER,
    scan_mode: str | None = None,
    interactive: bool = True,
) -> dict[str, Any]:
    """Run the boot scan and present the advisory decision screen."""
    print("Dang quet may, vui long doi...")
    export = export_startup_scan_report(root_drive=root_drive, scan_mode=scan_mode)
    result = export["startup"]
    print_startup_advisory(result)

    if not interactive:
        return export

    delete_ids = result["advisory"]["delete_candidate_ids"]

    while True:
        choice = input("\nChon (1/2/3, hoac 0 de thoat): ").strip()

        if choice in {"0", "1"}:
            print("Khong xoa gi. Da luu de xuat trong report.")
            break

        if choice == "2":
            session = build_selection_session(include_items=True)
            print_selection_session(session)
            raw_text = input(
                "Nhap file can xoa (vd M001=delete_candidate, M002=delete_candidate): "
            ).strip()
            decisions = parse_selection_input(raw_text)
            run_safe_delete_decision(decisions, note="startup_scan_select")
            break

        if choice == "3":
            if not delete_ids:
                print("Khong co file an toan nao de xoa.")
                break
            decisions = {selection_id: "delete_candidate" for selection_id in delete_ids}
            print(f"Se dry-run {len(decisions)} file safe_delete duoc de xuat.")
            run_safe_delete_decision(decisions, note="startup_scan_delete_all_safe")
            break

        print("Lua chon khong hop le.")

    return export


if __name__ == "__main__":
    run_startup_scan()
