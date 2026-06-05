from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.core.assistant_logger import log_action
from tools.core.execution_adapter import (
    EXPECTED_SELECTION_DECISION_SCHEMA,
    extract_decision_payload,
    load_selection_decision_report,
    validate_selection_decision_payload,
)
from tools.core.report_manager import create_report
from tools.core.risk_classifier import PROTECTED, classify_file_risk, resolve_path
from tools.core.safety_utils import safe_move, save_manifest


FILE_OPERATION_ADAPTER_TOOL = "file_operation_adapter"
FILE_OPERATION_ADAPTER_SCHEMA = "file_operation_adapter_v1"
FINAL_MOVE_TOKEN = "MOVE_SELECTION_V1"
SUPPORTED_MOVE_DECISION = "move_later"


def merge_report_tags(base_tags: list[str], extra_tags: list[str] | None = None) -> list[str]:
    tags: list[str] = []
    for tag in [*base_tags, *(extra_tags or [])]:
        text = str(tag).strip()
        if text and text not in tags:
            tags.append(text)
    return tags


def is_same_path(left: Path, right: Path) -> bool:
    return resolve_path(left) == resolve_path(right)


def build_destination_info(destination_root: str | Path | None) -> dict[str, Any]:
    if not destination_root:
        return {
            "path": None,
            "status": "missing",
            "valid": False,
            "reason": "Destination root is required.",
        }

    destination = Path(destination_root)
    risk = classify_file_risk(destination)

    if not destination.exists():
        return {
            "path": str(destination),
            "status": "missing",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "reason": "Destination root must already exist in v1.",
        }

    if not destination.is_dir():
        return {
            "path": str(destination),
            "status": "not_directory",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "reason": "Destination root must be a directory.",
        }

    if is_same_path(destination, Path(destination.anchor)):
        return {
            "path": str(destination),
            "status": "drive_root",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "reason": "Destination root cannot be a drive root in v1.",
        }

    if risk.get("risk") == PROTECTED:
        return {
            "path": str(destination),
            "status": "protected",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "matched_rule": risk.get("matched_rule"),
            "reason": "Destination is protected.",
        }

    return {
        "path": str(destination),
        "status": "valid",
        "valid": True,
        "risk": risk.get("risk"),
        "risk_category": risk.get("category"),
        "matched_rule": risk.get("matched_rule"),
        "reason": "Destination is valid.",
    }


def build_source_info(path: str | Path | None) -> dict[str, Any]:
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
            "reason": "File Operation Adapter v1 moves files only.",
        }

    if risk.get("risk") == PROTECTED:
        return {
            "path": str(source),
            "status": "protected",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "matched_rule": risk.get("matched_rule"),
            "reason": "Source path is protected.",
        }

    return {
        "path": str(source),
        "status": "valid",
        "valid": True,
        "risk": risk.get("risk"),
        "risk_category": risk.get("category"),
        "matched_rule": risk.get("matched_rule"),
        "can_user_confirm": risk.get("can_user_confirm"),
        "reason": "Source is valid for explicit move confirmation.",
    }


def plan_collision_safe_target(source: Path, destination_root: Path) -> Path:
    target = destination_root / source.name
    final_target = target
    count = 1
    while final_target.exists():
        final_target = target.with_name(f"{target.stem}_{count}{target.suffix}")
        count += 1
    return final_target


def iter_selected_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for item in payload.get("selected", []) or []:
        if isinstance(item, dict):
            items.append(item)
    return items


def build_move_step(
    item: dict[str, Any],
    *,
    destination_info: dict[str, Any],
) -> dict[str, Any]:
    decision = str(item.get("decision") or "").strip().lower()
    source_info = build_source_info(item.get("path"))
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
        "destination_info": destination_info,
        "file_operation": "move",
        "manifest_required": True,
        "undo_available_after_apply": False,
    }

    if decision != SUPPORTED_MOVE_DECISION:
        return {
            **base,
            "step_status": "not_in_scope",
            "can_move": False,
            "reason": "Only move_later decisions are handled by File Operation Adapter v1.",
        }

    if not destination_info.get("valid"):
        return {
            **base,
            "step_status": "blocked",
            "can_move": False,
            "reason": destination_info.get("reason") or "Destination is invalid.",
        }

    if not source_info.get("valid"):
        return {
            **base,
            "step_status": "blocked",
            "can_move": False,
            "reason": source_info.get("reason") or "Source is invalid.",
        }

    source = Path(source_info["path"])
    destination_root = Path(destination_info["path"])
    if is_same_path(source.parent, destination_root):
        return {
            **base,
            "step_status": "blocked",
            "can_move": False,
            "reason": "Destination root is the same as the source folder.",
        }

    planned_target = plan_collision_safe_target(source, destination_root)
    return {
        **base,
        "step_status": "pending_move",
        "can_move": True,
        "planned_target": str(planned_target),
        "reason": "Ready to move after final confirmation.",
    }


def build_move_steps(
    payload: dict[str, Any],
    *,
    destination_info: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        build_move_step(item, destination_info=destination_info)
        for item in iter_selected_items(payload)
    ]


def summarize_move_steps(
    steps: list[dict[str, Any]],
    *,
    adapter_executed: bool,
    manifest: str | None = None,
) -> dict[str, Any]:
    move_requested = [item for item in steps if item["decision"] == SUPPORTED_MOVE_DECISION]
    movable = [item for item in steps if item.get("can_move")]
    moved = [item for item in steps if item["step_status"] == "moved"]
    blocked = [item for item in steps if item["step_status"] == "blocked"]
    errors = [item for item in steps if item["step_status"] == "error"]
    not_in_scope = [item for item in steps if item["step_status"] == "not_in_scope"]

    return {
        "total": len(steps),
        "move_requested_count": len(move_requested),
        "movable_count": len(movable),
        "moved_count": len(moved),
        "blocked_count": len(blocked),
        "error_count": len(errors),
        "not_in_scope_count": len(not_in_scope),
        "adapter_executed": adapter_executed,
        "file_operations_executed": bool(moved),
        "file_operation_count": len(moved),
        "manifest": manifest,
        "undo_available": bool(manifest),
    }


def apply_move_steps(steps: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    applied_steps: list[dict[str, Any]] = []
    moved_records: list[dict[str, Any]] = []

    for item in steps:
        if not item.get("can_move"):
            applied_steps.append({**item, "executed": False})
            continue

        try:
            record = safe_move(item["source_info"]["path"], item["planned_target"])
            manifest_record = {
                **record,
                "selection_id": item.get("selection_id"),
                "decision": item.get("decision"),
                "operation": "move",
            }
            moved_records.append(manifest_record)
            applied_steps.append({
                **item,
                "step_status": "moved",
                "executed": True,
                "actual_target": record["new_path"],
                "reason": "Moved with safe_move and recorded in manifest.",
            })
        except Exception as exc:
            applied_steps.append({
                **item,
                "step_status": "error",
                "executed": False,
                "error": str(exc),
                "reason": "Move failed; no manifest record was created for this item.",
            })

    manifest_path = None
    if moved_records:
        manifest_path = str(save_manifest("file_operation_adapter_move", moved_records))

    return applied_steps, manifest_path


def build_safety_contract() -> dict[str, Any]:
    return {
        "schema": FILE_OPERATION_ADAPTER_SCHEMA,
        "supported_decisions": [SUPPORTED_MOVE_DECISION],
        "requires_final_token": True,
        "final_token": FINAL_MOVE_TOKEN,
        "requires_existing_destination": True,
        "files_only_v1": True,
        "blocks_protected_source": True,
        "blocks_protected_destination": True,
        "delete_enabled": False,
        "move_enabled": True,
        "uses_safe_move": True,
        "manifest_required": True,
        "undo_strategy": "manifest_restore",
    }


def build_file_operation_adapter_result(
    *,
    source_report_path: str | Path | None = None,
    destination_root: str | Path | None = None,
    mode: str = "dry_run",
    final_token: str | None = None,
) -> dict[str, Any]:
    report_data, report_path = load_selection_decision_report(source_report_path)
    payload = extract_decision_payload(report_data)
    validation = validate_selection_decision_payload(payload)
    destination_info = build_destination_info(destination_root)
    mode = str(mode or "dry_run").strip().lower()

    if report_data is None or payload is None:
        return {
            "schema": FILE_OPERATION_ADAPTER_SCHEMA,
            "status": "missing_source_report",
            "mode": mode,
            "source_report": report_path,
            "destination": destination_info,
            "validation": validation,
            "summary": summarize_move_steps([], adapter_executed=False),
            "steps": [],
            "safety_contract": build_safety_contract(),
        }

    steps = build_move_steps(payload, destination_info=destination_info)

    if validation["status"] != "valid":
        return {
            "schema": FILE_OPERATION_ADAPTER_SCHEMA,
            "status": "invalid_decision_report",
            "mode": mode,
            "source_report": report_path,
            "destination": destination_info,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_move_steps(steps, adapter_executed=False),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if mode not in {"dry_run", "apply"}:
        return {
            "schema": FILE_OPERATION_ADAPTER_SCHEMA,
            "status": "invalid_mode",
            "mode": mode,
            "source_report": report_path,
            "destination": destination_info,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_move_steps(steps, adapter_executed=False),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    dry_summary = summarize_move_steps(steps, adapter_executed=False)
    if mode == "dry_run":
        status = "dry_run" if dry_summary["move_requested_count"] else "no_move_items"
        if not destination_info.get("valid"):
            status = "destination_invalid"
        return {
            "schema": FILE_OPERATION_ADAPTER_SCHEMA,
            "status": status,
            "mode": mode,
            "source_report": report_path,
            "destination": destination_info,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if not destination_info.get("valid"):
        return {
            "schema": FILE_OPERATION_ADAPTER_SCHEMA,
            "status": "destination_invalid",
            "mode": mode,
            "source_report": report_path,
            "destination": destination_info,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if dry_summary["move_requested_count"] <= 0:
        return {
            "schema": FILE_OPERATION_ADAPTER_SCHEMA,
            "status": "no_move_items",
            "mode": mode,
            "source_report": report_path,
            "destination": destination_info,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if final_token != FINAL_MOVE_TOKEN:
        return {
            "schema": FILE_OPERATION_ADAPTER_SCHEMA,
            "status": "requires_final_confirmation",
            "mode": mode,
            "source_report": report_path,
            "destination": destination_info,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    applied_steps, manifest = apply_move_steps(steps)
    summary = summarize_move_steps(applied_steps, adapter_executed=True, manifest=manifest)
    if summary["error_count"]:
        status = "completed_with_errors"
    elif summary["blocked_count"]:
        status = "completed_with_blocks"
    elif summary["moved_count"]:
        status = "completed"
    else:
        status = "no_moves_completed"

    return {
        "schema": FILE_OPERATION_ADAPTER_SCHEMA,
        "status": status,
        "mode": mode,
        "source_report": report_path,
        "destination": destination_info,
        "validation": validation,
        "selection_summary": payload.get("summary", {}),
        "summary": summary,
        "steps": applied_steps,
        "manifest": manifest,
        "undo_available": bool(manifest),
        "safety_contract": build_safety_contract(),
    }


def export_file_operation_adapter_report(
    *,
    source_report_path: str | Path | None = None,
    destination_root: str | Path | None = None,
    mode: str = "dry_run",
    final_token: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    result = build_file_operation_adapter_result(
        source_report_path=source_report_path,
        destination_root=destination_root,
        mode=mode,
        final_token=final_token,
    )
    success_statuses = {"dry_run", "no_move_items", "completed", "completed_with_blocks"}
    warning_statuses = {"destination_invalid", "requires_final_confirmation", "no_moves_completed"}
    if result["status"] in success_statuses:
        status = "success"
    elif result["status"] in warning_statuses:
        status = "warning"
    else:
        status = "error"

    report = create_report(
        tool_name=FILE_OPERATION_ADAPTER_TOOL,
        action="file_operation_adapter_run",
        status=status,
        risk_level="medium",
        input_data={
            "source_report_path": str(source_report_path) if source_report_path else None,
            "destination_root": str(destination_root) if destination_root else None,
            "mode": mode,
            "final_token_provided": bool(final_token),
        },
        results=result,
        recommendations=[
            "File Operation Adapter v1 only moves move_later decisions.",
            "Use Undo Manager with the manifest if moved files need to be restored.",
            "Delete decisions remain disabled in this adapter.",
        ],
        summary=result["summary"],
        manifest=result.get("manifest"),
        undo_available=result.get("undo_available", False),
        tags=merge_report_tags(
            ["file_operation_adapter", "move_later", "manifest_restore", "guarded_execution"],
            extra_tags,
        ),
    )
    log_action(
        FILE_OPERATION_ADAPTER_TOOL,
        "export_file_operation_adapter_report",
        status,
        {
            "report": str(report),
            "mode": mode,
            "result_status": result["status"],
            "manifest": result.get("manifest"),
            "file_operations_executed": result["summary"]["file_operations_executed"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "operation": result,
    }


def print_operation_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== FILE OPERATION ADAPTER V1 ==========")
    print(f"Status: {result['status']}")
    print(f"Mode: {result['mode']}")
    print(f"Source report: {result.get('source_report')}")
    print(f"Destination: {result.get('destination', {}).get('path')}")
    print(f"Move requested: {summary['move_requested_count']}")
    print(f"Movable: {summary['movable_count']}")
    print(f"Moved: {summary['moved_count']}")
    print(f"Blocked: {summary['blocked_count']}")
    print(f"Errors: {summary['error_count']}")
    print(f"File operations executed: {summary['file_operations_executed']}")
    print(f"Manifest: {summary['manifest']}")

    for item in result["steps"][:30]:
        print(
            f"- {item.get('selection_id')} | {item.get('decision')} | "
            f"{item.get('step_status')} | {item.get('path')}"
        )
        print(f"  {item.get('reason')}")
        if item.get("planned_target"):
            print(f"  Target: {item['planned_target']}")
        if item.get("actual_target"):
            print(f"  Moved to: {item['actual_target']}")


def prompt_source_report_path() -> str | None:
    raw = input("Nhap path decision report (bo trong de dung latest): ").strip().strip('"')
    return raw or None


def prompt_destination_root() -> str:
    return input("Nhap folder dich da ton tai: ").strip().strip('"')


def run_file_operation_adapter() -> None:
    while True:
        print("""
========== FILE OPERATION ADAPTER V1 ==========
1. Preview move_later dry-run
2. Export move_later dry-run report
3. Apply move_later with final token
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            source_report = prompt_source_report_path()
            destination = prompt_destination_root()
            print_operation_summary(
                build_file_operation_adapter_result(
                    source_report_path=source_report,
                    destination_root=destination,
                    mode="dry_run",
                )
            )

        elif choice == "2":
            source_report = prompt_source_report_path()
            destination = prompt_destination_root()
            export_file_operation_adapter_report(
                source_report_path=source_report,
                destination_root=destination,
                mode="dry_run",
            )

        elif choice == "3":
            source_report = prompt_source_report_path()
            destination = prompt_destination_root()
            print(f"Final move token required: {FINAL_MOVE_TOKEN}")
            token = input("Nhap final move token: ").strip()
            result = export_file_operation_adapter_report(
                source_report_path=source_report,
                destination_root=destination,
                mode="apply",
                final_token=token,
            )
            print_operation_summary(result["operation"])

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_file_operation_adapter()
