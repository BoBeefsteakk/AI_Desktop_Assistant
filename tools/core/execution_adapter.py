from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report, read_recent_report_index
from tools.core.risk_classifier import classify_file_risk


EXECUTION_ADAPTER_TOOL = "execution_adapter"
EXECUTION_ADAPTER_SCHEMA = "execution_adapter_v1"
EXPECTED_SELECTION_DECISION_SCHEMA = "bot_selection_decision_v2"
FINAL_CONFIRM_TOKEN = "EXECUTE_SELECTION_V1"
RECORD_ONLY_DECISIONS = {"keep", "manual_review", "skip"}
BLOCKED_FILE_OPERATION_DECISIONS = {"needs_backup", "move_later", "delete_candidate"}


def safe_read_json(path: str | Path) -> dict[str, Any] | None:
    report_path = Path(path)
    if not report_path.exists():
        return None
    try:
        with report_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def get_latest_selection_decision_report(limit: int = 500) -> dict[str, Any] | None:
    records = read_recent_report_index(limit=limit)
    for record in reversed(records):
        if record.get("tool") == "bot_controller" and record.get("action") == "export_selection_decision":
            return record
    return None


def load_selection_decision_report(
    source_report_path: str | Path | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    if source_report_path:
        return safe_read_json(source_report_path), str(source_report_path)

    latest = get_latest_selection_decision_report()
    if latest is None:
        return None, None

    report_path = latest.get("report_path")
    if not report_path:
        return None, None
    return safe_read_json(report_path), str(report_path)


def extract_decision_payload(report_data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(report_data, dict):
        return None
    payload = report_data.get("results")
    return payload if isinstance(payload, dict) else None


def validate_selection_decision_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []

    if payload is None:
        return {
            "status": "invalid",
            "issues": ["Missing selection decision payload."],
            "warnings": [],
        }

    if payload.get("schema") != EXPECTED_SELECTION_DECISION_SCHEMA:
        issues.append(
            f"Expected schema {EXPECTED_SELECTION_DECISION_SCHEMA}, got {payload.get('schema')}"
        )

    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        issues.append("Missing or invalid summary.")
        summary = {}

    if int(summary.get("invalid_count") or 0) > 0:
        issues.append("Selection decision report contains invalid items.")
    if int(summary.get("blocked_count") or 0) > 0:
        issues.append("Selection decision report contains blocked items.")

    safety_contract = payload.get("safety_contract", {})
    if not isinstance(safety_contract, dict):
        issues.append("Missing safety_contract.")
    elif safety_contract.get("executes_file_operations") is not False:
        issues.append("Selection decision report must not have executed file operations.")

    selected = payload.get("selected", [])
    skipped = payload.get("skipped", [])
    if not isinstance(selected, list):
        issues.append("selected must be a list.")
    if not isinstance(skipped, list):
        issues.append("skipped must be a list.")

    if int(summary.get("selected_count") or 0) == 0 and int(summary.get("skipped_count") or 0) == 0:
        warnings.append("Selection decision report has no selected/skipped items.")

    return {
        "status": "valid" if not issues else "invalid",
        "issues": issues,
        "warnings": warnings,
    }


def inspect_path(path: str | None) -> dict[str, Any]:
    if not path:
        return {
            "path": path,
            "exists": False,
            "risk": "unknown",
            "reason": "Missing path.",
        }

    file_path = Path(path)
    risk = classify_file_risk(file_path)
    return {
        "path": str(file_path),
        "exists": file_path.exists(),
        "risk": risk.get("risk"),
        "risk_category": risk.get("category"),
        "reason": risk.get("reason"),
        "can_user_confirm": risk.get("can_user_confirm"),
        "can_auto_delete": risk.get("can_auto_delete"),
        "matched_rule": risk.get("matched_rule"),
    }


def build_execution_step(item: dict[str, Any], *, source_bucket: str) -> dict[str, Any]:
    decision = str(item.get("decision") or "").strip().lower()
    path_info = inspect_path(item.get("path"))
    base = {
        "selection_id": item.get("selection_id"),
        "path": item.get("path"),
        "name": item.get("name"),
        "size_text": item.get("size_text"),
        "selection_group": item.get("selection_group"),
        "policy_decision": item.get("policy_decision"),
        "plan_action": item.get("plan_action"),
        "decision": decision,
        "source_bucket": source_bucket,
        "path_info": path_info,
        "file_operation_enabled": False,
        "manifest_required": decision in {"move_later"},
        "undo_available": False,
    }

    if decision in RECORD_ONLY_DECISIONS:
        return {
            **base,
            "execution_type": "record_only",
            "can_adapter_apply": True,
            "step_status": "pending_record",
            "reason": "Decision can be recorded without touching files.",
        }

    if decision == "needs_backup":
        return {
            **base,
            "execution_type": "blocked_requires_backup_flow",
            "can_adapter_apply": False,
            "step_status": "blocked",
            "reason": "Backup flow is not implemented in Execution Adapter v1.",
        }

    if decision == "move_later":
        return {
            **base,
            "execution_type": "blocked_requires_destination_and_manifest",
            "can_adapter_apply": False,
            "step_status": "blocked",
            "reason": "Move requires a destination, manifest, and restore test before file operations are enabled.",
        }

    if decision == "delete_candidate":
        return {
            **base,
            "execution_type": "blocked_delete_not_enabled_v1",
            "can_adapter_apply": False,
            "step_status": "blocked",
            "reason": "Deletion is not enabled in Execution Adapter v1; delete_candidate is only recorded as intent.",
        }

    return {
        **base,
        "execution_type": "invalid_decision",
        "can_adapter_apply": False,
        "step_status": "invalid",
        "reason": "Unknown or unsupported decision.",
    }


def build_execution_steps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for item in payload.get("selected", []) or []:
        if isinstance(item, dict):
            steps.append(build_execution_step(item, source_bucket="selected"))
    for item in payload.get("skipped", []) or []:
        if isinstance(item, dict):
            steps.append(build_execution_step(item, source_bucket="skipped"))
    return steps


def summarize_execution_steps(
    steps: list[dict[str, Any]],
    *,
    adapter_executed: bool,
) -> dict[str, Any]:
    blocked = [item for item in steps if item["step_status"] == "blocked"]
    invalid = [item for item in steps if item["step_status"] == "invalid"]
    recordable = [item for item in steps if item["can_adapter_apply"]]
    missing_paths = [item for item in steps if not item["path_info"]["exists"]]
    by_decision: dict[str, int] = {}
    by_status: dict[str, int] = {}

    for item in steps:
        decision = item["decision"] or "unknown"
        status = item["step_status"]
        by_decision[decision] = by_decision.get(decision, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "total": len(steps),
        "recordable_noop_count": len(recordable),
        "blocked_count": len(blocked),
        "invalid_count": len(invalid),
        "missing_path_count": len(missing_paths),
        "adapter_executed": adapter_executed,
        "file_operations_executed": False,
        "file_operation_count": 0,
        "manifest": None,
        "undo_available": False,
        "by_decision": by_decision,
        "by_status": by_status,
    }


def apply_record_only_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    applied = []
    for item in steps:
        if item["can_adapter_apply"]:
            applied.append({
                **item,
                "step_status": "recorded",
                "executed": True,
                "reason": "Recorded decision; no file operation was performed.",
            })
        else:
            applied.append({
                **item,
                "executed": False,
            })
    return applied


def build_execution_adapter_result(
    *,
    source_report_path: str | Path | None = None,
    mode: str = "dry_run",
    final_token: str | None = None,
) -> dict[str, Any]:
    report_data, report_path = load_selection_decision_report(source_report_path)
    payload = extract_decision_payload(report_data)
    validation = validate_selection_decision_payload(payload)

    if report_data is None or payload is None:
        return {
            "schema": EXECUTION_ADAPTER_SCHEMA,
            "status": "missing_source_report",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "summary": summarize_execution_steps([], adapter_executed=False),
            "steps": [],
            "safety_contract": build_safety_contract(),
        }

    steps = build_execution_steps(payload)
    mode = str(mode or "dry_run").strip().lower()

    if validation["status"] != "valid":
        return {
            "schema": EXECUTION_ADAPTER_SCHEMA,
            "status": "invalid_decision_report",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_execution_steps(steps, adapter_executed=False),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if mode not in {"dry_run", "apply"}:
        return {
            "schema": EXECUTION_ADAPTER_SCHEMA,
            "status": "invalid_mode",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_execution_steps(steps, adapter_executed=False),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if mode == "dry_run":
        return {
            "schema": EXECUTION_ADAPTER_SCHEMA,
            "status": "dry_run",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_execution_steps(steps, adapter_executed=False),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    if final_token != FINAL_CONFIRM_TOKEN:
        return {
            "schema": EXECUTION_ADAPTER_SCHEMA,
            "status": "requires_final_confirmation",
            "mode": mode,
            "source_report": report_path,
            "validation": validation,
            "selection_summary": payload.get("summary", {}),
            "summary": summarize_execution_steps(steps, adapter_executed=False),
            "steps": steps,
            "safety_contract": build_safety_contract(),
        }

    applied_steps = apply_record_only_steps(steps)
    summary = summarize_execution_steps(applied_steps, adapter_executed=True)
    status = "completed_with_blocks" if summary["blocked_count"] else "completed"

    return {
        "schema": EXECUTION_ADAPTER_SCHEMA,
        "status": status,
        "mode": mode,
        "source_report": report_path,
        "validation": validation,
        "selection_summary": payload.get("summary", {}),
        "summary": summary,
        "steps": applied_steps,
        "safety_contract": build_safety_contract(),
    }


def build_safety_contract() -> dict[str, Any]:
    return {
        "requires_final_token": True,
        "final_token": FINAL_CONFIRM_TOKEN,
        "file_operations_enabled": False,
        "delete_enabled": False,
        "move_enabled": False,
        "record_only_decisions": sorted(RECORD_ONLY_DECISIONS),
        "blocked_file_operation_decisions": sorted(BLOCKED_FILE_OPERATION_DECISIONS),
        "manifest_required_for_future_file_operations": True,
        "executes_file_operations": False,
    }


def export_execution_adapter_report(
    *,
    source_report_path: str | Path | None = None,
    mode: str = "dry_run",
    final_token: str | None = None,
) -> dict[str, Any]:
    result = build_execution_adapter_result(
        source_report_path=source_report_path,
        mode=mode,
        final_token=final_token,
    )
    status = "success" if result["status"] in {"dry_run", "completed", "completed_with_blocks"} else "warning"
    report = create_report(
        tool_name=EXECUTION_ADAPTER_TOOL,
        action="execution_adapter_run",
        status=status,
        risk_level="safe",
        input_data={
            "source_report_path": str(source_report_path) if source_report_path else None,
            "mode": mode,
            "final_token_provided": bool(final_token),
        },
        results=result,
        recommendations=[
            "Execution Adapter v1 records safe decisions only; it does not delete or move files.",
            "Move/delete decisions remain blocked until a manifest-backed file operation layer is implemented.",
            "Use dry_run first, then apply only with the final token after reviewing blocked steps.",
        ],
        summary=result["summary"],
        undo_available=False,
        tags=["execution_adapter", "bot_controller", "guarded_execution", "read_only_v1"],
    )
    log_action(
        EXECUTION_ADAPTER_TOOL,
        "export_execution_adapter_report",
        status,
        {
            "report": str(report),
            "mode": mode,
            "result_status": result["status"],
            "file_operations_executed": result["summary"]["file_operations_executed"],
        },
    )
    print(f"Report: {report}")
    return {
        "status": status,
        "report": str(report),
        "execution": result,
    }


def print_execution_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print("\n========== EXECUTION ADAPTER V1 ==========")
    print(f"Status: {result['status']}")
    print(f"Mode: {result['mode']}")
    print(f"Source report: {result.get('source_report')}")
    print(f"Total steps: {summary['total']}")
    print(f"Recordable no-op: {summary['recordable_noop_count']}")
    print(f"Blocked: {summary['blocked_count']}")
    print(f"Invalid: {summary['invalid_count']}")
    print(f"File operations executed: {summary['file_operations_executed']}")
    print(f"Manifest: {summary['manifest']}")

    for item in result["steps"][:30]:
        print(
            f"- {item.get('selection_id')} | {item.get('decision')} | "
            f"{item.get('step_status')} | {item.get('path')}"
        )
        print(f"  {item.get('reason')}")


def run_execution_adapter() -> None:
    while True:
        print("""
========== EXECUTION ADAPTER V1 ==========
1. Preview latest selection decision dry-run
2. Export dry-run execution report
3. Apply record-only decisions with final token
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_execution_summary(build_execution_adapter_result(mode="dry_run"))

        elif choice == "2":
            export_execution_adapter_report(mode="dry_run")

        elif choice == "3":
            print(f"Final token required: {FINAL_CONFIRM_TOKEN}")
            token = input("Nhap final token: ").strip()
            result = export_execution_adapter_report(mode="apply", final_token=token)
            print_execution_summary(result["execution"])

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_execution_adapter()
