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
from tools.core.report_manager import (
    REPORT_SCHEMA_VERSION,
    create_report,
    read_recent_report_index,
    validate_report_file,
)
from tools.core.risk_classifier import PROTECTED, classify_file_risk
from tools.core.safe_executor import safe_delete
from tools.core.safety_utils import safe_move, save_manifest
from tools.core.tool_tester import TOOLS_TO_TEST
from tools.core.undo_manager import preview_manifest, restore_manifest


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

    assert_condition(protected["risk"] == PROTECTED, "Project root file should be protected.")
    assert_condition(missing_delete["status"] == "missing", "safe_delete should handle missing files.")

    return {
        "protected_readme": protected,
        "missing_delete": missing_delete,
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
