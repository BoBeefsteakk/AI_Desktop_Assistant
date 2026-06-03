from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any

from tools.core.action_policy import build_policy_gate
from tools.core.assistant_logger import log_action
from tools.core.capability_registry import get_capability_by_id
from tools.core.recommendation_center import (
    DEFAULT_VISIBLE_STATES,
    collect_recommendation_queue,
    print_recommendation_queue,
    sync_recommendation_queue,
    update_recommendation_from_menu,
    update_recommendation_state,
)
from tools.core.report_manager import create_report


RUNNER_TOOL_NAME = "guided_action_runner"
OPEN_TOKEN = "OPEN"


def target_requires_confirmation(capability: dict[str, Any]) -> bool:
    return (
        capability["risk_level"] != "safe"
        or bool(capability["mutates_files"])
        or bool(capability["needs_confirmation"])
    )


def capability_accepts_no_required_args(capability: dict[str, Any]) -> dict[str, Any]:
    try:
        module = importlib.import_module(capability["module"])
        function = getattr(module, capability["function"])
        signature = inspect.signature(function)
    except Exception as exc:
        return {
            "executable": False,
            "reason": f"Cannot inspect entrypoint: {exc}",
        }

    required = []
    for name, parameter in signature.parameters.items():
        if parameter.default is not inspect.Parameter.empty:
            continue
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        required.append(name)

    if required:
        return {
            "executable": False,
            "reason": f"Entrypoint requires arguments: {required}",
        }

    return {
        "executable": True,
        "reason": "Entrypoint can be called from the main menu.",
    }


def build_action_context(recommendation: dict[str, Any]) -> dict[str, Any]:
    tool_id = str(recommendation.get("suggested_tool_id") or "").strip()
    context: dict[str, Any] = {
        "status": "ready",
        "issues": [],
        "recommendation": dict(recommendation),
        "capability": None,
        "target_requires_confirmation": None,
        "runner_requires_confirmation": True,
        "policy_gate": None,
    }

    if not tool_id:
        context["status"] = "no_suggested_tool"
        context["issues"].append("Recommendation does not include suggested_tool_id.")
        return context

    capability = get_capability_by_id(tool_id)
    if capability is None:
        context["status"] = "missing_capability"
        context["issues"].append(f"Capability not found: {tool_id}")
        return context

    context["capability"] = capability
    context["target_requires_confirmation"] = target_requires_confirmation(capability)
    policy_gate = build_policy_gate(recommendation, capability=capability)
    context["policy_gate"] = policy_gate
    if not policy_gate["can_open_target"]:
        context["status"] = policy_gate["status"]
        context["issues"].append(policy_gate["reason"])
        return context

    if capability["id"] == RUNNER_TOOL_NAME:
        context["status"] = "not_executable"
        context["issues"].append("Guided Action Runner refuses to open itself recursively.")
        return context

    execution_contract = capability_accepts_no_required_args(capability)
    context["entrypoint_contract"] = execution_contract
    if not execution_contract["executable"]:
        context["status"] = "not_executable"
        context["issues"].append(execution_contract["reason"])

    return context


def build_action_contexts(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_action_context(item) for item in queue]


def preview_guided_actions(
    *,
    report_limit: int = 80,
    include_report_issues: bool = True,
    include_test_reports: bool = False,
    state_file: str | Path | None = None,
    states: set[str] | list[str] | tuple[str, ...] | None = DEFAULT_VISIBLE_STATES,
) -> dict[str, Any]:
    sync_result = sync_recommendation_queue(
        report_limit=report_limit,
        include_report_issues=include_report_issues,
        include_test_reports=include_test_reports,
        state_file=state_file,
        states=states,
    )
    contexts = build_action_contexts(sync_result["queue"])
    ready_contexts = [
        item for item in contexts
        if item["status"] == "ready"
    ]

    return {
        "status": "ready" if ready_contexts else "empty",
        "sync_result": sync_result,
        "contexts": contexts,
        "ready_count": len(ready_contexts),
        "blocked_count": len(contexts) - len(ready_contexts),
    }


def find_guided_action_context(
    contexts: list[dict[str, Any]],
    *,
    recommendation_id: str | None = None,
    fingerprint: str | None = None,
) -> dict[str, Any] | None:
    for context in contexts:
        recommendation = context["recommendation"]
        if recommendation_id and recommendation.get("id") == recommendation_id:
            return context
        if fingerprint and recommendation.get("fingerprint") == fingerprint:
            return context
    return None


def action_context_to_line(context: dict[str, Any], index: int) -> str:
    recommendation = context["recommendation"]
    capability = context.get("capability") or {}
    tool_name = capability.get("name") or recommendation.get("suggested_tool_name") or "-"
    risk = capability.get("risk_level") or recommendation.get("suggested_tool_risk") or "-"
    state = recommendation.get("workflow_state") or "pending"
    policy_gate = context.get("policy_gate") or {}
    policy = policy_gate.get("decision") or recommendation.get("action_policy_decision") or "-"
    return (
        f"{index:>2}. [{str(recommendation.get('severity')).upper()}] "
        f"{recommendation.get('title')} | State: {state} | "
        f"Tool: {tool_name} ({risk}) | Status: {context['status']}\n"
        f"    {recommendation.get('detail')}\n"
        f"    Policy: {policy}\n"
        f"    ID: {recommendation.get('fingerprint')}"
    )


def print_guided_actions(contexts: list[dict[str, Any]]) -> None:
    if not contexts:
        print("Khong co recommendation pending/deferred de mo tool.")
        return

    print("\n========== GUIDED ACTIONS ==========")
    for index, context in enumerate(contexts, start=1):
        print(action_context_to_line(context, index))
        if context["issues"]:
            print(f"    Issues: {context['issues']}")


def print_action_context(context: dict[str, Any]) -> None:
    recommendation = context["recommendation"]
    capability = context.get("capability")

    print("\n========== GUIDED ACTION DETAIL ==========")
    print(f"Recommendation: {recommendation.get('title')}")
    print(f"Severity: {recommendation.get('severity')}")
    print(f"State: {recommendation.get('workflow_state')}")
    print(f"Detail: {recommendation.get('detail')}")
    print(f"Report: {recommendation.get('report_path')}")
    print(f"Status: {context['status']}")

    if context["issues"]:
        print(f"Issues: {context['issues']}")

    policy_gate = context.get("policy_gate")
    if policy_gate:
        print("\nAction policy gate:")
        print(f"- Status: {policy_gate['status']}")
        print(f"- Decision: {policy_gate.get('decision') or '-'}")
        print(f"- Can open target: {policy_gate['can_open_target']}")
        print(f"- Strong confirmation: {policy_gate['requires_strong_confirmation']}")
        print(f"- Required token: {policy_gate.get('confirmation_token') or '-'}")
        print(f"- Reason: {policy_gate['reason']}")
        for warning in policy_gate.get("warnings", []):
            print(f"- Warning: {warning}")

    if not capability:
        return

    external_apps = ", ".join(capability["external_apps"]) if capability["external_apps"] else "-"
    print("\nSuggested tool:")
    print(f"- ID: {capability['id']}")
    print(f"- Name: {capability['name']}")
    print(f"- Category: {capability['category']}")
    print(f"- Risk: {capability['risk_level']}")
    print(f"- Mutates files: {capability['mutates_files']}")
    print(f"- Needs confirmation: {capability['needs_confirmation']}")
    print(f"- Target confirmation expected: {context['target_requires_confirmation']}")
    print(f"- Undo strategy: {capability['undo_strategy']}")
    print(f"- External apps: {external_apps}")
    print(f"- Summary: {capability['summary']}")


def confirm_guided_action(context: dict[str, Any]) -> bool:
    if context["status"] != "ready":
        print("Recommendation nay chua the mo tool.")
        return False

    print_action_context(context)
    print(
        "\nRunner chi mo tool duoc de xuat. "
        "Neu tool do co thao tac nguy hiem, tool that van se hoi confirmation rieng."
    )
    policy_gate = context.get("policy_gate") or {}
    token = policy_gate.get("confirmation_token") or OPEN_TOKEN
    answer = input(f"Nhap {token} de mo tool, phim khac de huy: ").strip()
    return answer == token


def write_guided_action_report(
    context: dict[str, Any],
    *,
    action: str,
    status: str,
    execution_result: dict[str, Any],
) -> Path:
    recommendation = context["recommendation"]
    capability = context.get("capability") or {}
    report = create_report(
        tool_name=RUNNER_TOOL_NAME,
        action=action,
        status=status,
        risk_level="medium",
        input_data={
            "recommendation_id": recommendation.get("id"),
            "fingerprint": recommendation.get("fingerprint"),
            "target_tool_id": capability.get("id"),
            "target_tool_name": capability.get("name"),
            "policy_decision": (context.get("policy_gate") or {}).get("decision"),
        },
        results={
            "context_status": context["status"],
            "policy_gate": context.get("policy_gate"),
            "execution": execution_result,
            "recommendation": recommendation,
            "capability": capability,
        },
        recommendations=[
            "Guided Action Runner only opens the suggested tool after explicit confirmation.",
            "Target tools keep their own confirmation and safety logic.",
            "Mark the recommendation handled only after reviewing the target tool result.",
        ],
        summary={
            "status": status,
            "target_tool_id": capability.get("id"),
            "target_risk": capability.get("risk_level"),
            "target_mutates_files": bool(capability.get("mutates_files")),
            "target_needs_confirmation": bool(capability.get("needs_confirmation")),
            "policy_gate_status": (context.get("policy_gate") or {}).get("status"),
            "policy_decision": (context.get("policy_gate") or {}).get("decision"),
            "undo_available": False,
        },
        undo_available=False,
        tags=["guided_action", "recommendations", "confirmation"],
    )
    return report


def execute_guided_action(
    context: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    capability = context.get("capability")
    if context["status"] != "ready" or capability is None:
        result = {
            "status": "blocked",
            "executed": False,
            "issues": context["issues"],
        }
        report = write_guided_action_report(
            context,
            action="blocked",
            status="warning",
            execution_result=result,
        )
        result["report"] = str(report)
        log_action(RUNNER_TOOL_NAME, "blocked", "warning", result)
        return result

    if dry_run:
        result = {
            "status": "dry_run",
            "executed": False,
            "target_tool_id": capability["id"],
            "target_tool_name": capability["name"],
        }
        report = write_guided_action_report(
            context,
            action="dry_run",
            status="success",
            execution_result=result,
        )
        result["report"] = str(report)
        log_action(RUNNER_TOOL_NAME, "dry_run", "success", result)
        return result

    log_action(
        RUNNER_TOOL_NAME,
        "open_target_tool",
        "started",
        {
            "target_tool_id": capability["id"],
            "target_tool_name": capability["name"],
            "recommendation_id": context["recommendation"].get("id"),
        },
    )

    try:
        module = importlib.import_module(capability["module"])
        function = getattr(module, capability["function"])
        print(f"\nDang mo tool: {capability['name']}")
        function()
        result = {
            "status": "success",
            "executed": True,
            "target_tool_id": capability["id"],
            "target_tool_name": capability["name"],
        }
        report_status = "success"

    except KeyboardInterrupt:
        result = {
            "status": "cancelled",
            "executed": True,
            "target_tool_id": capability["id"],
            "target_tool_name": capability["name"],
            "error": "Interrupted by user.",
        }
        report_status = "warning"

    except Exception as exc:
        result = {
            "status": "error",
            "executed": True,
            "target_tool_id": capability["id"],
            "target_tool_name": capability["name"],
            "error": str(exc),
        }
        report_status = "error"

    report = write_guided_action_report(
        context,
        action="open_target_tool",
        status=report_status,
        execution_result=result,
    )
    result["report"] = str(report)
    log_action(RUNNER_TOOL_NAME, "open_target_tool", report_status, result)
    return result


def run_guided_action_by_index(
    index: int,
    *,
    report_limit: int = 80,
    state_file: str | Path | None = None,
    include_test_reports: bool = False,
    execute: bool = False,
) -> dict[str, Any]:
    preview = preview_guided_actions(
        report_limit=report_limit,
        state_file=state_file,
        include_test_reports=include_test_reports,
    )
    contexts = preview["contexts"]
    if index < 1 or index > len(contexts):
        return {
            "status": "invalid_index",
            "executed": False,
            "index": index,
            "context_count": len(contexts),
        }

    return execute_guided_action(contexts[index - 1], dry_run=not execute)


def choose_context_from_menu(contexts: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not contexts:
        print("Khong co action nao de chon.")
        return None

    print_guided_actions(contexts)
    raw_index = input("Nhap so thu tu recommendation muon mo tool: ").strip()
    if not raw_index.isdigit():
        print("Lua chon khong hop le.")
        return None

    index = int(raw_index) - 1
    if not 0 <= index < len(contexts):
        print("So thu tu khong hop le.")
        return None

    return contexts[index]


def maybe_mark_recommendation_after_run(
    context: dict[str, Any],
    *,
    state_file: str | Path | None = None,
) -> None:
    recommendation = context["recommendation"]
    fingerprint = str(recommendation.get("fingerprint") or "").strip()
    if not fingerprint:
        return

    answer = input("Danh dau recommendation nay la handled? [y/N]: ").strip().lower()
    if answer not in {"y", "yes", "ok"}:
        return

    update_recommendation_state(
        fingerprint,
        "handled",
        note="Marked handled after Guided Action Runner opened target tool.",
        state_file=state_file,
    )
    print(f"Da danh dau handled: {fingerprint}")


def run_guided_action_runner() -> None:
    while True:
        print("""
========== GUIDED ACTION RUNNER ==========
1. Sync + xem action pending/deferred
2. Mo tool tu recommendation
3. Doi trang thai recommendation
4. Xem queue goc tu Recommendation Center
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            preview = preview_guided_actions()
            print(f"Ready actions: {preview['ready_count']}")
            print(f"Blocked actions: {preview['blocked_count']}")
            print(f"State file: {preview['sync_result']['state_file']}")
            print_guided_actions(preview["contexts"])

        elif choice == "2":
            preview = preview_guided_actions()
            context = choose_context_from_menu(preview["contexts"])
            if context is None:
                continue
            if not confirm_guided_action(context):
                print("Da huy.")
                continue
            result = execute_guided_action(context)
            print(f"Guided action status: {result['status']}")
            print(f"Report: {result.get('report')}")
            if result["status"] in {"success", "cancelled"}:
                maybe_mark_recommendation_after_run(context)

        elif choice == "3":
            update_recommendation_from_menu()

        elif choice == "4":
            queue = collect_recommendation_queue(states=DEFAULT_VISIBLE_STATES)
            print_recommendation_queue(queue)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_guided_action_runner()
