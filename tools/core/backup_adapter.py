from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import BACKUPS_DIR
from tools.core.assistant_logger import log_action
from tools.core.execution_adapter import (
    extract_decision_payload,
    load_selection_decision_report,
    validate_selection_decision_payload,
)
from tools.core.report_manager import create_report
from tools.core.risk_classifier import PROTECTED, classify_file_risk
from tools.core.safety_utils import save_manifest


BACKUP_ADAPTER_TOOL = "backup_adapter"
BACKUP_ADAPTER_SCHEMA = "backup_adapter_v1"
FINAL_BACKUP_TOKEN = "BACKUP_SELECTION_V1"
SUPPORTED_BACKUP_DECISION = "needs_backup"
BACKUP_RUNS_DIR = BACKUPS_DIR / "selection_backups"


def merge_report_tags(base_tags: list[str], extra_tags: list[str] | None = None) -> list[str]:
    tags: list[str] = []
    for tag in [*base_tags, *(extra_tags or [])]:
        text = str(tag).strip()
        if text and text not in tags:
            tags.append(text)
    return tags


def iter_selected_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for item in payload.get("selected", []) or []:
        if isinstance(item, dict):
            items.append(item)
    return items


def build_backup_run_dir(run_id: str | None = None) -> Path:
    return BACKUP_RUNS_DIR / (run_id or datetime.now().strftime("run_%Y%m%d_%H%M%S"))


def sanitize_drive_anchor(path: Path) -> str:
    anchor = path.anchor.replace("\\", "").replace(":", "")
    return anchor or "relative"


def plan_collision_safe_target(source: Path, backup_run_dir: Path) -> Path:
    resolved = source.resolve(strict=False)
    parts = list(resolved.parts)
    if parts and parts[0].endswith("\\"):
        parts[0] = sanitize_drive_anchor(resolved)
    target = backup_run_dir.joinpath(*parts)
    final_target = target
    count = 1
    while final_target.exists():
        final_target = target.with_name(f"{target.stem}_{count}{target.suffix}")
        count += 1
    return final_target


def build_backup_source_info(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {
            "path": None,
            "status": "missing",
            "valid": False,
            "reason": "Missing source path.",
        }

    source = Path(path)
    risk = classify_file_risk(source)

    if not source.exists():
        return {
            "path": str(source),
            "status": "missing",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "matched_rule": risk.get("matched_rule"),
            "reason": "Source path does not exist.",
        }

    if not source.is_file():
        return {
            "path": str(source),
            "status": "not_file",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "matched_rule": risk.get("matched_rule"),
            "reason": "Backup Adapter v1 backs up files only.",
        }

    if risk.get("risk") == PROTECTED:
        return {
            "path": str(source),
            "status": "protected",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "matched_rule": risk.get("matched_rule"),
            "reason": "Source path is protected and will not be copied by Backup Adapter.",
        }

    return {
        "path": str(source),
        "status": "valid",
        "valid": True,
        "risk": risk.get("risk"),
        "risk_category": risk.get("category"),
        "matched_rule": risk.get("matched_rule"),
        "size": source.stat().st_size,
        "reason": "Source is valid for explicit backup confirmation.",
    }


def build_backup_step(item: dict[str, Any], *, backup_run_dir: Path) -> dict[str, Any]:
    decision = str(item.get("decision") or "").strip().lower()
    source_info = build_backup_source_info(item.get("path"))
    base = {
        "selection_id": item.get("selection_id"),
        "path": item.get("path"),
        "name": item.get("name"),
        "size_text": item.get("size_text"),
        "selection_group": item.get("selection_group"),
        "policy_decision": item.get("policy_decision"),
        "plan_action": item.get("plan_action"),
        "decision": decision,
        "source_info": source_info,
        "backup_run_dir": str(backup_run_dir),
        "file_operation": "copy_to_backup",
        "manifest_required": True,
        "undo_available_after_apply": False,
        "source_preserved": True,
    }

    if decision != SUPPORTED_BACKUP_DECISION:
        return {
            **base,
            "step_status": "not_in_scope",
            "can_backup": False,
            "reason": "Only needs_backup decisions are handled by Backup Adapter v1.",
        }

    if not source_info.get("valid"):
        return {
            **base,
            "step_status": "blocked",
            "can_backup": False,
            "reason": source_info.get("reason") or "Source is invalid.",
        }

    source = Path(source_info["path"])
    planned_backup_path = plan_collision_safe_target(source, backup_run_dir)
    return {
        **base,
        "step_status": "pending_backup",
        "can_backup": True,
        "planned_backup_path": str(planned_backup_path),
        "reason": "Ready to copy to backup after final confirmation.",
    }


def build_backup_steps(payload: dict[str, Any], *, backup_run_dir: Path) -> list[dict[str, Any]]:
    return [
        build_backup_step(item, backup_run_dir=backup_run_dir)
        for item in iter_selected_items(payload)
    ]


def summarize_backup_steps(
    steps: list[dict[str, Any]],
    *,
    adapter_executed: bool,
    manifest: str | None = None,
    backup_run_dir: str | None = None,
) -> dict[str, Any]:
    requested = [item for item in steps if item["decision"] == SUPPORTED_BACKUP_DECISION]
    backupable = [item for item in steps if item.get("can_backup")]
    backed_up = [item for item in steps if item["step_status"] == "backed_up"]
    blocked = [item for item in steps if item["step_status"] == "blocked"]
    errors = [item for item in steps if item["step_status"] == "error"]
    not_in_scope = [item for item in steps if item["step_status"] == "not_in_scope"]

    return {
        "total": len(steps),
        "backup_requested_count": len(requested),
        "backupable_count": len(backupable),
        "backed_up_count": len(backed_up),
        "blocked_count": len(blocked),
        "error_count": len(errors),
        "not_in_scope_count": len(not_in_scope),
        "adapter_executed": adapter_executed,
        "file_operations_executed": bool(backed_up),
        "file_operation_count": len(backed_up),
        "backup_run_dir": backup_run_dir,
        "manifest": manifest,
        "undo_available": False,
        "source_preserved": True,
    }


def apply_backup_steps(steps: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    applied_steps: list[dict[str, Any]] = []
    manifest_records: list[dict[str, Any]] = []

    for item in steps:
        if not item.get("can_backup"):
            applied_steps.append({**item, "executed": False})
            continue

        source = Path(item["source_info"]["path"])
        target = Path(item["planned_backup_path"])
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            final_target = plan_collision_safe_target(source, Path(item["backup_run_dir"]))
            shutil.copy2(source, final_target)
            copied_size = final_target.stat().st_size
            if copied_size != source.stat().st_size:
                raise RuntimeError("Copied file size does not match source size.")

            manifest_record = {
                "old_path": str(source),
                "new_path": str(final_target),
                "source_path": str(source),
                "backup_path": str(final_target),
                "selection_id": item.get("selection_id"),
                "decision": item.get("decision"),
                "operation": "backup_copy",
                "source_preserved": True,
                "size": copied_size,
            }
            manifest_records.append(manifest_record)
            applied_steps.append({
                **item,
                "step_status": "backed_up",
                "executed": True,
                "actual_backup_path": str(final_target),
                "reason": "Copied to backup and recorded in manifest.",
            })
        except Exception as exc:
            applied_steps.append({
                **item,
                "step_status": "error",
                "executed": False,
                "error": str(exc),
                "reason": "Backup copy failed; no manifest record was created for this item.",
            })

    manifest_path = None
    if manifest_records:
        manifest_path = str(save_manifest("backup_adapter_copy", manifest_records))

    return applied_steps, manifest_path


def build_safety_contract() -> dict[str, Any]:
    return {
        "schema": BACKUP_ADAPTER_SCHEMA,
        "supported_decisions": [SUPPORTED_BACKUP_DECISION],
        "requires_final_token": True,
        "final_token": FINAL_BACKUP_TOKEN,
        "files_only_v1": True,
        "blocks_protected_source": True,
        "delete_enabled": False,
        "move_enabled": False,
        "backup_enabled": True,
        "source_preserved": True,
        "uses_copy2": True,
        "manifest_required": True,
            "undo_strategy": "not_needed",
    }


def build_backup_adapter_result(
    *,
    source_report_path: str | Path | None = None,
    mode: str = "dry_run",
    final_token: str | None = None,
    backup_run_dir: str | Path | None = None,
) -> dict[str, Any]:
    report_data, report_path = load_selection_decision_report(source_report_path)
    payload = extract_decision_payload(report_data)
    validation = validate_selection_decision_payload(payload)
    mode = str(mode or "dry_run").strip().lower()
    run_dir = Path(backup_run_dir) if backup_run_dir else build_backup_run_dir()

    if report_data is None or payload is None:
        return {
            "schema": BACKUP_ADAPTER_SCHEMA,
            "status": "missing_source_report",
            "mode": mode,
            "source_report": report_path,
            "backup_run_dir": str(run_dir),
            "validation": validation,
            "summary": summarize_backup_steps([], adapter_executed=False, backup_run_dir=str(run_dir)),
            "steps": [],
            "safety_contract": build_safety_contract(),
        }

    steps = build_backup_steps(payload, backup_run_dir=run_dir)

    if validation["status"] != "valid":
        return {
            "schema": BACKUP_ADAPTER_SCHEMA,
            "status": "invalid_decision_report",
            "mode": mode,
            "source_report": report_path,
            "backup_run_dir": str(run_dir),
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_backup_steps(steps, adapter_executed=False, backup_run_dir=str(run_dir)),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if mode not in {"dry_run", "apply"}:
        return {
            "schema": BACKUP_ADAPTER_SCHEMA,
            "status": "invalid_mode",
            "mode": mode,
            "source_report": report_path,
            "backup_run_dir": str(run_dir),
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_backup_steps(steps, adapter_executed=False, backup_run_dir=str(run_dir)),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    dry_summary = summarize_backup_steps(steps, adapter_executed=False, backup_run_dir=str(run_dir))
    if mode == "dry_run":
        status = "dry_run" if dry_summary["backup_requested_count"] else "no_backup_items"
        return {
            "schema": BACKUP_ADAPTER_SCHEMA,
            "status": status,
            "mode": mode,
            "source_report": report_path,
            "backup_run_dir": str(run_dir),
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if dry_summary["backup_requested_count"] <= 0:
        return {
            "schema": BACKUP_ADAPTER_SCHEMA,
            "status": "no_backup_items",
            "mode": mode,
            "source_report": report_path,
            "backup_run_dir": str(run_dir),
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if final_token != FINAL_BACKUP_TOKEN:
        return {
            "schema": BACKUP_ADAPTER_SCHEMA,
            "status": "requires_final_confirmation",
            "mode": mode,
            "source_report": report_path,
            "backup_run_dir": str(run_dir),
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    applied_steps, manifest = apply_backup_steps(steps)
    summary = summarize_backup_steps(
        applied_steps,
        adapter_executed=True,
        manifest=manifest,
        backup_run_dir=str(run_dir),
    )
    if summary["error_count"]:
        status = "completed_with_errors"
    elif summary["blocked_count"]:
        status = "completed_with_blocks"
    elif summary["backed_up_count"]:
        status = "completed"
    else:
        status = "no_backups_completed"

    return {
        "schema": BACKUP_ADAPTER_SCHEMA,
        "status": status,
        "mode": mode,
        "source_report": report_path,
        "backup_run_dir": str(run_dir),
        "validation": validation,
        "selection_summary": payload.get("summary", {}),
        "summary": summary,
        "steps": applied_steps,
        "manifest": manifest,
        "undo_available": False,
        "safety_contract": build_safety_contract(),
    }


def export_backup_adapter_report(
    *,
    source_report_path: str | Path | None = None,
    mode: str = "dry_run",
    final_token: str | None = None,
    backup_run_dir: str | Path | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    result = build_backup_adapter_result(
        source_report_path=source_report_path,
        mode=mode,
        final_token=final_token,
        backup_run_dir=backup_run_dir,
    )
    success_statuses = {"dry_run", "no_backup_items", "completed", "completed_with_blocks"}
    warning_statuses = {"requires_final_confirmation", "no_backups_completed"}
    if result["status"] in success_statuses:
        status = "success"
    elif result["status"] in warning_statuses:
        status = "warning"
    else:
        status = "error"

    report = create_report(
        tool_name=BACKUP_ADAPTER_TOOL,
        action="backup_adapter_run",
        status=status,
        risk_level="medium",
        input_data={
            "source_report_path": str(source_report_path) if source_report_path else None,
            "mode": mode,
            "final_token_provided": bool(final_token),
            "backup_run_dir": str(backup_run_dir) if backup_run_dir else result.get("backup_run_dir"),
        },
        results=result,
        recommendations=[
            "Backup Adapter v1 only handles needs_backup decisions.",
            "Backup copy preserves the source file; use the manifest as copy evidence, not as an undo requirement.",
            "Protected sources are blocked even for backup.",
        ],
        summary=result["summary"],
        manifest=result.get("manifest"),
        undo_available=False,
        tags=merge_report_tags(
            ["backup_adapter", "needs_backup", "copy_only", "guarded_execution"],
            extra_tags,
        ),
    )
    log_action(
        BACKUP_ADAPTER_TOOL,
        "export_backup_adapter_report",
        status,
        {
            "report": str(report),
            "mode": mode,
            "result_status": result["status"],
            "manifest": result.get("manifest"),
            "backup_requested_count": result["summary"]["backup_requested_count"],
            "backed_up_count": result["summary"]["backed_up_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "backup": result,
    }


def print_backup_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== BACKUP ADAPTER V1 ==========")
    print(f"Status: {result['status']}")
    print(f"Mode: {result['mode']}")
    print(f"Backup requested: {summary['backup_requested_count']}")
    print(f"Backupable: {summary['backupable_count']}")
    print(f"Backed up: {summary['backed_up_count']}")
    print(f"Blocked: {summary['blocked_count']}")
    print(f"Errors: {summary['error_count']}")
    print(f"Backup dir: {summary.get('backup_run_dir')}")
    print(f"Manifest: {summary.get('manifest')}")
    for step in result.get("steps", [])[:50]:
        print(f"- {step['selection_id']} | {step['step_status']} | {step.get('source_info', {}).get('risk')} | {step.get('path')}")
        print(f"  {step.get('reason')}")
        if step.get("planned_backup_path"):
            print(f"  Backup: {step['planned_backup_path']}")
        if step.get("actual_backup_path"):
            print(f"  Copied: {step['actual_backup_path']}")


def run_backup_adapter() -> None:
    while True:
        print("""
========== BACKUP ADAPTER V1 ==========
1. Dry-run latest selection decision report
2. Apply latest selection decision report with token
3. Dry-run explicit selection decision report
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            result = export_backup_adapter_report(mode="dry_run")
            print_backup_summary(result["backup"])

        elif choice == "2":
            dry_run = export_backup_adapter_report(mode="dry_run")
            print_backup_summary(dry_run["backup"])
            if dry_run["backup"]["summary"]["backupable_count"] <= 0:
                print("Khong co file nao du dieu kien backup.")
                continue
            print(f"Final backup token required: {FINAL_BACKUP_TOKEN}")
            token = input("Nhap final backup token de apply, bo trong de huy: ").strip()
            if not token:
                print("Da huy apply backup.")
                continue
            result = export_backup_adapter_report(mode="apply", final_token=token)
            print_backup_summary(result["backup"])

        elif choice == "3":
            source = input("Nhap report path: ").strip().strip('"')
            result = export_backup_adapter_report(source_report_path=source, mode="dry_run")
            print_backup_summary(result["backup"])

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_backup_adapter()
