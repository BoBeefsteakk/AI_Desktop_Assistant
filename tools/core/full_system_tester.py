from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from config.settings import BASE_DIR, USER_SETTINGS_FILE, validate_user_settings
from tools.core.audit_center import get_audit_snapshot
from tools.core.behavior_tester import make_sandbox, cleanup_sandbox, write_text
from tools.core.capability_registry import (
    get_capabilities,
    validate_capability_registry,
)
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
from tools.core.feed_readiness import build_feed_readiness_result
from tools.core.risk_classifier import PROTECTED, REVIEW_REQUIRED, SAFE_DELETE, classify_file_risk
from tools.core.scenario_tester import run_sandbox_scenarios
from tools.core.safe_executor import safe_delete
from tools.core.safety_utils import safe_move, save_manifest
from tools.core.tool_tester import TOOLS_TO_TEST
from tools.core.undo_manager import preview_manifest, restore_manifest
from tools.search import natural_command
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
    ("tools/core/safety_utils.py", "shutil.move"),
    ("tools/core/behavior_tester.py", "shutil.rmtree"),
    ("tools/core/scenario_tester.py", "shutil.rmtree"),
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

    return {
        "recommendation_ids": sorted(recommendation_ids),
        "summary": summary,
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

        dry_run = execute_guided_action(context, dry_run=True)
        assert_condition(dry_run["status"] == "dry_run", "Guided dry-run should not execute target tool.")
        assert_condition(dry_run["executed"] is False, "Guided dry-run must stay non-mutating.")
        assert_condition(Path(dry_run["report"]).exists(), "Guided dry-run should create a report.")

        return {
            "preview_ready_count": preview["ready_count"],
            "target_tool": context["capability"]["id"],
            "dry_run_report": dry_run["report"],
            "no_tool_status": no_tool_context["status"],
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
    ("Feed Readiness Contract", test_feed_readiness_contract),
    ("Scenario Tester Contract", test_scenario_tester_contract),
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
