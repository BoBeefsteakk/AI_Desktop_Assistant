from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.core.assistant_logger import log_action
from tools.core.execution_adapter import (
    extract_decision_payload,
    load_selection_decision_report,
    validate_selection_decision_payload,
)
from tools.core.report_manager import create_report
from tools.core.risk_classifier import SAFE_DELETE, classify_file_risk
from tools.core.safe_executor import safe_delete


SAFE_DELETE_ADAPTER_TOOL = "safe_delete_adapter"
SAFE_DELETE_ADAPTER_SCHEMA = "safe_delete_adapter_v1"
FINAL_DELETE_TOKEN = "DELETE_SELECTION_V1"
SUPPORTED_DELETE_DECISION = "delete_candidate"


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


def build_delete_source_info(path: str | Path | None) -> dict[str, Any]:
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
            "reason": "Safe Delete Adapter v1 deletes files only.",
        }

    if risk.get("risk") != SAFE_DELETE:
        return {
            "path": str(source),
            "status": "blocked_by_risk",
            "valid": False,
            "risk": risk.get("risk"),
            "risk_category": risk.get("category"),
            "matched_rule": risk.get("matched_rule"),
            "reason": "Only risk=safe_delete can be deleted by this adapter.",
        }

    return {
        "path": str(source),
        "status": "valid",
        "valid": True,
        "risk": risk.get("risk"),
        "risk_category": risk.get("category"),
        "matched_rule": risk.get("matched_rule"),
        "reason": "Source is valid for safe delete after final token.",
    }


def build_delete_step(item: dict[str, Any]) -> dict[str, Any]:
    decision = str(item.get("decision") or "").strip().lower()
    source_info = build_delete_source_info(item.get("path"))
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
        "file_operation": "delete_to_recycle_bin",
        "manifest_required": False,
        "undo_available_after_apply": False,
        "recycle_bin_only": True,
    }

    if decision != SUPPORTED_DELETE_DECISION:
        return {
            **base,
            "step_status": "not_in_scope",
            "can_delete": False,
            "reason": "Only delete_candidate decisions are handled by Safe Delete Adapter v1.",
        }

    if not source_info.get("valid"):
        return {
            **base,
            "step_status": "blocked",
            "can_delete": False,
            "reason": source_info.get("reason") or "Source is invalid.",
        }

    return {
        **base,
        "step_status": "pending_delete",
        "can_delete": True,
        "reason": "Ready to send to Recycle Bin after final confirmation token.",
    }


def build_delete_steps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        build_delete_step(item)
        for item in iter_selected_items(payload)
    ]


def summarize_delete_steps(
    steps: list[dict[str, Any]],
    *,
    adapter_executed: bool,
) -> dict[str, Any]:
    delete_requested = [item for item in steps if item["decision"] == SUPPORTED_DELETE_DECISION]
    deletable = [item for item in steps if item.get("can_delete")]
    deleted = [item for item in steps if item["step_status"] == "deleted"]
    blocked = [item for item in steps if item["step_status"] == "blocked"]
    errors = [item for item in steps if item["step_status"] == "error"]
    not_in_scope = [item for item in steps if item["step_status"] == "not_in_scope"]

    return {
        "total": len(steps),
        "delete_requested_count": len(delete_requested),
        "deletable_count": len(deletable),
        "deleted_count": len(deleted),
        "blocked_count": len(blocked),
        "error_count": len(errors),
        "not_in_scope_count": len(not_in_scope),
        "adapter_executed": adapter_executed,
        "file_operations_executed": bool(deleted),
        "file_operation_count": len(deleted),
        "recycle_bin_only": True,
        "manifest": None,
        "undo_available": False,
    }


def apply_delete_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    applied_steps: list[dict[str, Any]] = []

    for item in steps:
        if not item.get("can_delete"):
            applied_steps.append({**item, "executed": False})
            continue

        result = safe_delete(item["source_info"]["path"])
        if result.get("status") == "deleted":
            applied_steps.append({
                **item,
                "step_status": "deleted",
                "executed": True,
                "delete_result": result,
                "reason": "Sent to Recycle Bin with safe_delete.",
            })
        else:
            applied_steps.append({
                **item,
                "step_status": "error" if result.get("status") == "error" else "blocked",
                "executed": False,
                "delete_result": result,
                "reason": result.get("reason") or "safe_delete did not delete this file.",
            })

    return applied_steps


def build_safety_contract() -> dict[str, Any]:
    return {
        "schema": SAFE_DELETE_ADAPTER_SCHEMA,
        "supported_decisions": [SUPPORTED_DELETE_DECISION],
        "requires_final_token": True,
        "final_token": FINAL_DELETE_TOKEN,
        "files_only_v1": True,
        "requires_risk": SAFE_DELETE,
        "blocks_review_required": True,
        "blocks_protected": True,
        "delete_enabled": True,
        "move_enabled": False,
        "uses_safe_delete": True,
        "permanent_delete": False,
        "recycle_bin_only": True,
        "undo_strategy": "recycle_bin",
    }


def build_safe_delete_adapter_result(
    *,
    source_report_path: str | Path | None = None,
    mode: str = "dry_run",
    final_token: str | None = None,
) -> dict[str, Any]:
    report_data, report_path = load_selection_decision_report(source_report_path)
    payload = extract_decision_payload(report_data)
    validation = validate_selection_decision_payload(payload)
    mode = str(mode or "dry_run").strip().lower()

    if report_data is None or payload is None:
        return {
            "schema": SAFE_DELETE_ADAPTER_SCHEMA,
            "status": "missing_source_report",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "summary": summarize_delete_steps([], adapter_executed=False),
            "steps": [],
            "safety_contract": build_safety_contract(),
        }

    steps = build_delete_steps(payload)

    if validation["status"] != "valid":
        return {
            "schema": SAFE_DELETE_ADAPTER_SCHEMA,
            "status": "invalid_decision_report",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_delete_steps(steps, adapter_executed=False),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if mode not in {"dry_run", "apply"}:
        return {
            "schema": SAFE_DELETE_ADAPTER_SCHEMA,
            "status": "invalid_mode",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_delete_steps(steps, adapter_executed=False),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    dry_summary = summarize_delete_steps(steps, adapter_executed=False)
    if mode == "dry_run":
        status = "dry_run" if dry_summary["delete_requested_count"] else "no_delete_items"
        return {
            "schema": SAFE_DELETE_ADAPTER_SCHEMA,
            "status": status,
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if dry_summary["delete_requested_count"] <= 0:
        return {
            "schema": SAFE_DELETE_ADAPTER_SCHEMA,
            "status": "no_delete_items",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if final_token != FINAL_DELETE_TOKEN:
        return {
            "schema": SAFE_DELETE_ADAPTER_SCHEMA,
            "status": "requires_final_confirmation",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": dry_summary,
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    applied_steps = apply_delete_steps(steps)
    summary = summarize_delete_steps(applied_steps, adapter_executed=True)
    if summary["error_count"]:
        status = "completed_with_errors"
    elif summary["blocked_count"]:
        status = "completed_with_blocks"
    elif summary["deleted_count"]:
        status = "completed"
    else:
        status = "no_deletes_completed"

    return {
        "schema": SAFE_DELETE_ADAPTER_SCHEMA,
        "status": status,
        "mode": mode,
        "source_report": report_path,
        "validation": validation,
        "selection_summary": payload.get("summary", {}),
        "summary": summary,
        "steps": applied_steps,
        "manifest": None,
        "undo_available": False,
        "safety_contract": build_safety_contract(),
    }


def export_safe_delete_adapter_report(
    *,
    source_report_path: str | Path | None = None,
    mode: str = "dry_run",
    final_token: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    result = build_safe_delete_adapter_result(
        source_report_path=source_report_path,
        mode=mode,
        final_token=final_token,
    )
    success_statuses = {"dry_run", "no_delete_items", "completed", "completed_with_blocks"}
    warning_statuses = {"requires_final_confirmation", "no_deletes_completed"}
    if result["status"] in success_statuses:
        status = "success"
    elif result["status"] in warning_statuses:
        status = "warning"
    else:
        status = "error"

    report = create_report(
        tool_name=SAFE_DELETE_ADAPTER_TOOL,
        action="safe_delete_adapter_run",
        status=status,
        risk_level="medium",
        input_data={
            "source_report_path": str(source_report_path) if source_report_path else None,
            "mode": mode,
            "final_token_provided": bool(final_token),
        },
        results=result,
        recommendations=[
            "Safe Delete Adapter v1 only handles delete_candidate decisions.",
            "Only risk=safe_delete files are sent to Recycle Bin; review_required/protected are blocked.",
            "Recycle Bin undo is outside this tool; inspect the report before emptying Recycle Bin.",
        ],
        summary=result["summary"],
        manifest=None,
        undo_available=False,
        tags=merge_report_tags(
            ["safe_delete_adapter", "delete_candidate", "recycle_bin", "guarded_execution"],
            extra_tags,
        ),
    )
    log_action(
        SAFE_DELETE_ADAPTER_TOOL,
        "export_safe_delete_adapter_report",
        status,
        {
            "report": str(report),
            "mode": mode,
            "result_status": result["status"],
            "delete_requested_count": result["summary"]["delete_requested_count"],
            "deleted_count": result["summary"]["deleted_count"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "delete": result,
    }


def print_delete_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== SAFE DELETE ADAPTER V1 ==========")
    print(f"Status: {result['status']}")
    print(f"Mode: {result['mode']}")
    print(f"Delete requested: {summary['delete_requested_count']}")
    print(f"Deletable: {summary['deletable_count']}")
    print(f"Deleted: {summary['deleted_count']}")
    print(f"Blocked: {summary['blocked_count']}")
    print(f"Errors: {summary['error_count']}")
    for step in result.get("steps", [])[:50]:
        print(f"- {step['selection_id']} | {step['step_status']} | {step.get('source_info', {}).get('risk')} | {step.get('path')}")
        print(f"  {step.get('reason')}")


def run_safe_delete_adapter() -> None:
    while True:
        print("""
========== SAFE DELETE ADAPTER V1 ==========
1. Dry-run latest selection decision report
2. Apply latest selection decision report with token
3. Dry-run explicit selection decision report
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            result = export_safe_delete_adapter_report(mode="dry_run")
            print_delete_summary(result["delete"])

        elif choice == "2":
            dry_run = export_safe_delete_adapter_report(mode="dry_run")
            print_delete_summary(dry_run["delete"])
            if dry_run["delete"]["summary"]["deletable_count"] <= 0:
                print("Khong co file nao du dieu kien safe_delete.")
                continue
            print(f"Final delete token required: {FINAL_DELETE_TOKEN}")
            token = input("Nhap final delete token de apply, bo trong de huy: ").strip()
            if not token:
                print("Da huy apply delete.")
                continue
            result = export_safe_delete_adapter_report(mode="apply", final_token=token)
            print_delete_summary(result["delete"])

        elif choice == "3":
            source = input("Nhap report path: ").strip().strip('"')
            result = export_safe_delete_adapter_report(source_report_path=source, mode="dry_run")
            print_delete_summary(result["delete"])

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_safe_delete_adapter()
