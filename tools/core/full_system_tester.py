from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from config.settings import BASE_DIR, USER_SETTINGS_FILE, validate_user_settings
from tools.core.audit_center import get_audit_snapshot
from tools.core.action_policy import (
    build_action_policy_health,
    get_matching_policies_for_path,
    get_policy_for_recommendation,
    seed_default_action_policies,
    validate_action_policies,
)
from tools.core.behavior_tester import make_sandbox, cleanup_sandbox, write_text
from tools.core.action_planner import build_action_plan
from tools.core.backup_adapter import (
    BACKUP_ADAPTER_SCHEMA,
    FINAL_BACKUP_TOKEN,
    build_backup_adapter_result,
)
from tools.core.bot_controller import (
    build_bot_controller_result,
    build_selection_session_from_groups,
    build_selection_decision,
    execute_bot_decision,
    export_backup_selection_flow_report,
    export_move_later_selection_flow_report,
    export_safe_delete_selection_flow_report,
)
from tools.core.auto_scan_session import AUTO_SCAN_SESSION_SCHEMA, build_auto_scan_session_result
from tools.core.candidate_review import build_candidate_review
from tools.core.capability_registry import (
    get_capabilities,
    validate_capability_registry,
)
from tools.core.pre_feed_bundle import build_pre_feed_bundle
from tools.core.report_manager import (
    REPORT_SCHEMA_VERSION,
    create_report,
    read_recent_report_index,
    validate_report_file,
)
from tools.core.recommendation_center import (
    collect_recommendation_queue,
    summarize_recommendation_queue,
    sync_recommendation_queue,
    update_recommendation_state,
)
from tools.core.guided_action_runner import (
    build_action_context,
    execute_guided_action,
    find_guided_action_context,
    preview_guided_actions,
)
from tools.core.external_apps import (
    build_external_apps_health,
    build_external_apps_health_state,
    get_external_apps_status,
)
from tools.core.execution_adapter import (
    FINAL_CONFIRM_TOKEN,
    build_execution_adapter_result,
)
from tools.core.feed_readiness import build_feed_readiness_result
from tools.core.file_operation_adapter import (
    FINAL_MOVE_TOKEN,
    build_file_operation_adapter_result,
)
from tools.core.issue_classifier import ISSUE_CLASSIFIER_SCHEMA, build_issue_classifier_result
from tools.core.obsidian_exporter import (
    OBSIDIAN_EXPORT_SCHEMA,
    build_obsidian_export_result,
)
from tools.core.risk_classifier import PROTECTED, REVIEW_REQUIRED, SAFE_DELETE, classify_file_risk
from tools.core.scenario_tester import run_sandbox_scenarios
from tools.core.safe_delete_adapter import (
    FINAL_DELETE_TOKEN,
    SAFE_DELETE_ADAPTER_SCHEMA,
    build_safe_delete_adapter_result,
)
from tools.core.safe_executor import safe_delete
from tools.core.safety_utils import safe_move, save_manifest
from tools.core.tool_tester import TOOLS_TO_TEST
from tools.core.undo_manager import preview_manifest, restore_manifest
from tools.search import natural_command
from tools.ui.bot_panel import (
    BOT_PANEL_SCHEMA,
    build_bot_panel_snapshot,
    cleanup_demo_sandbox as cleanup_ui_demo_sandbox,
    create_demo_sandbox,
)
from tools.storage.wiztree_adapter import (
    get_top_wiztree_files,
    get_top_wiztree_folders,
    get_wiztree_status,
    parse_wiztree_csv,
)
from tools.storage.system_advisor import build_system_advisor_result


DANGEROUS_PATTERNS = {
    "send2trash": "Direct send2trash usage should stay in safe_executor.",
    "shutil.move": "Direct move should stay in safety_utils restore/move helpers.",
    "shutil.rmtree": "Recursive delete should only be used for verified test sandbox cleanup.",
    "os.remove": "Direct remove is not allowed.",
    "os.rmdir": "Direct rmdir is not allowed.",
    ".unlink(": "Direct unlink is not allowed.",
    ".rmdir(": "Direct rmdir is not allowed.",
}

STATIC_AUDIT_ALLOWLIST = {
    ("tools/core/safe_executor.py", "send2trash"),
    ("tools/core/safe_executor.py", ".unlink("),
    ("tools/core/safe_executor.py", ".rmdir("),
    ("tools/core/safety_utils.py", "shutil.move"),
    ("tools/core/behavior_tester.py", "shutil.rmtree"),
    ("tools/core/scenario_tester.py", "shutil.rmtree"),
    ("tools/ui/bot_panel.py", "shutil.rmtree"),
    ("tools/automation/startup_registration.py", ".unlink("),
}


def normalize_repo_path(path: Path) -> str:
    return path.relative_to(BASE_DIR).as_posix()


def run_command(command: list[str], timeout: int = 120) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_compileall() -> dict[str, Any]:
    result = run_command(
        [sys.executable, "-m", "compileall", "-q", "main.py", "config", "tools"]
    )
    assert_condition(result["returncode"] == 0, "compileall failed.")
    return result


def test_tool_import_matrix() -> dict[str, Any]:
    results = []

    for tool in TOOLS_TO_TEST:
        status = "pass"
        error = None
        try:
            module = importlib.import_module(tool["module"])
            if not hasattr(module, tool["function"]):
                raise AttributeError(f"Function not found: {tool['function']}")
        except Exception as exc:
            status = "fail"
            error = str(exc)

        results.append({
            **tool,
            "status": status,
            "error": error,
        })

    failed = [item for item in results if item["status"] != "pass"]
    assert_condition(not failed, "One or more tool imports failed.")

    return {
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": results,
    }


def test_main_menu_coverage() -> dict[str, Any]:
    main_text = (BASE_DIR / "main.py").read_text(encoding="utf-8")
    expected = [
        "Behavior Tester",
        "Tool Tester",
        "Config Manager",
        "Audit Center",
        "Undo Manager",
        "Full System Tester",
        "WizTree Adapter",
        "External Apps Manager",
        "Capability Registry",
        "Recommendation Center",
        "Guided Action Runner",
        "Feed Assistant Readiness",
        "Scenario Tester",
        "Action Policy Manager",
        "Candidate Review",
        "Dry-run Action Planner",
        "Pre-feed Bundle",
        "AI Bot Controller",
        "Execution Adapter",
        "File Operation Adapter",
        "Obsidian Exporter",
        "Auto Scan Session",
        "Issue Classifier",
        "Safe Delete Adapter",
        "Bot Panel UI",
        "Backup Adapter",
        "Startup Scan",
        "Startup Registration",
        "Startup Decision Window",
    ]
    missing = [label for label in expected if label not in main_text]

    assert_condition(not missing, f"Main menu missing entries: {missing}")
    return {
        "expected": expected,
        "missing": missing,
    }


def test_config_health() -> dict[str, Any]:
    validation = validate_user_settings()

    assert_condition(USER_SETTINGS_FILE.exists(), "user_settings.json is missing.")
    assert_condition(validation["status"] == "valid", "User settings validation failed.")

    with USER_SETTINGS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    required_top_level = {
        "paths",
        "thresholds",
        "safety",
        "browser_cache",
        "download_organizer",
        "download_watcher",
        "media_organizer",
        "wiztree",
        "external_apps",
    }
    missing = sorted(required_top_level - set(data))
    assert_condition(not missing, f"user_settings.json missing sections: {missing}")

    return {
        "validation": validation,
        "sections": sorted(data),
    }


def test_safety_static_audit() -> dict[str, Any]:
    findings = []

    source_roots = [
        BASE_DIR / "main.py",
        BASE_DIR / "config",
        BASE_DIR / "tools",
    ]
    paths = []
    for source_root in source_roots:
        if source_root.is_file():
            paths.append(source_root)
        elif source_root.exists():
            paths.extend(source_root.rglob("*.py"))

    for path in paths:
        repo_path = normalize_repo_path(path)
        if repo_path == "tools/core/full_system_tester.py":
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(errors="ignore").splitlines()

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            for pattern, reason in DANGEROUS_PATTERNS.items():
                if pattern not in line:
                    continue
                if (repo_path, pattern) in STATIC_AUDIT_ALLOWLIST:
                    continue
                findings.append({
                    "file": repo_path,
                    "line": line_no,
                    "pattern": pattern,
                    "reason": reason,
                    "code": stripped,
                })

    assert_condition(not findings, "Static safety audit found direct risky operations.")
    return {
        "scanned_roots": [normalize_repo_path(path) for path in source_roots],
        "checked_patterns": sorted(DANGEROUS_PATTERNS),
        "findings": findings,
    }


def test_risk_classifier_guardrails() -> dict[str, Any]:
    protected = classify_file_risk(BASE_DIR / "README.md")
    missing_delete = safe_delete(BASE_DIR / "missing_full_system_test.tmp")
    appdata_temp = classify_file_risk(Path(r"C:\Users\Demo\AppData\Local\Temp\cache.tmp"))
    appdata_data = classify_file_risk(Path(r"C:\Users\Demo\AppData\Local\Vendor\data.db"))
    dev_artifact = classify_file_risk(Path(r"D:\Projects\demo\dist\bundle.old"))
    browser_cache = classify_file_risk(
        Path(r"C:\Users\Demo\AppData\Local\Google\Chrome\User Data\Default\Cache\entry")
    )
    windows_temp = classify_file_risk(Path(r"C:\Windows\Temp\cache.tmp"))

    assert_condition(protected["risk"] == PROTECTED, "Project root file should be protected.")
    assert_condition(missing_delete["status"] == "missing", "safe_delete should handle missing files.")
    assert_condition(appdata_temp["risk"] == SAFE_DELETE, "AppData Local Temp files should be safe_delete.")
    assert_condition(appdata_data["risk"] == REVIEW_REQUIRED, "Generic AppData files should require review.")
    assert_condition(dev_artifact["risk"] == REVIEW_REQUIRED, "Dev artifacts should require review.")
    assert_condition(browser_cache["risk"] == SAFE_DELETE, "Known browser cache should be safe_delete.")
    assert_condition(windows_temp["risk"] == PROTECTED, "Windows temp should stay protected.")

    return {
        "protected_readme": protected,
        "missing_delete": missing_delete,
        "appdata_temp": appdata_temp,
        "appdata_data": appdata_data,
        "dev_artifact": dev_artifact,
        "browser_cache": browser_cache,
        "windows_temp": windows_temp,
    }


def test_report_manager_and_audit_index() -> dict[str, Any]:
    report_a = create_report("full_system_report_collision", "success", {}, {"case": "a"})
    report_b = create_report("full_system_report_collision", "success", {}, {"case": "b"})
    recent = read_recent_report_index(limit=20)
    validation = validate_report_file(report_b)

    assert_condition(report_a != report_b, "Report manager should avoid timestamp collisions.")
    assert_condition(report_a.exists() and report_b.exists(), "Collision reports should exist.")
    assert_condition(
        any(item.get("report_path") == str(report_b) for item in recent),
        "Report index should include the latest created report.",
    )
    assert_condition(validation["status"] == "valid", "Created report should match schema.")

    return {
        "report_a": str(report_a),
        "report_b": str(report_b),
        "recent_index_count": len(recent),
        "schema_validation": validation,
    }


def test_report_schema_validation() -> dict[str, Any]:
    report = create_report(
        tool_name="full_system_schema_test",
        status="success",
        input_data={
            "expected_schema_version": REPORT_SCHEMA_VERSION,
        },
        results={
            "total": 1,
            "passed": 1,
            "failed": 0,
        },
        recommendations=[
            "Report schema validation is active.",
        ],
        action="validate_schema",
        risk_level="safe",
        summary={
            "total": 1,
            "passed": 1,
            "failed": 0,
            "undo_available": False,
        },
        undo_available=False,
        tags=["schema", "full_system"],
    )
    validation = validate_report_file(report)

    assert_condition(validation["status"] == "valid", "Schema test report should be valid.")

    return {
        "report": str(report),
        "schema_version": REPORT_SCHEMA_VERSION,
        "validation": validation,
    }


def test_audit_center_health() -> dict[str, Any]:
    snapshot = get_audit_snapshot(limit=20)
    assert_condition(isinstance(snapshot["logs"], list), "Audit logs should be a list.")
    assert_condition(isinstance(snapshot["reports"], list), "Audit reports should be a list.")
    return {
        "log_count": snapshot["log_count"],
        "report_count": snapshot["report_count"],
    }


def test_undo_manager_roundtrip() -> dict[str, Any]:
    sandbox = make_sandbox()

    try:
        root = sandbox / "full_undo"
        source = root / "original" / "restore_me.txt"
        target = root / "moved" / "restore_me.txt"

        write_text(source, "full undo")
        move_record = safe_move(source, target)
        manifest = save_manifest("full_system_undo_test", [move_record])

        preview = preview_manifest(manifest)
        assert_condition(preview["restorable_count"] == 1, "Undo preview should be restorable.")

        result = restore_manifest(manifest)
        assert_condition(result["status"] == "success", "Undo restore should succeed.")
        assert_condition(result["restored_count"] == 1, "Undo restore should restore one file.")
        assert_condition(source.exists(), "Original path should exist after undo.")
        assert_condition(not Path(move_record["new_path"]).exists(), "Moved path should be gone after undo.")

        return {
            "manifest": str(manifest),
            "restored_count": result["restored_count"],
            "report": result["report"],
        }

    finally:
        cleanup_sandbox(sandbox)


def test_behavior_suite_subprocess() -> dict[str, Any]:
    result = run_command([sys.executable, "-m", "tools.core.behavior_tester"], timeout=180)
    assert_condition(result["returncode"] == 0, "Behavior tester process failed.")
    assert_condition("Failed: 0" in result["stdout"], "Behavior tester reported failures.")
    return result


def test_wiztree_adapter_sample_csv() -> dict[str, Any]:
    sandbox = make_sandbox()

    try:
        csv_path = sandbox / "wiztree_sample.csv"
        sample_csv = (
            "File Name,Size,Allocated,Modified,Attributes,Files,Folders\n"
            r"D:\Data\,3000,4096,2026-05-30,D,2,1" "\n"
            r"D:\Data\a.bin,2097152,2097152,2026-05-30,A,0,0" "\n"
            r"D:\Data\b.txt,10,10,2026-05-30,A,0,0" "\n"
        )
        write_text(csv_path, sample_csv)

        records = parse_wiztree_csv(csv_path)
        top_folders = get_top_wiztree_folders(records, limit=1)
        large_files = get_top_wiztree_files(records, min_size_mb=1, limit=1)

        assert_condition(len(records) == 3, "WizTree CSV parser should read all rows.")
        assert_condition(top_folders[0]["path"] == r"D:\Data", "Top folder path should be normalized.")
        assert_condition(large_files[0]["path"] == r"D:\Data\a.bin", "Large file sorting should use size.")

        return {
            "records": records,
            "top_folders": top_folders,
            "large_files": large_files,
            "wiztree_status": get_wiztree_status(),
        }

    finally:
        cleanup_sandbox(sandbox)


def test_external_apps_registry() -> dict[str, Any]:
    status = get_external_apps_status(include_versions=False)
    health = build_external_apps_health(include_versions=False)
    missing = [
        item for item in status["apps"]
        if not item["available"]
    ]

    assert_condition(status["enabled"], "External apps registry should be enabled.")
    assert_condition(not missing, f"External apps missing configured paths: {missing}")
    assert_condition(
        health["schema"] == "external_apps_health_v2",
        "External apps health report should expose v2 schema.",
    )
    assert_condition(
        "system_advisor" in {
            tool["id"]
            for tool in next(item for item in health["apps"] if item["name"] == "wiztree")["dependent_tools"]
        },
        "External apps health should map WizTree to System Advisor.",
    )
    assert_condition(
        health["summary"]["impacted_tool_count"] == 0,
        "No tool should be impacted when all configured external apps are available.",
    )

    no_drift_health = build_external_apps_health(
        include_versions=False,
        previous_state=build_external_apps_health_state(health),
    )
    assert_condition(
        no_drift_health["summary"]["drift_event_count"] == 0,
        "External apps drift detector should stay quiet for identical baseline.",
    )

    drift_state = build_external_apps_health_state(health)
    drift_state["apps"]["everything_cli"]["path"] = r"D:\old_external_path\es.exe"
    drift_health = build_external_apps_health(
        include_versions=False,
        previous_state=drift_state,
    )
    drift_ids = {item["id"] for item in drift_health["drift_events"]}
    assert_condition(
        "external-app-everything_cli-path_changed" in drift_ids,
        "External apps health should detect path drift.",
    )

    return {
        "status": status,
        "health_summary": health["summary"],
        "drift_event_ids": sorted(drift_ids),
    }


def test_capability_registry() -> dict[str, Any]:
    capabilities = get_capabilities()
    validation = validate_capability_registry(expected_tools=TOOLS_TO_TEST)

    assert_condition(validation["status"] == "valid", f"Capability registry invalid: {validation['issues']}")
    assert_condition(
        validation["capability_count"] >= len(TOOLS_TO_TEST),
        "Capability registry should cover every tool tester entry.",
    )

    return {
        "validation": validation,
        "capability_count": len(capabilities),
    }


def test_system_advisor_v2_contract() -> dict[str, Any]:
    result = build_system_advisor_result(
        root_drive="D:\\",
        storage_provider="python",
        wiztree_status="skipped",
        storage_scan_report=None,
        top_folders=[
            {
                "path": "D:\\Downloads",
                "size": 5 * 1024 * 1024 * 1024,
                "source": "contract_test",
            }
        ],
        large_files=[
            {
                "path": "D:\\Downloads\\archive.zip",
                "size": 2 * 1024 * 1024 * 1024,
                "extension": ".zip",
            }
        ],
        processes=[
            {
                "pid": 1,
                "name": "browser.exe",
                "cpu_percent": 1.0,
                "memory_bytes": 700 * 1024 * 1024,
                "memory_percent": 7.0,
                "system_memory_percent": 86.0,
            }
        ],
        disk_snapshot={
            "disks": [
                {
                    "device": "D:",
                    "mountpoint": "D:\\",
                    "percent": 91.0,
                    "free": 9 * 1024 * 1024 * 1024,
                    "status": "critical",
                }
            ],
            "smart_health": {
                "devices": [],
            },
        },
        external_apps={
            "enabled": True,
            "total": 1,
            "available": 1,
            "missing": 0,
            "apps": [
                {"name": "everything_cli", "available": True},
            ],
        },
        audit_snapshot={
            "log_count": 0,
            "report_count": 0,
            "reports": [],
        },
    )

    recommendations = result["recommendations"]
    summary = result["recommendation_summary"]
    recommendation_ids = {item["id"] for item in recommendations}

    assert_condition("disk-critical-D:\\" in recommendation_ids, "Advisor should flag critical disk usage.")
    assert_condition("ram-critical" in recommendation_ids, "Advisor should flag critical RAM usage.")
    assert_condition("large-archive-files" in recommendation_ids, "Advisor should flag large archive files.")
    assert_condition(summary["total"] == len(recommendations), "Advisor summary total should match recommendations.")
    assert_condition(result["snapshot"]["storage"]["provider"] == "python", "Advisor snapshot should keep storage provider.")
    assert_condition(
        all(isinstance(item.get("explanation"), str) and item["explanation"] for item in recommendations),
        "Advisor recommendations should expose Vietnamese explanation text.",
    )
    assert_condition(
        result["disk_full_reason"]["read_only"] is True
        and isinstance(result["disk_full_reason"].get("reason_text"), str)
        and result["disk_full_reason"]["contributors"],
        "Advisor should expose read-only disk_full_reason summary.",
    )

    return {
        "recommendation_ids": sorted(recommendation_ids),
        "summary": summary,
        "disk_full_reason": result["disk_full_reason"],
    }


def test_recommendation_center_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    state_file = sandbox / "recommendation_queue.jsonl"

    try:
        create_report(
            tool_name="system_advisor",
            action="analyze_system_v2",
            status="success",
            risk_level="safe",
            input_data={
                "contract_test": True,
            },
            results={
                "recommendations": [
                    {
                        "id": "contract-critical",
                        "severity": "critical",
                        "title": "Contract critical recommendation",
                        "detail": "Recommendation Center should collect this structured item.",
                        "source": "contract_test",
                        "suggested_tool_id": "large_file_finder",
                        "suggestion_only": True,
                    }
                ],
            },
            recommendations=[
                "[CRITICAL] Contract critical recommendation.",
            ],
            summary={
                "total": 1,
                "critical_count": 1,
                "warning_count": 0,
                "info_count": 0,
                "undo_available": False,
            },
            undo_available=False,
            tags=["system_advisor", "read_only", "v2", "contract_test"],
        )
        create_report(
            tool_name="contract_warning_tool",
            action="contract_warning",
            status="warning",
            risk_level="safe",
            input_data={},
            results={},
            recommendations=[],
            summary={
                "undo_available": False,
            },
            undo_available=False,
            tags=["contract_test"],
        )

        sync_result = sync_recommendation_queue(
            report_limit=20,
            state_file=state_file,
            include_test_reports=True,
            states=None,
        )
        queue = collect_recommendation_queue(
            report_limit=20,
            state_file=state_file,
            include_test_reports=True,
        )
        default_queue = collect_recommendation_queue(
            report_limit=20,
            state_file=state_file,
        )
        summary = summarize_recommendation_queue(queue)
        recommendation_ids = {item["id"] for item in queue}

        assert_condition("contract-critical" in recommendation_ids, "Recommendation Center should collect Advisor items.")
        assert_condition(
            "contract-critical" not in {item["id"] for item in default_queue},
            "Default Recommendation Center queue should exclude test-tagged reports.",
        )
        assert_condition(
            any(item.get("report_tool") == "contract_warning_tool" for item in queue),
            "Recommendation Center should convert warning/error reports into audit recommendations.",
        )
        assert_condition(
            all(item.get("suggestion_only") is True for item in queue),
            "Recommendation Center must remain suggestion-only.",
        )
        assert_condition(summary["total"] == len(queue), "Queue summary total should match queue length.")
        assert_condition(state_file.exists(), "Recommendation workflow state file should be created during sync.")

        critical = next(item for item in queue if item["id"] == "contract-critical")
        update_recommendation_state(
            critical["fingerprint"],
            "handled",
            note="full system contract",
            state_file=state_file,
        )
        handled_queue = collect_recommendation_queue(
            report_limit=20,
            state_file=state_file,
            include_test_reports=True,
            states={"handled"},
        )
        assert_condition(
            any(item["id"] == "contract-critical" for item in handled_queue),
            "Recommendation workflow should persist handled state.",
        )

        return {
            "summary": summary,
            "recommendation_ids": sorted(recommendation_ids),
            "state_file": str(state_file),
            "created_count": sync_result["created_count"],
        }

    finally:
        cleanup_sandbox(sandbox)


def test_guided_action_runner_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    state_file = sandbox / "guided_action_queue.jsonl"
    recommendation_id = f"full-guided-action-{sandbox.name}"

    try:
        create_report(
            tool_name="system_advisor",
            action="guided_action_contract",
            status="success",
            risk_level="safe",
            input_data={
                "sandbox": str(sandbox),
            },
            results={
                "recommendations": [
                    {
                        "id": recommendation_id,
                        "severity": "warning",
                        "title": "Full guided action contract",
                        "detail": f"Guided runner dry-run contract {sandbox.name}.",
                        "source": "full_system_test",
                        "suggested_tool_id": "download_organizer",
                        "suggestion_only": True,
                    }
                ],
            },
            recommendations=[],
            summary={
                "total": 1,
                "warning_count": 1,
                "undo_available": False,
            },
            undo_available=False,
            tags=["guided_action", "full_system"],
        )

        preview = preview_guided_actions(
            report_limit=30,
            state_file=state_file,
            include_test_reports=True,
        )
        context = find_guided_action_context(
            preview["contexts"],
            recommendation_id=recommendation_id,
        )
        no_tool_context = build_action_context({
            "id": "no-tool",
            "title": "No tool",
            "detail": "No suggested tool should be blocked.",
            "severity": "info",
        })
        manual_policy_context = build_action_context({
            "id": "large-archive-files",
            "title": "Large archive files",
            "detail": "Policy gate should require strong confirmation.",
            "severity": "warning",
            "suggested_tool_id": "large_file_finder",
        })

        assert_condition(context is not None, "Guided Action Runner should collect seeded recommendation.")
        assert_condition(context["status"] == "ready", "Guided action context should be ready.")
        assert_condition(
            context["capability"]["id"] == "download_organizer",
            "Guided Action Runner should resolve target capability.",
        )
        assert_condition(
            context["target_requires_confirmation"] is True,
            "Guided Action Runner should preserve target confirmation metadata.",
        )
        assert_condition(
            no_tool_context["status"] == "no_suggested_tool",
            "Guided Action Runner should block recommendations without suggested tool.",
        )
        assert_condition(
            manual_policy_context["status"] == "ready",
            "Manual-only policy should still allow opening the target with stronger confirmation.",
        )
        assert_condition(
            manual_policy_context["policy_gate"]["decision"] == "manual_only",
            "Guided Action Runner should attach action policy gate metadata.",
        )
        assert_condition(
            manual_policy_context["policy_gate"]["requires_strong_confirmation"] is True,
            "Manual-only policy should require strong confirmation.",
        )
        assert_condition(
            manual_policy_context["policy_gate"]["confirmation_token"] == "OPEN_MANUAL",
            "Manual-only policy should require OPEN_MANUAL token.",
        )

        dry_run = execute_guided_action(context, dry_run=True)
        assert_condition(dry_run["status"] == "dry_run", "Guided dry-run should not execute target tool.")
        assert_condition(dry_run["executed"] is False, "Guided dry-run must stay non-mutating.")
        assert_condition(Path(dry_run["report"]).exists(), "Guided dry-run should create a report.")

        return {
            "preview_ready_count": preview["ready_count"],
            "target_tool": context["capability"]["id"],
            "dry_run_report": dry_run["report"],
            "no_tool_status": no_tool_context["status"],
            "manual_policy_gate": manual_policy_context["policy_gate"],
        }

    finally:
        cleanup_sandbox(sandbox)


def test_natural_command_v3_queue_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    state_file = sandbox / "natural_command_v3_queue.jsonl"
    recommendation_id = f"full-natural-command-v3-{sandbox.name}"

    try:
        preview_decision = natural_command.resolve_command("xem goi y")
        open_decision = natural_command.resolve_command("lam goi y so 1")
        handled_decision = natural_command.resolve_command("danh dau muc 1 da xu ly")
        question_decision = natural_command.resolve_command("tai sao o D day")

        assert_condition(
            preview_decision["type"] == "recommendation_queue_preview",
            "Natural Command v3 should resolve queue preview.",
        )
        assert_condition(
            open_decision["type"] == "recommendation_open" and open_decision["index"] == 1,
            "Natural Command v3 should resolve open by index.",
        )
        assert_condition(
            handled_decision["type"] == "recommendation_state_update"
            and handled_decision["state"] == "handled",
            "Natural Command v3 should resolve handled state update.",
        )
        assert_condition(
            question_decision["type"] == "answer_question"
            and question_decision["intent"] == "disk_full_reason",
            "Natural Command should route disk-full questions to its read-only answer API.",
        )

        question_scan = build_auto_scan_session_result(
            root_drive=str(sandbox),
            top_folders=[{
                "path": str(sandbox / "Downloads"),
                "size": 4 * 1024 * 1024,
                "source": "full_system_test",
            }],
            large_files=[{
                "path": str(sandbox / "Downloads" / "archive.zip"),
                "size": 3 * 1024 * 1024,
                "source": "full_system_test",
            }],
        )
        question_answer = natural_command.answer_user_question(
            "tai sao o D day",
            auto_scan_result=question_scan,
        )
        assert_condition(
            question_answer["schema"] == "natural_command_answer_v1"
            and question_answer["status"] == "ready"
            and question_answer["safety_contract"]["read_only"] is True
            and question_answer["safety_contract"]["delete_enabled"] is False
            and question_answer["safety_contract"]["move_enabled"] is False,
            "Natural Command answer API should remain structured and read-only.",
        )

        create_report(
            tool_name="system_advisor",
            action="natural_command_v3_contract",
            status="success",
            risk_level="safe",
            input_data={
                "sandbox": str(sandbox),
            },
            results={
                "recommendations": [
                    {
                        "id": recommendation_id,
                        "severity": "critical",
                        "title": "Full natural command v3 contract",
                        "detail": f"Natural Command queue contract {sandbox.name}.",
                        "source": "full_system_test",
                        "suggested_tool_id": "audit_center",
                        "suggestion_only": True,
                    }
                ],
            },
            recommendations=[],
            summary={
                "total": 1,
                "critical_count": 1,
                "undo_available": False,
            },
            undo_available=False,
            tags=["natural_command_v3", "full_system"],
        )

        preview = preview_guided_actions(
            report_limit=30,
            state_file=state_file,
            include_test_reports=True,
        )
        context = find_guided_action_context(
            preview["contexts"],
            recommendation_id=recommendation_id,
        )
        assert_condition(context is not None, "Natural Command v3 queue test should collect seeded item.")

        index = preview["contexts"].index(context) + 1
        dry_run = natural_command.run_recommendation_open_command(
            index,
            report_limit=30,
            state_file=state_file,
            include_test_reports=True,
            dry_run=True,
            require_confirmation=False,
        )
        assert_condition(dry_run["status"] == "dry_run", "Natural Command v3 dry-run should not execute target.")

        handled = natural_command.run_recommendation_state_command(
            index,
            "handled",
            report_limit=30,
            state_file=state_file,
            include_test_reports=True,
        )
        handled_queue = collect_recommendation_queue(
            report_limit=30,
            state_file=state_file,
            include_test_reports=True,
            states={"handled"},
        )
        assert_condition(handled["status"] == "success", "Natural Command v3 should update state.")
        assert_condition(
            any(item["id"] == recommendation_id for item in handled_queue),
            "Natural Command v3 handled state should persist.",
        )

        return {
            "recommendation_id": recommendation_id,
            "index": index,
            "dry_run_report": dry_run["report"],
            "handled_state": handled["state"],
            "answer_schema": question_answer["schema"],
        }

    finally:
        cleanup_sandbox(sandbox)


def test_action_policy_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    policy_file = sandbox / "action_policy.jsonl"

    try:
        seed = seed_default_action_policies(policy_file=policy_file)
        validation = validate_action_policies(policy_file=policy_file)
        health = build_action_policy_health(policy_file=policy_file)

        riot_matches = get_matching_policies_for_path(
            r"D:\Downloads\Riot Games\League of Legends\Game\data.wad",
            policy_file=policy_file,
        )
        steam_matches = get_matching_policies_for_path(
            r"D:\Steam\steamapps\workshop\content\431960\video.mp4",
            policy_file=policy_file,
        )
        downloads_app_matches = get_matching_policies_for_path(
            r"D:\Downloads\app\Premiere_Setup.rar",
            policy_file=policy_file,
        )
        backup_matches = get_matching_policies_for_path(
            r"D:\backup\backup\export\clip.mp4",
            policy_file=policy_file,
        )
        archive_recommendation_policy = get_policy_for_recommendation(
            {"id": "large-archive-files"},
            policy_file=policy_file,
        )
        video_recommendation_policy = get_policy_for_recommendation(
            {"id": "large-video-files"},
            policy_file=policy_file,
        )

        assert_condition(seed["created_count"] >= 6, "Action Policy seed should create baseline policies.")
        assert_condition(validation["status"] == "valid", f"Action Policy validation failed: {validation['issues']}")
        assert_condition(riot_matches[0]["decision"] == "ignore_forever", "Riot Games should be ignore_forever.")
        assert_condition(steam_matches[0]["decision"] == "ignore_forever", "Steam Workshop should be ignore_forever.")
        assert_condition(downloads_app_matches[0]["decision"] == "manual_only", "Downloads app should be manual_only.")
        assert_condition(backup_matches[0]["decision"] == "needs_backup", "Backup path should need backup policy.")
        assert_condition(
            archive_recommendation_policy["decision"] == "manual_only",
            "Large archive recommendation should be manual_only.",
        )
        assert_condition(
            video_recommendation_policy["decision"] == "move_later",
            "Large video recommendation should be move_later.",
        )
        assert_condition(
            health["validation"]["status"] == "valid",
            "Action Policy health should include valid validation.",
        )

        return {
            "seed": seed,
            "validation": validation,
            "summary": health["summary"],
            "riot_policy": riot_matches[0],
            "steam_policy": steam_matches[0],
            "downloads_app_policy": downloads_app_matches[0],
            "backup_policy": backup_matches[0],
            "archive_recommendation_policy": archive_recommendation_policy,
            "video_recommendation_policy": video_recommendation_policy,
        }

    finally:
        cleanup_sandbox(sandbox)


def write_fake_step3_report(path: Path) -> None:
    data = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "step3_deferred_storage_review",
        "action": "contract_fixture",
        "risk_level": "safe",
        "status": "success",
        "summary": {
            "archive_count": 1,
            "video_count": 1,
            "undo_available": False,
        },
        "input": {},
        "results": {
            "archive_review": {
                "items": [
                    {
                        "path": r"D:\Downloads\app\Premiere_Setup.rar",
                        "name": "Premiere_Setup.rar",
                        "extension": ".rar",
                        "size": 1024,
                        "size_text": "1.00 KB",
                        "exists": True,
                        "risk": "review_required",
                        "risk_category": "review_unknown",
                        "context": "downloads_app_installer_bundle",
                        "decision": "manual_review_only",
                    },
                ],
            },
            "video_review": {
                "items": [
                    {
                        "path": r"D:\Steam\steamapps\workshop\content\431960\clip.mp4",
                        "name": "clip.mp4",
                        "extension": ".mp4",
                        "size": 2048,
                        "size_text": "2.00 KB",
                        "exists": True,
                        "risk": "review_required",
                        "risk_category": "review_unknown",
                        "context": "app_managed_steam_workshop",
                        "decision": "manual_review_only",
                    },
                ],
            },
        },
        "manifest": None,
        "undo_available": False,
        "recommendations": [],
        "tags": ["contract_test"],
    }
    write_text(path, json.dumps(data, ensure_ascii=False))


def test_candidate_review_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        source_report = sandbox / "step3_contract_report.json"
        write_fake_step3_report(source_report)
        review = build_candidate_review(source_report_path=source_report)
        actions = {item["candidate_action"] for item in review["items"]}

        assert_condition(review["status"] == "success", "Candidate Review should load fake Step 3 report.")
        assert_condition(review["summary"]["total"] == 2, "Candidate Review should include archive and video item.")
        assert_condition(review["summary"]["covered_by_policy_count"] == 2, "Candidate Review should cover both items by policy.")
        assert_condition("manual_review" in actions, "Downloads app archive should need manual review.")
        assert_condition("keep_ignore" in actions, "Steam Workshop media should be blocked/ignored by policy.")
        assert_condition(
            review["summary"]["auto_execute_count"] == 0,
            "Candidate Review must not mark items auto executable.",
        )

        return {
            "summary": review["summary"],
            "actions": sorted(actions),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_action_planner_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        source_report = sandbox / "step3_contract_report.json"
        write_fake_step3_report(source_report)
        plan = build_action_plan(source_report_path=source_report)
        actions = {item["plan_action"] for item in plan["items"]}

        assert_condition(plan["status"] == "success", "Action Planner should build from fake Step 3 report.")
        assert_condition(plan["summary"]["total"] == 2, "Action Planner should include two items.")
        assert_condition(plan["summary"]["can_execute_now_count"] == 0, "Action Planner dry-run must not execute now.")
        assert_condition(
            plan["safety_contract"]["dry_run_only"] is True,
            "Action Planner should expose dry-run safety contract.",
        )
        assert_condition(
            {"manual_review", "keep"}.issubset(actions),
            "Action Planner should include manual review and keep actions.",
        )

        return {
            "summary": plan["summary"],
            "actions": sorted(actions),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_pre_feed_bundle_contract() -> dict[str, Any]:
    bundle = build_pre_feed_bundle(include_doc_content=False)

    assert_condition(bundle["schema"] == "pre_feed_bundle_v1", "Pre-feed Bundle should expose v1 schema.")
    assert_condition(bundle["safety_contract"]["read_only"] is True, "Pre-feed Bundle should be read-only.")
    assert_condition(bundle["safety_contract"]["no_user_file_contents"] is True, "Pre-feed Bundle should avoid user file contents.")
    assert_condition(
        all("content" not in item for item in bundle["docs"]),
        "Pre-feed Bundle contract test should omit doc content when requested.",
    )
    assert_condition(
        bundle["capability_registry"]["validation"]["status"] == "valid",
        "Pre-feed Bundle should include valid Capability Registry snapshot.",
    )
    assert_condition(
        bundle["action_plan"]["summary"]["can_execute_now_count"] == 0,
        "Pre-feed Bundle action plan should not enable execution.",
    )

    return {
        "doc_count": len(bundle["docs"]),
        "queue_summary": bundle["recommendation_queue"]["summary"],
        "policy_count": bundle["action_policy"]["summary"]["total"],
        "readiness": bundle["feed_readiness"]["summary"],
    }


def test_bot_controller_contract() -> dict[str, Any]:
    result = build_bot_controller_result(include_items=True)
    summary = result["summary"]
    decision_screen = result["decision_screen"]
    selection_ui = result["selection_ui"]

    assert_condition(result["schema"] == "bot_controller_v2", "Bot Controller should expose v2 schema.")
    assert_condition(
        result["safety_contract"]["executes_file_operations"] is False,
        "Bot Controller v2 must not execute file operations.",
    )
    assert_condition(
        {"ok", "select", "move_later", "delete_candidate", "cancel", "details"}.issubset(decision_screen),
        "Bot Controller should expose simple user decisions.",
    )
    assert_condition(
        result["action_plan"]["safety_contract"]["dry_run_only"] is True,
        "Bot Controller should use dry-run action plan.",
    )
    assert_condition(
        summary["candidate_count"] == result["candidate_review"]["summary"]["total"],
        "Bot Controller summary should match candidate review.",
    )
    assert_condition(
        selection_ui["schema"] == "bot_selection_ui_v2",
        "Bot Controller should expose selection UI v2.",
    )
    assert_condition(
        selection_ui["summary"]["needs_selection_count"] == summary["needs_selection_count"],
        "Selection UI should match needs-selection summary.",
    )
    assert_condition(
        selection_ui["decision_contract"]["executes_file_operations"] is False,
        "Selection UI should be decision-report-only.",
    )
    ok_result = execute_bot_decision("ok", bot_result=result)
    assert_condition(
        ok_result["executed"] is False,
        "Bot Controller OK decision should not execute in v2.",
    )
    select_result = execute_bot_decision("select", bot_result=result)
    assert_condition(
        select_result["selection_ui"]["schema"] == "bot_selection_ui_v2",
        "Select decision should return selection UI.",
    )
    move_later_result = execute_bot_decision("move_later", bot_result=result)
    assert_condition(
        move_later_result["executed"] is False,
        "Move-later bot decision should require selection and destination first.",
    )
    assert_condition(
        move_later_result["selection_ui"]["schema"] == "bot_selection_ui_v2",
        "Move-later decision should return selection UI.",
    )
    delete_result = execute_bot_decision("delete_candidate", bot_result=result)
    assert_condition(
        delete_result["executed"] is False,
        "Safe-delete bot decision should require selection and token first.",
    )
    assert_condition(
        delete_result["selection_ui"]["schema"] == "bot_selection_ui_v2",
        "Safe-delete decision should return selection UI.",
    )

    selection_items = selection_ui["groups"]["needs_selection"]
    if selection_items:
        first_item = selection_items[0]
        decision_report = build_selection_decision(
            {first_item["selection_id"]: "keep"},
            session=selection_ui,
        )
        assert_condition(
            decision_report["schema"] == "bot_selection_decision_v2",
            "Selection decision should expose v2 schema.",
        )
        assert_condition(
            decision_report["summary"]["selected_count"] == 1,
            "Selection decision should record selected items.",
        )
        assert_condition(
            decision_report["safety_contract"]["executes_file_operations"] is False,
            "Selection decision must not execute file operations.",
        )

    locked_items = selection_ui["groups"]["do_not_touch"]
    if locked_items:
        locked_item = locked_items[0]
        blocked_report = build_selection_decision(
            {locked_item["selection_id"]: "delete_candidate"},
            session=selection_ui,
        )
        assert_condition(
            blocked_report["summary"]["blocked_count"] == 1,
            "Selection decision should block locked do-not-touch items.",
        )

    return {
        "summary": summary,
        "decision_screen": decision_screen,
        "selection_summary": selection_ui["summary"],
        "ok_result": ok_result,
        "move_later_result_status": move_later_result["status"],
        "delete_result_status": delete_result["status"],
    }


def test_auto_scan_and_issue_classifier_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        safe_file = sandbox / "Downloads" / "old_cache.tmp"
        video_file = sandbox / "Media" / "selected_video.mp4"
        project_file = sandbox / "Work" / "edit_project.prproj"
        write_text(safe_file, "safe delete contract")
        write_text(video_file, "video contract")
        write_text(project_file, "project contract")

        top_folders = [
            {
                "path": str(sandbox / "Downloads"),
                "size": 1024,
                "source": "contract_test",
            }
        ]
        large_files = [
            {
                "path": str(safe_file),
                "size": safe_file.stat().st_size,
                "source": "contract_test",
            },
            {
                "path": str(video_file),
                "size": video_file.stat().st_size,
                "source": "contract_test",
            },
            {
                "path": str(project_file),
                "size": project_file.stat().st_size,
                "source": "contract_test",
            },
        ]
        scan = build_auto_scan_session_result(
            root_drive=sandbox,
            top_folders=top_folders,
            large_files=large_files,
        )
        assert_condition(scan["schema"] == AUTO_SCAN_SESSION_SCHEMA, "Auto Scan Session should expose v1 schema.")
        assert_condition(
            scan["safety_contract"]["executes_file_operations"] is False,
            "Auto Scan Session must be read-only.",
        )
        assert_condition(
            scan["summary"]["large_file_count"] == 3,
            "Auto Scan Session should preserve supplied large-file snapshot.",
        )

        classifier = build_issue_classifier_result(
            auto_scan_result=scan,
            include_items=True,
        )
        summary = classifier["summary"]
        assert_condition(
            classifier["schema"] == ISSUE_CLASSIFIER_SCHEMA,
            "Issue Classifier should expose v1 schema.",
        )
        assert_condition(classifier["status"] == "ready", "Issue Classifier should be ready for valid auto scan.")
        assert_condition(
            classifier["safety_contract"]["executes_file_operations"] is False,
            "Issue Classifier must not execute file operations.",
        )
        assert_condition(
            summary["delete_candidate_count"] >= 1,
            "Issue Classifier should detect safe delete candidates.",
        )
        assert_condition(
            summary["move_later_count"] >= 1,
            "Issue Classifier should detect move_later candidates.",
        )
        assert_condition(
            summary["needs_backup_count"] >= 1,
            "Issue Classifier should detect backup-first candidates.",
        )

        return {
            "scan_summary": scan["summary"],
            "classifier_summary": summary,
            "group_counts": {
                key: len(value)
                for key, value in classifier["action_groups"].items()
            },
        }
    finally:
        cleanup_sandbox(sandbox)


def write_fake_selection_decision_report(path: Path, target_file: Path) -> None:
    data = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "bot_controller",
        "action": "export_selection_decision",
        "risk_level": "safe",
        "status": "success",
        "summary": {
            "selected_count": 2,
            "blocked_count": 0,
            "invalid_count": 0,
            "undo_available": False,
        },
        "input": {},
        "results": {
            "schema": "bot_selection_decision_v2",
            "status": "ready",
            "summary": {
                "input_decision_count": 2,
                "selected_count": 2,
                "skipped_count": 0,
                "blocked_count": 0,
                "invalid_count": 0,
                "unselected_count": 0,
                "by_decision": {
                    "keep": 1,
                    "delete_candidate": 1,
                },
                "execution_enabled": False,
                "undo_available": False,
            },
            "selected": [
                {
                    "selection_id": "M001",
                    "path": str(target_file),
                    "name": target_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "manual_only",
                    "plan_action": "manual_review",
                    "decision": "keep",
                    "execution_enabled": False,
                },
                {
                    "selection_id": "M002",
                    "path": str(target_file),
                    "name": target_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "manual_only",
                    "plan_action": "manual_review",
                    "decision": "delete_candidate",
                    "execution_enabled": False,
                },
            ],
            "skipped": [],
            "blocked": [],
            "invalid": [],
            "safety_contract": {
                "decision_report_only": True,
                "executes_file_operations": False,
                "requires_execution_adapter": True,
                "delete_candidate_is_not_delete": True,
            },
        },
        "manifest": None,
        "undo_available": False,
        "recommendations": [],
        "tags": ["contract_test"],
    }
    write_text(path, json.dumps(data, ensure_ascii=False))


def write_fake_move_selection_decision_report(path: Path, target_file: Path) -> None:
    data = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "bot_controller",
        "action": "export_selection_decision",
        "risk_level": "safe",
        "status": "success",
        "summary": {
            "selected_count": 2,
            "blocked_count": 0,
            "invalid_count": 0,
            "undo_available": False,
        },
        "input": {},
        "results": {
            "schema": "bot_selection_decision_v2",
            "status": "ready",
            "summary": {
                "input_decision_count": 2,
                "selected_count": 2,
                "skipped_count": 0,
                "blocked_count": 0,
                "invalid_count": 0,
                "unselected_count": 0,
                "by_decision": {
                    "move_later": 1,
                    "keep": 1,
                },
                "execution_enabled": False,
                "undo_available": False,
            },
            "selected": [
                {
                    "selection_id": "M001",
                    "path": str(target_file),
                    "name": target_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "move_later",
                    "plan_action": "move_later",
                    "decision": "move_later",
                    "execution_enabled": False,
                },
                {
                    "selection_id": "M002",
                    "path": str(target_file),
                    "name": target_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "manual_only",
                    "plan_action": "manual_review",
                    "decision": "keep",
                    "execution_enabled": False,
                },
            ],
            "skipped": [],
            "blocked": [],
            "invalid": [],
            "safety_contract": {
                "decision_report_only": True,
                "executes_file_operations": False,
                "requires_execution_adapter": True,
                "requires_manifest_for_move": True,
                "delete_candidate_is_not_delete": True,
            },
        },
        "manifest": None,
        "undo_available": False,
        "recommendations": [],
        "tags": ["contract_test"],
    }
    write_text(path, json.dumps(data, ensure_ascii=False))


def write_fake_backup_selection_decision_report(path: Path, target_file: Path) -> None:
    data = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "bot_controller",
        "action": "export_selection_decision",
        "risk_level": "safe",
        "status": "success",
        "summary": {
            "selected_count": 2,
            "blocked_count": 0,
            "invalid_count": 0,
            "undo_available": False,
        },
        "input": {},
        "results": {
            "schema": "bot_selection_decision_v2",
            "status": "ready",
            "summary": {
                "input_decision_count": 2,
                "selected_count": 2,
                "skipped_count": 0,
                "blocked_count": 0,
                "invalid_count": 0,
                "unselected_count": 0,
                "by_decision": {
                    "needs_backup": 1,
                    "keep": 1,
                },
                "execution_enabled": False,
                "undo_available": False,
            },
            "selected": [
                {
                    "selection_id": "M001",
                    "path": str(target_file),
                    "name": target_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "needs_backup",
                    "plan_action": "backup_first",
                    "decision": "needs_backup",
                    "execution_enabled": False,
                },
                {
                    "selection_id": "M002",
                    "path": str(target_file),
                    "name": target_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "manual_only",
                    "plan_action": "manual_review",
                    "decision": "keep",
                    "execution_enabled": False,
                },
            ],
            "skipped": [],
            "blocked": [],
            "invalid": [],
            "safety_contract": {
                "decision_report_only": True,
                "executes_file_operations": False,
                "requires_execution_adapter": True,
                "requires_backup_adapter_for_backup": True,
                "delete_candidate_is_not_delete": True,
            },
        },
        "manifest": None,
        "undo_available": False,
        "recommendations": [],
        "tags": ["contract_test"],
    }
    write_text(path, json.dumps(data, ensure_ascii=False))


def write_fake_safe_delete_selection_decision_report(
    path: Path,
    safe_file: Path,
    review_file: Path,
) -> None:
    data = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "bot_controller",
        "action": "export_selection_decision",
        "risk_level": "safe",
        "status": "success",
        "summary": {
            "selected_count": 3,
            "blocked_count": 0,
            "invalid_count": 0,
            "undo_available": False,
        },
        "input": {},
        "results": {
            "schema": "bot_selection_decision_v2",
            "status": "ready",
            "summary": {
                "input_decision_count": 3,
                "selected_count": 3,
                "skipped_count": 0,
                "blocked_count": 0,
                "invalid_count": 0,
                "unselected_count": 0,
                "by_decision": {
                    "delete_candidate": 2,
                    "keep": 1,
                },
                "execution_enabled": False,
                "undo_available": False,
            },
            "selected": [
                {
                    "selection_id": "M001",
                    "path": str(safe_file),
                    "name": safe_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "delete_candidate",
                    "plan_action": "delete_candidate",
                    "decision": "delete_candidate",
                    "execution_enabled": False,
                },
                {
                    "selection_id": "M002",
                    "path": str(review_file),
                    "name": review_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "manual_only",
                    "plan_action": "manual_review",
                    "decision": "delete_candidate",
                    "execution_enabled": False,
                },
                {
                    "selection_id": "M003",
                    "path": str(safe_file),
                    "name": safe_file.name,
                    "size_text": "1.00 KB",
                    "selection_group": "needs_selection",
                    "policy_decision": "manual_only",
                    "plan_action": "manual_review",
                    "decision": "keep",
                    "execution_enabled": False,
                },
            ],
            "skipped": [],
            "blocked": [],
            "invalid": [],
            "safety_contract": {
                "decision_report_only": True,
                "executes_file_operations": False,
                "requires_execution_adapter": True,
                "requires_safe_delete_adapter_for_delete": True,
                "delete_candidate_is_not_delete": True,
            },
        },
        "manifest": None,
        "undo_available": False,
        "recommendations": [],
        "tags": ["contract_test"],
    }
    write_text(path, json.dumps(data, ensure_ascii=False))


def test_execution_adapter_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        target_file = sandbox / "execution_adapter" / "keep_me.tmp"
        report_path = sandbox / "selection_decision_report.json"
        write_text(target_file, "adapter contract")
        write_fake_selection_decision_report(report_path, target_file)

        dry_run = build_execution_adapter_result(source_report_path=report_path, mode="dry_run")
        assert_condition(dry_run["schema"] == "execution_adapter_v1", "Execution Adapter should expose v1 schema.")
        assert_condition(dry_run["status"] == "dry_run", "Execution Adapter dry-run should not require token.")
        assert_condition(
            dry_run["summary"]["file_operations_executed"] is False,
            "Execution Adapter v1 must not execute file operations.",
        )
        assert_condition(
            dry_run["summary"]["recordable_noop_count"] == 1,
            "Execution Adapter should record keep/manual decisions as no-op capable.",
        )
        assert_condition(
            dry_run["summary"]["blocked_count"] == 1,
            "Execution Adapter should block delete_candidate in v1.",
        )

        no_token = build_execution_adapter_result(source_report_path=report_path, mode="apply")
        assert_condition(
            no_token["status"] == "requires_final_confirmation",
            "Execution Adapter apply should require final token.",
        )

        applied = build_execution_adapter_result(
            source_report_path=report_path,
            mode="apply",
            final_token=FINAL_CONFIRM_TOKEN,
        )
        assert_condition(
            applied["status"] == "completed_with_blocks",
            "Execution Adapter should apply record-only steps while keeping file operations blocked.",
        )
        assert_condition(
            applied["summary"]["adapter_executed"] is True,
            "Execution Adapter should mark adapter execution after valid final token.",
        )
        assert_condition(
            applied["summary"]["file_operations_executed"] is False,
            "Execution Adapter must still avoid file operations after token in v1.",
        )
        assert_condition(target_file.exists(), "Execution Adapter v1 must not delete the target file.")

        return {
            "dry_run_summary": dry_run["summary"],
            "no_token_status": no_token["status"],
            "applied_summary": applied["summary"],
            "target_exists_after_apply": target_file.exists(),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_file_operation_adapter_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        source_file = sandbox / "file_operation_adapter" / "move_me.mp4"
        destination_root = sandbox / "file_operation_destination"
        report_path = sandbox / "move_selection_decision_report.json"
        write_text(source_file, "adapter move contract")
        destination_root.mkdir(parents=True, exist_ok=True)
        write_fake_move_selection_decision_report(report_path, source_file)

        dry_run = build_file_operation_adapter_result(
            source_report_path=report_path,
            destination_root=destination_root,
            mode="dry_run",
        )
        assert_condition(dry_run["schema"] == "file_operation_adapter_v1", "File Operation Adapter should expose v1 schema.")
        assert_condition(dry_run["status"] == "dry_run", "Move dry-run should be ready.")
        assert_condition(dry_run["summary"]["move_requested_count"] == 1, "Move dry-run should find one move_later item.")
        assert_condition(dry_run["summary"]["movable_count"] == 1, "Move dry-run should have one movable item.")
        assert_condition(
            dry_run["summary"]["file_operations_executed"] is False,
            "Move dry-run must not execute file operations.",
        )
        assert_condition(source_file.exists(), "Dry-run must not move the source file.")

        no_token = build_file_operation_adapter_result(
            source_report_path=report_path,
            destination_root=destination_root,
            mode="apply",
        )
        assert_condition(
            no_token["status"] == "requires_final_confirmation",
            "Move apply should require final token.",
        )
        assert_condition(source_file.exists(), "Missing token must not move the source file.")

        applied = build_file_operation_adapter_result(
            source_report_path=report_path,
            destination_root=destination_root,
            mode="apply",
            final_token=FINAL_MOVE_TOKEN,
        )
        manifest = applied.get("manifest")
        moved_file = destination_root / source_file.name
        assert_condition(applied["status"] == "completed", "Move apply should complete in sandbox.")
        assert_condition(applied["summary"]["moved_count"] == 1, "Move apply should move one file.")
        assert_condition(applied["summary"]["file_operations_executed"] is True, "Move apply should execute a file operation.")
        assert_condition(bool(manifest), "Move apply should create a manifest.")
        assert_condition(not source_file.exists(), "Source should be moved after apply.")
        assert_condition(moved_file.exists(), "Destination file should exist after apply.")

        preview = preview_manifest(manifest)
        assert_condition(preview["restorable_count"] == 1, "Move manifest should be restorable.")
        restored = restore_manifest(manifest)
        assert_condition(restored["status"] == "success", "Move manifest restore should succeed.")
        assert_condition(source_file.exists(), "Source file should exist again after restore.")

        return {
            "dry_run_summary": dry_run["summary"],
            "no_token_status": no_token["status"],
            "applied_summary": applied["summary"],
            "manifest": manifest,
            "restore": {
                "status": restored["status"],
                "restored_count": restored.get("restored_count"),
            },
            "source_exists_after_restore": source_file.exists(),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_backup_adapter_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        source_file = sandbox / "backup_adapter" / "needs_backup.prproj"
        backup_run_dir = sandbox / "backup_run"
        report_path = sandbox / "backup_selection_decision_report.json"
        write_text(source_file, "backup adapter contract")
        write_fake_backup_selection_decision_report(report_path, source_file)

        dry_run = build_backup_adapter_result(
            source_report_path=report_path,
            backup_run_dir=backup_run_dir,
            mode="dry_run",
        )
        assert_condition(dry_run["schema"] == BACKUP_ADAPTER_SCHEMA, "Backup Adapter should expose v1 schema.")
        assert_condition(dry_run["status"] == "dry_run", "Backup dry-run should be ready.")
        assert_condition(dry_run["summary"]["backup_requested_count"] == 1, "Backup dry-run should find one needs_backup item.")
        assert_condition(dry_run["summary"]["backupable_count"] == 1, "Backup dry-run should have one backupable item.")
        assert_condition(
            dry_run["summary"]["file_operations_executed"] is False,
            "Backup dry-run must not copy files.",
        )
        planned_backup = Path(dry_run["steps"][0]["planned_backup_path"])
        assert_condition(source_file.exists(), "Backup dry-run must preserve source file.")
        assert_condition(not planned_backup.exists(), "Backup dry-run must not create the backup copy.")

        no_token = build_backup_adapter_result(
            source_report_path=report_path,
            backup_run_dir=backup_run_dir,
            mode="apply",
        )
        assert_condition(
            no_token["status"] == "requires_final_confirmation",
            "Backup apply should require final token.",
        )
        assert_condition(source_file.exists(), "Missing token must preserve source file.")
        assert_condition(not planned_backup.exists(), "Missing token must not copy backup file.")

        applied = build_backup_adapter_result(
            source_report_path=report_path,
            backup_run_dir=backup_run_dir,
            mode="apply",
            final_token=FINAL_BACKUP_TOKEN,
        )
        manifest = applied.get("manifest")
        actual_backup = Path(applied["steps"][0]["actual_backup_path"])
        assert_condition(applied["status"] == "completed", "Backup apply should complete in sandbox.")
        assert_condition(applied["summary"]["backed_up_count"] == 1, "Backup apply should copy one file.")
        assert_condition(applied["summary"]["file_operations_executed"] is True, "Backup apply should execute one copy operation.")
        assert_condition(bool(manifest), "Backup apply should create a manifest.")
        assert_condition(source_file.exists(), "Backup apply must preserve source file.")
        assert_condition(actual_backup.exists(), "Backup copy should exist after apply.")
        assert_condition(
            source_file.read_text(encoding="utf-8") == actual_backup.read_text(encoding="utf-8"),
            "Backup copy content should match source.",
        )

        return {
            "dry_run_summary": dry_run["summary"],
            "no_token_status": no_token["status"],
            "applied_summary": applied["summary"],
            "manifest": manifest,
            "source_exists_after_apply": source_file.exists(),
            "backup_exists_after_apply": actual_backup.exists(),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_safe_delete_adapter_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        safe_file = sandbox / "Downloads" / "delete_me.tmp"
        review_file = sandbox / "Review" / "keep_me.log"
        report_path = sandbox / "safe_delete_selection_decision_report.json"
        write_text(safe_file, "safe delete adapter contract")
        write_text(review_file, "review required contract")
        write_fake_safe_delete_selection_decision_report(report_path, safe_file, review_file)

        dry_run = build_safe_delete_adapter_result(
            source_report_path=report_path,
            mode="dry_run",
        )
        assert_condition(dry_run["schema"] == SAFE_DELETE_ADAPTER_SCHEMA, "Safe Delete Adapter should expose v1 schema.")
        assert_condition(dry_run["status"] == "dry_run", "Safe delete dry-run should be ready.")
        assert_condition(dry_run["summary"]["delete_requested_count"] == 2, "Safe delete dry-run should find two delete_candidate items.")
        assert_condition(dry_run["summary"]["deletable_count"] == 1, "Safe delete dry-run should allow only safe_delete risk.")
        assert_condition(dry_run["summary"]["blocked_count"] == 1, "Safe delete dry-run should block review_required risk.")
        assert_condition(
            dry_run["summary"]["file_operations_executed"] is False,
            "Safe delete dry-run must not delete files.",
        )
        assert_condition(safe_file.exists(), "Safe delete dry-run must not delete the safe file.")
        assert_condition(review_file.exists(), "Safe delete dry-run must not delete the review file.")

        no_token = build_safe_delete_adapter_result(
            source_report_path=report_path,
            mode="apply",
        )
        assert_condition(
            no_token["status"] == "requires_final_confirmation",
            "Safe delete apply should require final token.",
        )
        assert_condition(safe_file.exists(), "Missing token must not delete the safe file.")

        applied = build_safe_delete_adapter_result(
            source_report_path=report_path,
            mode="apply",
            final_token=FINAL_DELETE_TOKEN,
        )
        assert_condition(applied["status"] == "completed_with_blocks", "Safe delete apply should delete safe file and block review file.")
        assert_condition(applied["summary"]["deleted_count"] == 1, "Safe delete apply should delete one file.")
        assert_condition(applied["summary"]["blocked_count"] == 1, "Safe delete apply should keep one blocked file.")
        assert_condition(applied["summary"]["file_operations_executed"] is True, "Safe delete apply should execute one file operation.")
        assert_condition(not safe_file.exists(), "Safe file should be sent to Recycle Bin after token.")
        assert_condition(review_file.exists(), "Review-required file must remain after token.")

        return {
            "dry_run_summary": dry_run["summary"],
            "no_token_status": no_token["status"],
            "applied_summary": applied["summary"],
            "safe_file_exists_after_apply": safe_file.exists(),
            "review_file_exists_after_apply": review_file.exists(),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_bot_backup_flow_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        source_file = sandbox / "bot_backup_flow" / "project_file.prproj"
        write_text(source_file, "bot backup flow")

        groups = {
            "safe_to_execute": [],
            "needs_selection": [
                {
                    "path": str(source_file),
                    "name": source_file.name,
                    "size": source_file.stat().st_size,
                    "size_text": "1.00 KB",
                    "candidate_group": "large_project_or_archive",
                    "context": "contract_test",
                    "policy_decision": "needs_backup",
                    "plan_action": "backup_first",
                    "plan_status": "requires_user_input",
                    "reason": "Fake item for bot backup flow.",
                    "can_execute_now": False,
                    "requires_user_input": True,
                }
            ],
            "do_not_touch": [],
            "review_only": [],
        }
        session = build_selection_session_from_groups(groups, include_items=True)
        selection_id = session["groups"]["needs_selection"][0]["selection_id"]
        contract_report_tags = ["contract_test", "full_system"]

        dry_run = export_backup_selection_flow_report(
            {selection_id: "needs_backup"},
            mode="dry_run",
            session=session,
            note="full_system_bot_backup_contract",
            extra_tags=contract_report_tags,
        )
        dry_flow = dry_run["flow"]
        assert_condition(dry_flow["schema"] == "bot_backup_flow_v1", "Bot backup flow should expose v1 schema.")
        assert_condition(dry_flow["status"] == "dry_run", "Bot backup dry-run should be ready.")
        assert_condition(
            dry_flow["summary"]["backupable_count"] == 1,
            "Bot backup dry-run should find one backupable item.",
        )
        assert_condition(source_file.exists(), "Bot backup dry-run must preserve source file.")

        no_token = export_backup_selection_flow_report(
            {selection_id: "needs_backup"},
            mode="apply",
            session=session,
            note="full_system_bot_backup_contract_no_token",
            extra_tags=contract_report_tags,
        )
        assert_condition(
            no_token["flow"]["status"] == "requires_final_confirmation",
            "Bot backup apply should require final token.",
        )
        assert_condition(source_file.exists(), "Bot backup missing token must preserve source file.")

        applied = export_backup_selection_flow_report(
            {selection_id: "needs_backup"},
            mode="apply",
            final_token=FINAL_BACKUP_TOKEN,
            session=session,
            note="full_system_bot_backup_contract_apply",
            extra_tags=contract_report_tags,
        )
        applied_flow = applied["flow"]
        manifest = applied_flow["summary"]["manifest"]
        backup_report = applied_flow["backup_report"]["backup"]
        actual_backup = Path(backup_report["steps"][0]["actual_backup_path"])
        assert_condition(applied_flow["status"] == "completed", "Bot backup apply should complete in sandbox.")
        assert_condition(applied_flow["summary"]["backed_up_count"] == 1, "Bot backup should copy one file.")
        assert_condition(applied_flow["summary"]["file_operations_executed"] is True, "Bot backup should execute copy after token.")
        assert_condition(bool(manifest), "Bot backup apply should expose a manifest.")
        assert_condition(source_file.exists(), "Bot backup apply must preserve source file.")
        assert_condition(actual_backup.exists(), "Bot backup copy should exist.")

        return {
            "dry_summary": dry_flow["summary"],
            "no_token_status": no_token["flow"]["status"],
            "applied_summary": applied_flow["summary"],
            "manifest": manifest,
            "source_exists_after_apply": source_file.exists(),
            "backup_exists_after_apply": actual_backup.exists(),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_bot_move_later_flow_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        source_file = sandbox / "bot_move_later_flow" / "selected_video.mp4"
        destination_root = sandbox / "bot_move_later_destination"
        write_text(source_file, "bot move later flow")
        destination_root.mkdir(parents=True, exist_ok=True)

        groups = {
            "safe_to_execute": [],
            "needs_selection": [
                {
                    "path": str(source_file),
                    "name": source_file.name,
                    "size": source_file.stat().st_size,
                    "size_text": "1.00 KB",
                    "candidate_group": "large_video",
                    "context": "contract_test",
                    "policy_decision": "move_later",
                    "plan_action": "move_later",
                    "plan_status": "requires_user_input",
                    "reason": "Fake item for bot move-later flow.",
                    "can_execute_now": False,
                    "requires_user_input": True,
                }
            ],
            "do_not_touch": [],
            "review_only": [],
        }
        session = build_selection_session_from_groups(groups, include_items=True)
        selection_id = session["groups"]["needs_selection"][0]["selection_id"]
        contract_report_tags = ["contract_test", "full_system"]

        dry_run = export_move_later_selection_flow_report(
            {selection_id: "move_later"},
            destination_root=destination_root,
            mode="dry_run",
            session=session,
            note="full_system_bot_move_later_contract",
            extra_tags=contract_report_tags,
        )
        dry_flow = dry_run["flow"]
        assert_condition(dry_flow["schema"] == "bot_move_later_flow_v1", "Bot move-later flow should expose v1 schema.")
        assert_condition(dry_flow["status"] == "dry_run", "Bot move-later dry-run should be ready.")
        assert_condition(
            dry_flow["summary"]["movable_count"] == 1,
            "Bot move-later dry-run should find one movable item.",
        )
        assert_condition(source_file.exists(), "Bot move-later dry-run must not move the source file.")

        no_token = export_move_later_selection_flow_report(
            {selection_id: "move_later"},
            destination_root=destination_root,
            mode="apply",
            session=session,
            note="full_system_bot_move_later_contract_no_token",
            extra_tags=contract_report_tags,
        )
        assert_condition(
            no_token["flow"]["status"] == "requires_final_confirmation",
            "Bot move-later apply should require final token.",
        )
        assert_condition(source_file.exists(), "Bot move-later missing token must not move source file.")

        applied = export_move_later_selection_flow_report(
            {selection_id: "move_later"},
            destination_root=destination_root,
            mode="apply",
            final_token=FINAL_MOVE_TOKEN,
            session=session,
            note="full_system_bot_move_later_contract_apply",
            extra_tags=contract_report_tags,
        )
        applied_flow = applied["flow"]
        manifest = applied_flow["summary"]["manifest"]
        moved_file = destination_root / source_file.name
        assert_condition(applied_flow["status"] == "completed", "Bot move-later apply should complete in sandbox.")
        assert_condition(applied_flow["summary"]["moved_count"] == 1, "Bot move-later should move one file.")
        assert_condition(applied_flow["summary"]["file_operations_executed"] is True, "Bot move-later should execute move after token.")
        assert_condition(bool(manifest), "Bot move-later apply should expose a manifest.")
        assert_condition(moved_file.exists(), "Moved file should exist in destination.")

        restored = restore_manifest(manifest)
        assert_condition(restored["status"] == "success", "Bot move-later manifest restore should succeed.")
        assert_condition(source_file.exists(), "Source file should exist again after bot flow restore.")

        return {
            "dry_summary": dry_flow["summary"],
            "no_token_status": no_token["flow"]["status"],
            "applied_summary": applied_flow["summary"],
            "manifest": manifest,
            "restore_status": restored["status"],
            "source_exists_after_restore": source_file.exists(),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_bot_safe_delete_flow_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        safe_file = sandbox / "Downloads" / "delete_me.tmp"
        write_text(safe_file, "bot safe delete flow")

        groups = {
            "safe_to_execute": [],
            "needs_selection": [
                {
                    "path": str(safe_file),
                    "name": safe_file.name,
                    "size": safe_file.stat().st_size,
                    "size_text": "1.00 KB",
                    "candidate_group": "safe_delete_candidate",
                    "context": "contract_test",
                    "policy_decision": "delete_candidate",
                    "plan_action": "delete_candidate",
                    "plan_status": "requires_user_input",
                    "reason": "Fake item for bot safe-delete flow.",
                    "can_execute_now": False,
                    "requires_user_input": True,
                }
            ],
            "do_not_touch": [],
            "review_only": [],
        }
        session = build_selection_session_from_groups(groups, include_items=True)
        selection_id = session["groups"]["needs_selection"][0]["selection_id"]
        contract_report_tags = ["contract_test", "full_system"]

        dry_run = export_safe_delete_selection_flow_report(
            {selection_id: "delete_candidate"},
            mode="dry_run",
            session=session,
            note="full_system_bot_safe_delete_contract",
            extra_tags=contract_report_tags,
        )
        dry_flow = dry_run["flow"]
        assert_condition(dry_flow["schema"] == "bot_safe_delete_flow_v1", "Bot safe-delete flow should expose v1 schema.")
        assert_condition(dry_flow["status"] == "dry_run", "Bot safe-delete dry-run should be ready.")
        assert_condition(
            dry_flow["summary"]["deletable_count"] == 1,
            "Bot safe-delete dry-run should find one deletable item.",
        )
        assert_condition(safe_file.exists(), "Bot safe-delete dry-run must not delete the file.")

        no_token = export_safe_delete_selection_flow_report(
            {selection_id: "delete_candidate"},
            mode="apply",
            session=session,
            note="full_system_bot_safe_delete_contract_no_token",
            extra_tags=contract_report_tags,
        )
        assert_condition(
            no_token["flow"]["status"] == "requires_final_confirmation",
            "Bot safe-delete apply should require final token.",
        )
        assert_condition(safe_file.exists(), "Bot safe-delete missing token must not delete source file.")

        applied = export_safe_delete_selection_flow_report(
            {selection_id: "delete_candidate"},
            mode="apply",
            final_token=FINAL_DELETE_TOKEN,
            session=session,
            note="full_system_bot_safe_delete_contract_apply",
            extra_tags=contract_report_tags,
        )
        applied_flow = applied["flow"]
        assert_condition(applied_flow["status"] == "completed", "Bot safe-delete apply should complete in sandbox.")
        assert_condition(applied_flow["summary"]["deleted_count"] == 1, "Bot safe-delete should delete one file.")
        assert_condition(applied_flow["summary"]["file_operations_executed"] is True, "Bot safe-delete should execute delete after token.")
        assert_condition(not safe_file.exists(), "Safe file should be sent to Recycle Bin after bot flow apply.")

        return {
            "dry_summary": dry_flow["summary"],
            "no_token_status": no_token["flow"]["status"],
            "applied_summary": applied_flow["summary"],
            "safe_file_exists_after_apply": safe_file.exists(),
        }
    finally:
        cleanup_sandbox(sandbox)


def test_obsidian_exporter_contract() -> dict[str, Any]:
    sandbox = make_sandbox()
    try:
        vault = sandbox / "obsidian_vault"
        result = build_obsidian_export_result(
            vault_root=vault,
            max_items=20,
            write_files=True,
        )
        expected_files = [
            vault / "00_Index.md",
            vault / "10_System_Map" / "System Flow.md",
            vault / "10_System_Map" / "System Flow.canvas",
            vault / "20_Tools" / "Capability Map.md",
            vault / "30_File_Database" / "Recommendation Queue.md",
            vault / "50_Decisions" / "Safety Contract.md",
            vault / "60_Graph_Nodes" / "Graph Hub.md",
        ]

        assert_condition(result["schema"] == OBSIDIAN_EXPORT_SCHEMA, "Obsidian exporter should expose v1 schema.")
        assert_condition(result["status"] == "success", "Obsidian exporter should complete successfully.")
        assert_condition(result["summary"]["note_count"] >= len(expected_files), "Obsidian exporter should build core notes.")
        assert_condition(result["summary"]["graph_node_count"] >= 20, "Obsidian exporter should create graph node notes.")
        for path in expected_files:
            assert_condition(path.exists(), f"Expected Obsidian note missing: {path}")

        index_text = (vault / "00_Index.md").read_text(encoding="utf-8")
        flow_text = (vault / "10_System_Map" / "System Flow.md").read_text(encoding="utf-8")
        hub_text = (vault / "60_Graph_Nodes" / "Graph Hub.md").read_text(encoding="utf-8")
        assert_condition("AI Desktop Assistant Map" in index_text, "Obsidian index should contain title.")
        assert_condition("flowchart TD" in flow_text, "Obsidian flow note should contain Mermaid graph.")
        assert_condition("[[60_Graph_Nodes/Tools/" in hub_text, "Graph hub should link tool nodes.")
        assert_condition(
            result["safety_contract"]["executes_file_operations"] is False,
            "Obsidian exporter must not execute file operations.",
        )
        assert_condition(
            result["safety_contract"]["writes_only_vault_files"] is True,
            "Obsidian exporter should only write vault files.",
        )
        assert_condition(
            result["safety_contract"]["prunes_generated_graph_nodes"] is True,
            "Obsidian exporter should only prune generated graph nodes.",
        )

        return {
            "vault": str(vault),
            "summary": result["summary"],
            "files": [str(path) for path in expected_files],
        }
    finally:
        cleanup_sandbox(sandbox)


def test_feed_readiness_contract() -> dict[str, Any]:
    result = build_feed_readiness_result()
    summary = result["summary"]
    check_ids = {item["id"] for item in result["checks"]}

    expected_checks = {
        "config",
        "capability_registry",
        "external_apps",
        "recommendation_queue",
        "action_policy",
        "full_system_tester",
        "report_schema",
        "audit_snapshot",
        "feed_sources",
    }
    assert_condition(
        result["schema"] == "feed_readiness_v1",
        "Feed Readiness should expose v1 schema.",
    )
    assert_condition(
        expected_checks.issubset(check_ids),
        f"Feed Readiness missing checks: {expected_checks - check_ids}",
    )
    assert_condition(
        summary["fail_count"] == 0,
        "Feed Readiness should have no hard blockers in current repo state.",
    )
    assert_condition(
        result["capability_summary"]["total"] >= len(TOOLS_TO_TEST),
        "Feed Readiness should include capability summary.",
    )
    assert_condition(
        result["external_apps_summary"]["available"] == result["external_apps_summary"]["total"],
        "Feed Readiness should see all configured external apps available.",
    )

    return {
        "summary": summary,
        "check_ids": sorted(check_ids),
        "queue_summary": result["recommendation_queue_summary"],
    }


def test_scenario_tester_contract() -> dict[str, Any]:
    result = run_sandbox_scenarios(
        cleanup=True,
        keep_on_failure=False,
        create_report_file=True,
    )
    test_by_name = {
        item["name"]: item
        for item in result["tests"]
    }

    download_scan = test_by_name["Download Organizer scan skips partial and nested files"]["details"]
    risk_guardrails = test_by_name["Risk guardrails for game data, archives and project files"]["details"]

    assert_condition(result["status"] == "success", "Scenario Tester should pass all fake-file cases.")
    assert_condition(result["failed"] == 0, "Scenario Tester should report zero failures.")
    assert_condition(result["cleanup"]["status"] == "cleaned", "Scenario Tester should clean its sandbox.")
    assert_condition(
        download_scan["partial_download_skipped"] is True,
        "Scenario Tester should prove partial downloads are skipped.",
    )
    assert_condition(
        risk_guardrails["riot"]["risk"] == REVIEW_REQUIRED,
        "Scenario Tester should keep Riot Games data at review_required.",
    )
    assert_condition(
        risk_guardrails["protected_project_delete"]["status"] == "blocked",
        "Scenario Tester should prove protected project files cannot be deleted.",
    )

    return {
        "status": result["status"],
        "total": result["total"],
        "passed": result["passed"],
        "failed": result["failed"],
        "cleanup": result["cleanup"],
        "report": result["report"],
    }


def test_bot_panel_ui_contract() -> dict[str, Any]:
    snapshot = build_bot_panel_snapshot()
    demo_root = Path(snapshot["demo_sandbox_root"])
    assert_condition(
        snapshot["schema"] == BOT_PANEL_SCHEMA,
        "Bot Panel UI should expose a stable schema.",
    )
    assert_condition(
        snapshot["entrypoint"] == "python -m tools.ui.bot_panel",
        "Bot Panel UI should expose its module entrypoint.",
    )
    assert_condition(
        snapshot["executes_file_operations_directly"] is False,
        "Bot Panel UI should not bypass adapters for file operations.",
    )
    assert_condition(
        snapshot["supports_assistant_dashboard"] is True,
        "Bot Panel UI should expose an assistant-first dashboard.",
    )
    assert_condition(
        snapshot["supports_issue_cards"] is True,
        "Bot Panel UI should expose assistant issue cards.",
    )
    assert_condition(
        snapshot["supports_full_demo_flow"] is True,
        "Bot Panel UI should expose a full guided demo flow.",
    )
    assert_condition(
        snapshot["supports_one_click_ai_plan"] is True,
        "Bot Panel UI should expose one-click AI plan preview/apply.",
    )
    assert_condition(
        snapshot["supports_assistant_activity_log"] is True,
        "Bot Panel UI should expose a readable assistant activity log.",
    )
    assert_condition(
        snapshot["supports_run_history_panel"] is True,
        "Bot Panel UI should expose recent report history on the assistant screen.",
    )
    assert_condition(
        snapshot["assistant_result_panel_scope"] == "full_width",
        "Bot Panel UI should expose the assistant result panel as a full-width reading area.",
    )
    assert_condition(
        int(snapshot["assistant_result_panel_min_height_px"]) >= 480,
        "Bot Panel UI result panel should be tall enough to read multi-line output.",
    )
    assert_condition(
        int(snapshot["assistant_history_panel_rows"]) >= 8,
        "Bot Panel UI history panel should show enough recent reports without feeling clipped.",
    )
    assert_condition(
        snapshot["assistant_history_panel_scope"] == "bottom_full_height",
        "Bot Panel UI history panel should live in the tall bottom reading area.",
    )
    assert_condition(
        int(snapshot["assistant_history_panel_min_height_px"]) >= 480,
        "Bot Panel UI history panel should have enough vertical room for multiple reports.",
    )
    assert_condition(
        snapshot["assistant_bottom_panel_anchor"] == "bottom_visible",
        "Bot Panel UI should anchor result/history at the bottom so it stays visible.",
    )
    assert_condition(
        snapshot["can_call_safe_delete_adapter"] is True,
        "Bot Panel UI should connect to Safe Delete Adapter.",
    )
    assert_condition(
        snapshot["can_call_backup_adapter"] is True,
        "Bot Panel UI should connect to Backup Adapter.",
    )
    assert_condition(
        snapshot["backup_apply_requires_token"] == FINAL_BACKUP_TOKEN,
        "Bot Panel UI should use the Backup Adapter token.",
    )
    assert_condition(
        snapshot["can_call_file_operation_adapter"] is True,
        "Bot Panel UI should connect to File Operation Adapter.",
    )
    assert_condition(
        snapshot["move_apply_requires_token"] == FINAL_MOVE_TOKEN,
        "Bot Panel UI should use the File Operation Adapter token.",
    )
    assert_condition(
        snapshot["safe_delete_apply_requires_token"] == FINAL_DELETE_TOKEN,
        "Bot Panel UI should use the Safe Delete Adapter token.",
    )
    assert_condition(
        snapshot["supports_move_later_flow"] is True,
        "Bot Panel UI should support move_later flow.",
    )
    assert_condition(
        snapshot["supports_backup_flow"] is True,
        "Bot Panel UI should support needs_backup flow.",
    )
    assert_condition(
        snapshot["supports_move_undo"] is True,
        "Bot Panel UI should expose undo for the latest move manifest.",
    )
    assert_condition(
        snapshot["supports_safe_delete_flow"] is True,
        "Bot Panel UI should support safe_delete flow.",
    )
    assert_condition(
        not demo_root.resolve().is_relative_to(BASE_DIR.resolve()),
        "Bot Panel demo sandbox should stay outside the protected tool workspace.",
    )

    sandbox = create_demo_sandbox()
    try:
        tmp_file = sandbox / "cache" / "old_cache.tmp"
        log_file = sandbox / "logs" / "review_me.log"
        project_file = sandbox / "work" / "edit_project.prproj"
        move_destination = sandbox / "_move_destination"
        assert_condition(tmp_file.exists(), "Bot Panel demo sandbox should create a tmp file.")
        assert_condition(log_file.exists(), "Bot Panel demo sandbox should create a review file.")
        assert_condition(project_file.exists(), "Bot Panel demo sandbox should create a needs_backup project file.")
        assert_condition(move_destination.is_dir(), "Bot Panel demo sandbox should create a move destination.")
        assert_condition(
            classify_file_risk(tmp_file)["risk"] == SAFE_DELETE,
            "Bot Panel demo tmp file should classify as SAFE_DELETE.",
        )
        assert_condition(
            classify_file_risk(log_file)["risk"] == REVIEW_REQUIRED,
            "Bot Panel demo log file should classify as REVIEW_REQUIRED.",
        )
        return {
            **snapshot,
            "demo_sandbox": str(sandbox),
            "move_destination": str(move_destination),
            "tmp_risk": classify_file_risk(tmp_file)["risk"],
            "log_risk": classify_file_risk(log_file)["risk"],
            "project_risk": classify_file_risk(project_file)["risk"],
        }
    finally:
        cleanup_ui_demo_sandbox(sandbox)


def test_dependency_health() -> dict[str, Any]:
    modules = ["psutil", "send2trash", "watchdog"]
    results = []

    for module_name in modules:
        status = "pass"
        error = None
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            status = "fail"
            error = str(exc)
        results.append({
            "module": module_name,
            "status": status,
            "error": error,
        })

    failed = [item for item in results if item["status"] != "pass"]
    assert_condition(not failed, "Missing or broken runtime dependency.")

    return {
        "results": results,
    }


def test_git_submodule_health() -> dict[str, Any]:
    result = run_command(["git", "submodule", "status"])
    assert_condition(result["returncode"] == 0, "git submodule status failed.")
    return result


FULL_SYSTEM_TESTS: list[tuple[str, Callable[[], dict[str, Any]]]] = [
    ("Compile All", test_compileall),
    ("Tool Import Matrix", test_tool_import_matrix),
    ("Main Menu Coverage", test_main_menu_coverage),
    ("Config Health", test_config_health),
    ("Safety Static Audit", test_safety_static_audit),
    ("Risk Classifier Guardrails", test_risk_classifier_guardrails),
    ("Report Manager and Audit Index", test_report_manager_and_audit_index),
    ("Report Schema Validation", test_report_schema_validation),
    ("Audit Center Health", test_audit_center_health),
    ("Undo Manager Roundtrip", test_undo_manager_roundtrip),
    ("Behavior Suite Subprocess", test_behavior_suite_subprocess),
    ("WizTree Adapter Sample CSV", test_wiztree_adapter_sample_csv),
    ("External Apps Registry", test_external_apps_registry),
    ("Capability Registry", test_capability_registry),
    ("System Advisor v2 Contract", test_system_advisor_v2_contract),
    ("Recommendation Center Contract", test_recommendation_center_contract),
    ("Guided Action Runner Contract", test_guided_action_runner_contract),
    ("Natural Command v3 Queue Contract", test_natural_command_v3_queue_contract),
    ("Action Policy Contract", test_action_policy_contract),
    ("Candidate Review Contract", test_candidate_review_contract),
    ("Dry-run Action Planner Contract", test_action_planner_contract),
    ("Pre-feed Bundle Contract", test_pre_feed_bundle_contract),
    ("AI Bot Controller Contract", test_bot_controller_contract),
    ("Auto Scan and Issue Classifier Contract", test_auto_scan_and_issue_classifier_contract),
    ("Execution Adapter Contract", test_execution_adapter_contract),
    ("Backup Adapter Contract", test_backup_adapter_contract),
    ("File Operation Adapter Contract", test_file_operation_adapter_contract),
    ("Safe Delete Adapter Contract", test_safe_delete_adapter_contract),
    ("Bot Backup Flow Contract", test_bot_backup_flow_contract),
    ("Bot Move-later Flow Contract", test_bot_move_later_flow_contract),
    ("Bot Safe-delete Flow Contract", test_bot_safe_delete_flow_contract),
    ("Obsidian Exporter Contract", test_obsidian_exporter_contract),
    ("Feed Readiness Contract", test_feed_readiness_contract),
    ("Scenario Tester Contract", test_scenario_tester_contract),
    ("Bot Panel UI Contract", test_bot_panel_ui_contract),
    ("Dependency Health", test_dependency_health),
    ("Git Submodule Health", test_git_submodule_health),
]


def run_single_full_test(name: str, test_func: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        details = test_func()
        print(f"[PASS] {name}")
        return {
            "name": name,
            "status": "pass",
            "details": details,
        }
    except Exception as exc:
        print(f"[FAIL] {name} -> {exc}")
        return {
            "name": name,
            "status": "fail",
            "error": str(exc),
        }


def run_full_system_suite() -> dict[str, Any]:
    print("\n========== FULL SYSTEM TESTER ==========")

    results = [
        run_single_full_test(name, test_func)
        for name, test_func in FULL_SYSTEM_TESTS
    ]

    passed = sum(1 for item in results if item["status"] == "pass")
    failed = sum(1 for item in results if item["status"] == "fail")
    status = "success" if failed == 0 else "error"

    report = create_report(
        tool_name="full_system_tester",
        status=status,
        input_data={
            "test_count": len(FULL_SYSTEM_TESTS),
        },
        results={
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "tests": results,
        },
        recommendations=[
            "Run this suite before larger refactors or before feeding assistant context.",
            "Add a new case here whenever a new tool or failure mode is discovered.",
        ],
    )

    print("\n========== FULL SYSTEM SUMMARY ==========")
    print(f"Total : {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Report: {report}")

    return {
        "status": status,
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "report": str(report),
        "tests": results,
    }


def run_full_system_tester() -> None:
    run_full_system_suite()


if __name__ == "__main__":
    run_full_system_tester()
