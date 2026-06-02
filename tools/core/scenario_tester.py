from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from config.settings import BASE_DIR
from tools.automation.download_organizer import (
    get_today_folder_name,
    move_download_files,
    scan_download_files,
)
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report
from tools.core.risk_classifier import PROTECTED, REVIEW_REQUIRED, SAFE_DELETE, classify_file_risk
from tools.core.safe_executor import safe_delete
from tools.core.safety_utils import format_size, restore_from_manifest
from tools.storage.empty_folder_finder import find_empty_folders
from tools.storage.folder_size_analyzer import analyze_top_folders
from tools.storage.large_file_finder import find_large_files
from tools.storage.media_organizer import move_media_files, scan_media_files
from tools.storage.temp_cleaner import scan_temp_files
from tools.system.junk_file_cleaner import scan_junk_files


SANDBOX_ROOT_NAME = "_ai_desktop_assistant_scenario_tests"


def get_sandbox_root() -> Path:
    drive = BASE_DIR.drive or "D:"
    return Path(f"{drive}\\") / SANDBOX_ROOT_NAME


def resolve_path(path: str | Path) -> Path:
    try:
        return Path(path).resolve(strict=False)
    except OSError:
        return Path(path).absolute()


def is_sandbox_path(path: str | Path) -> bool:
    root = resolve_path(get_sandbox_root())
    resolved = resolve_path(path)
    return resolved == root or root in resolved.parents


def assert_sandbox_path(path: str | Path) -> None:
    if not is_sandbox_path(path):
        raise RuntimeError(f"Refuse non-sandbox path: {path}")


def make_sandbox() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    sandbox = get_sandbox_root() / f"run_{timestamp}"
    assert_sandbox_path(sandbox)
    sandbox.mkdir(parents=True, exist_ok=False)
    return sandbox


def cleanup_sandbox(sandbox: str | Path) -> dict[str, Any]:
    sandbox_path = Path(sandbox)
    assert_sandbox_path(sandbox_path)

    if not sandbox_path.exists():
        return {
            "status": "missing",
            "sandbox": str(sandbox_path),
        }

    shutil.rmtree(sandbox_path)
    return {
        "status": "cleaned",
        "sandbox": str(sandbox_path),
        "exists_after_cleanup": sandbox_path.exists(),
    }


def write_fake_file(path: Path, size_bytes: int = 128, marker: bytes = b"fake") -> None:
    assert_sandbox_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if size_bytes <= len(marker):
        path.write_bytes(marker[:size_bytes])
        return

    with path.open("wb") as file:
        file.write(marker)
        file.seek(size_bytes - 1)
        file.write(b"\0")


def prepare_sandbox_fixture(sandbox: Path) -> dict[str, Path]:
    assert_sandbox_path(sandbox)

    downloads = sandbox / "Downloads"
    media = sandbox / "Media"
    temp = sandbox / "Temp"
    empty_root = sandbox / "EmptyFolders"
    project = sandbox / "Project"

    paths = {
        "downloads": downloads,
        "media": media,
        "temp": temp,
        "empty_root": empty_root,
        "download_photo": downloads / "root_photo.jpg",
        "download_pdf": downloads / "root_paper.pdf",
        "download_setup": downloads / "setup.exe",
        "download_partial": downloads / "video_downloading.crdownload",
        "premiere_archive": downloads / "app" / "Premiere_Setup.rar",
        "app_cache": downloads / "app" / "installer_cache.tmp",
        "riot_data": downloads / "Riot Games" / "League of Legends" / "Game" / "game_data.wad",
        "media_video": media / "clip.mp4",
        "media_audio": media / "track.mp3",
        "media_text": media / "notes.txt",
        "temp_cache": temp / "cache.tmp",
        "junk_log": downloads / "Junk" / "orphan.log",
        "junk_tmp": downloads / "Junk" / "cache.tmp",
        "empty_a": empty_root / "empty_a",
        "empty_b": empty_root / "empty_b",
        "not_empty": empty_root / "not_empty",
        "dev_artifact": project / "dist" / "bundle.old",
    }

    write_fake_file(paths["download_photo"], 32 * 1024)
    write_fake_file(paths["download_pdf"], 24 * 1024)
    write_fake_file(paths["download_setup"], 64 * 1024)
    write_fake_file(paths["download_partial"], 48 * 1024)
    write_fake_file(paths["premiere_archive"], 2 * 1024 * 1024)
    write_fake_file(paths["app_cache"], 4 * 1024)
    write_fake_file(paths["riot_data"], 2 * 1024 * 1024)
    write_fake_file(paths["media_video"], 2 * 1024 * 1024)
    write_fake_file(paths["media_audio"], 1024 * 1024)
    write_fake_file(paths["media_text"], 512)
    write_fake_file(paths["temp_cache"], 1024)
    write_fake_file(paths["junk_log"], 1024)
    write_fake_file(paths["junk_tmp"], 1024)
    write_fake_file(paths["dev_artifact"], 1024)

    paths["empty_a"].mkdir(parents=True, exist_ok=True)
    paths["empty_b"].mkdir(parents=True, exist_ok=True)
    paths["not_empty"].mkdir(parents=True, exist_ok=True)
    write_fake_file(paths["not_empty"] / "keep.txt", 64)

    return paths


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_case(name: str, func: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        details = func()
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


def run_download_scan_case(paths: dict[str, Path]) -> dict[str, Any]:
    files = scan_download_files(paths["downloads"])
    names = {Path(item["path"]).name for item in files}

    assert_condition("root_photo.jpg" in names, "Download Organizer should find root photo.")
    assert_condition("root_paper.pdf" in names, "Download Organizer should find root document.")
    assert_condition("setup.exe" in names, "Download Organizer should find root installer.")
    assert_condition(
        "video_downloading.crdownload" not in names,
        "Download Organizer should skip partial downloads.",
    )
    assert_condition("Premiere_Setup.rar" not in names, "Download Organizer should not scan nested app folders.")

    return {
        "found_count": len(files),
        "found_names": sorted(names),
        "partial_download_skipped": True,
    }


def run_download_move_restore_case(paths: dict[str, Path]) -> dict[str, Any]:
    files = scan_download_files(paths["downloads"])
    selected = [
        item for item in files
        if Path(item["path"]).name in {"root_photo.jpg", "root_paper.pdf"}
    ]

    assert_condition(len(selected) == 2, "Expected two fake root files for move/restore.")

    result = move_download_files(
        selected_files=selected,
        downloads_dir=paths["downloads"],
        today_folder=paths["downloads"] / get_today_folder_name(),
        preview_report="scenario_tester_sandbox_preview",
    )

    manifest = result.get("manifest")
    assert_condition(result["moved_count"] == 2, "Download move should move two fake files.")
    assert_condition(bool(manifest), "Download move should create a manifest.")

    restore_result = restore_from_manifest(manifest)
    assert_condition(restore_result["status"] == "success", "Download restore should succeed.")
    assert_condition(restore_result["restored_count"] == 2, "Download restore should restore two files.")
    assert_condition(paths["download_photo"].exists(), "Restored fake photo should exist.")
    assert_condition(paths["download_pdf"].exists(), "Restored fake document should exist.")

    return {
        "moved_count": result["moved_count"],
        "manifest": manifest,
        "restored_count": restore_result["restored_count"],
    }


def run_media_move_restore_case(paths: dict[str, Path]) -> dict[str, Any]:
    files = scan_media_files(str(paths["media"]), recursive=False)
    names = {Path(item["path"]).name for item in files}

    assert_condition({"clip.mp4", "track.mp3"}.issubset(names), "Media scan should find fake media.")
    assert_condition("notes.txt" not in names, "Media scan should skip non-media files.")

    result = move_media_files(
        selected_files=files,
        root=paths["media"],
        target=paths["media"] / "Tat_ca_media",
        recursive=False,
        preview_report="scenario_tester_sandbox_preview",
    )

    manifest = result.get("manifest")
    assert_condition(result["moved_count"] == len(files), "Media move should move all fake media.")
    assert_condition(bool(manifest), "Media move should create a manifest.")

    restore_result = restore_from_manifest(manifest)
    assert_condition(restore_result["status"] == "success", "Media restore should succeed.")
    assert_condition(restore_result["restored_count"] == len(files), "Media restore count should match.")
    assert_condition(paths["media_video"].exists(), "Restored fake video should exist.")
    assert_condition(paths["media_audio"].exists(), "Restored fake audio should exist.")

    return {
        "found_names": sorted(names),
        "moved_count": result["moved_count"],
        "manifest": manifest,
        "restored_count": restore_result["restored_count"],
    }


def run_risk_guardrail_case(paths: dict[str, Path]) -> dict[str, Any]:
    riot = classify_file_risk(paths["riot_data"])
    premiere = classify_file_risk(paths["premiere_archive"])
    dev_artifact = classify_file_risk(paths["dev_artifact"])
    protected_project = safe_delete(BASE_DIR / "README.md")
    missing = safe_delete(paths["downloads"] / "missing_fake.tmp")

    assert_condition(riot["risk"] == REVIEW_REQUIRED, "Riot Games data should require review.")
    assert_condition(
        premiere["risk"] == REVIEW_REQUIRED,
        "Installer/archive under Downloads should require review, not auto-delete.",
    )
    assert_condition(dev_artifact["risk"] == REVIEW_REQUIRED, "Dev artifact should require review.")
    assert_condition(protected_project["status"] == "blocked", "Project file safe_delete should be blocked.")
    assert_condition(missing["status"] == "missing", "Missing path should be handled.")

    return {
        "riot": riot,
        "premiere_archive": premiere,
        "dev_artifact": dev_artifact,
        "protected_project_delete": protected_project,
        "missing_delete": missing,
    }


def run_storage_scan_case(paths: dict[str, Path], sandbox: Path) -> dict[str, Any]:
    large_files = find_large_files(str(sandbox), min_size_mb=1, limit=20)
    large_names = {Path(item["path"]).name for item in large_files}
    top_folders = analyze_top_folders(str(sandbox), limit=10)
    top_names = {Path(item["path"]).name for item in top_folders}

    assert_condition("Premiere_Setup.rar" in large_names, "Large file scan should find fake archive.")
    assert_condition("clip.mp4" in large_names, "Large file scan should find fake video.")
    assert_condition("Downloads" in top_names, "Folder analyzer should include fake Downloads.")

    return {
        "large_file_count": len(large_files),
        "large_files": [
            {
                "name": Path(item["path"]).name,
                "size": item["size"],
                "size_text": format_size(item["size"]),
            }
            for item in large_files
        ],
        "top_folder_count": len(top_folders),
        "top_folders": [
            {
                "name": Path(item["path"]).name,
                "size": item["size"],
                "size_text": format_size(item["size"]),
            }
            for item in top_folders
        ],
    }


def run_cleanup_scan_case(paths: dict[str, Path]) -> dict[str, Any]:
    temp_items = scan_temp_files(str(paths["temp"]), max_age_days=1)
    junk_items = scan_junk_files(str(paths["downloads"]), recursive=True, include_empty=True)
    empty_folders = find_empty_folders(str(paths["empty_root"]))

    temp_by_name = {Path(item["path"]).name: item for item in temp_items}
    junk_by_name = {Path(item["path"]).name: item for item in junk_items}
    empty_names = {Path(item["path"]).name for item in empty_folders}

    assert_condition(temp_by_name["cache.tmp"]["risk"] == SAFE_DELETE, "Temp cache should be safe_delete.")
    assert_condition(junk_by_name["cache.tmp"]["risk"] == SAFE_DELETE, "Junk tmp should be safe_delete.")
    assert_condition(junk_by_name["orphan.log"]["risk"] == REVIEW_REQUIRED, "Junk log should require review.")
    assert_condition({"empty_a", "empty_b"}.issubset(empty_names), "Empty folder scan should find fake empties.")
    assert_condition("not_empty" not in empty_names, "Empty folder scan should skip non-empty folders.")

    return {
        "temp_count": len(temp_items),
        "junk_count": len(junk_items),
        "empty_folder_count": len(empty_folders),
        "temp_risks": {name: item["risk"] for name, item in temp_by_name.items()},
        "junk_risks": {name: item["risk"] for name, item in junk_by_name.items()},
        "empty_names": sorted(empty_names),
    }


def run_sandbox_scenarios(
    *,
    cleanup: bool = True,
    keep_on_failure: bool = False,
    create_report_file: bool = True,
) -> dict[str, Any]:
    sandbox = make_sandbox()
    print("\n========== SCENARIO TESTER ==========")
    print(f"Sandbox: {sandbox}")

    paths = prepare_sandbox_fixture(sandbox)
    tests: list[tuple[str, Callable[[], dict[str, Any]]]] = [
        ("Download Organizer scan skips partial and nested files", lambda: run_download_scan_case(paths)),
        ("Download Organizer move and manifest restore", lambda: run_download_move_restore_case(paths)),
        ("Media Organizer move and manifest restore", lambda: run_media_move_restore_case(paths)),
        ("Risk guardrails for game data, archives and project files", lambda: run_risk_guardrail_case(paths)),
        ("Storage scans find fake large files and top folders", lambda: run_storage_scan_case(paths, sandbox)),
        ("Cleanup scanners classify temp, junk and empty folders", lambda: run_cleanup_scan_case(paths)),
    ]

    results = [run_case(name, func) for name, func in tests]
    passed = sum(1 for item in results if item["status"] == "pass")
    failed = sum(1 for item in results if item["status"] == "fail")
    status = "success" if failed == 0 else "error"
    cleanup_result: dict[str, Any] = {
        "requested": cleanup,
        "status": "not_requested",
        "sandbox": str(sandbox),
    }

    if cleanup and (status == "success" or not keep_on_failure):
        try:
            cleanup_result = cleanup_sandbox(sandbox)
        except Exception as exc:
            cleanup_result = {
                "requested": cleanup,
                "status": "error",
                "sandbox": str(sandbox),
                "error": str(exc),
            }
            status = "error"
    elif cleanup:
        cleanup_result = {
            "requested": cleanup,
            "status": "kept_for_debug",
            "sandbox": str(sandbox),
        }

    report = None
    if create_report_file:
        report = create_report(
            tool_name="scenario_tester",
            action="run_sandbox_scenarios",
            status=status,
            risk_level="safe",
            input_data={
                "sandbox": str(sandbox),
                "cleanup": cleanup,
                "keep_on_failure": keep_on_failure,
            },
            results={
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "tests": results,
                "cleanup": cleanup_result,
            },
            recommendations=[
                "Use Scenario Tester for fake-file validation before touching real Downloads/app/game data.",
                "If a real case is confusing, reproduce it here first with fake files.",
            ],
            summary={
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "cleanup_status": cleanup_result.get("status"),
                "undo_available": False,
            },
            undo_available=False,
            tags=["scenario_tester", "sandbox", "fake_files", "safe"],
        )

        log_action(
            "scenario_tester",
            "run_sandbox_scenarios",
            status,
            {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "sandbox": str(sandbox),
                "cleanup_status": cleanup_result.get("status"),
                "report": str(report),
            },
        )

    print("\n========== SCENARIO SUMMARY ==========")
    print(f"Total : {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Cleanup: {cleanup_result.get('status')}")
    if report:
        print(f"Report: {report}")

    return {
        "status": status,
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "sandbox": str(sandbox),
        "cleanup": cleanup_result,
        "report": str(report) if report else None,
        "tests": results,
    }


def run_scenario_tester() -> None:
    run_sandbox_scenarios(cleanup=True, keep_on_failure=True, create_report_file=True)


if __name__ == "__main__":
    run_scenario_tester()
