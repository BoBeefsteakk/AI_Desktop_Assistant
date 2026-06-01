from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

from config.settings import BASE_DIR, USER_SETTINGS_FILE, validate_user_settings
from tools.automation import download_organizer, download_watcher, startup_launcher
from tools.core.audit_center import get_audit_snapshot
from tools.core.report_manager import create_report
from tools.core import external_apps, guided_action_runner, recommendation_center
from tools.core.risk_classifier import PROTECTED, REVIEW_REQUIRED, SAFE_DELETE, classify_file_risk
from tools.core.safe_executor import safe_delete
from tools.core.safety_utils import restore_from_manifest, safe_move, save_manifest
from tools.core.undo_manager import preview_manifest, restore_manifest
from tools.search import natural_command
from tools.storage import empty_folder_finder, media_organizer, system_advisor
from tools.system.disk_checker import get_disk_info
from tools.system.process_monitor import get_top_processes


SANDBOX_ROOT = BASE_DIR.parent / "_ai_desktop_assistant_behavior_tests"


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def make_sandbox() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    sandbox = SANDBOX_ROOT / f"run_{timestamp}"

    count = 1
    while sandbox.exists():
        sandbox = SANDBOX_ROOT / f"run_{timestamp}_{count}"
        count += 1

    sandbox.mkdir(parents=True, exist_ok=False)
    return sandbox


def cleanup_sandbox(sandbox: Path) -> None:
    root = SANDBOX_ROOT.resolve()
    target = sandbox.resolve()

    if target == root or root not in target.parents:
        raise RuntimeError(f"Refuse to cleanup unsafe sandbox path: {target}")

    if target.exists():
        shutil.rmtree(target)


def write_text(path: Path, content: str = "test") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_risk_classifier_and_safe_delete(sandbox: Path) -> dict[str, Any]:
    protected_file = BASE_DIR / "README.md"
    risk_data = classify_file_risk(protected_file)
    delete_result = safe_delete(protected_file)
    missing_result = safe_delete(sandbox / "missing.tmp")
    downloads_temp = classify_file_risk(sandbox / "Downloads" / "cache.tmp")
    appdata_temp = classify_file_risk(sandbox / "AppData" / "Local" / "Temp" / "safe.tmp")
    appdata_data = classify_file_risk(sandbox / "AppData" / "Local" / "Vendor" / "data.db")
    dev_artifact = classify_file_risk(sandbox / "project" / "dist" / "bundle.old")
    browser_cache = classify_file_risk(
        sandbox / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cache" / "entry"
    )
    windows_temp = classify_file_risk(Path(r"C:\Windows\Temp\safe.tmp"))

    assert_condition(
        risk_data["risk"] == PROTECTED,
        "Project file should be protected by risk classifier.",
    )
    assert_condition(
        delete_result["status"] == "blocked",
        "safe_delete should block protected project files.",
    )
    assert_condition(
        missing_result["status"] == "missing",
        "safe_delete should report missing paths without error.",
    )
    assert_condition(
        downloads_temp["risk"] == SAFE_DELETE,
        "Temp files inside Downloads should be safe_delete.",
    )
    assert_condition(
        appdata_temp["risk"] == SAFE_DELETE,
        "Temp files inside AppData Local Temp should be safe_delete.",
    )
    assert_condition(
        appdata_data["risk"] == REVIEW_REQUIRED,
        "Generic AppData files should require review, not hard block.",
    )
    assert_condition(
        dev_artifact["risk"] == REVIEW_REQUIRED
        and dev_artifact["category"] == "review_dev_artifact",
        "Dev artifacts should require review instead of becoming protected.",
    )
    assert_condition(
        browser_cache["risk"] == SAFE_DELETE,
        "Known browser cache should remain safe_delete even under AppData.",
    )
    assert_condition(
        windows_temp["risk"] == PROTECTED,
        "Windows paths should remain protected even when they contain Temp.",
    )

    return {
        "protected_risk": risk_data,
        "protected_delete": delete_result,
        "missing_delete": missing_result,
        "downloads_temp": downloads_temp,
        "appdata_temp": appdata_temp,
        "appdata_data": appdata_data,
        "dev_artifact": dev_artifact,
        "browser_cache": browser_cache,
        "windows_temp": windows_temp,
    }


def test_download_organizer_roundtrip(sandbox: Path) -> dict[str, Any]:
    root = sandbox / "downloads"
    write_text(root / "photo.jpg", "fake image")
    write_text(root / "paper.pdf", "fake pdf")
    write_text(root / "archive.zip", "fake zip")
    write_text(root / "downloading.crdownload", "partial")

    files = download_organizer.scan_download_files(root)
    names = sorted(Path(item["path"]).name for item in files)

    assert_condition(
        names == ["archive.zip", "paper.pdf", "photo.jpg"],
        "Download Organizer should skip temporary download files.",
    )

    move_result = download_organizer.move_download_files(
        selected_files=files,
        downloads_dir=root,
        today_folder=root / download_organizer.get_today_folder_name(),
        preview_report="behavior_test",
    )

    assert_condition(
        move_result["moved_count"] == 3,
        "Download Organizer should move all selected files.",
    )
    assert_condition(
        (root / "downloading.crdownload").exists(),
        "Temporary download file should remain untouched.",
    )

    download_organizer.restore_downloads_from_manifest(move_result["manifest"])

    assert_condition((root / "photo.jpg").exists(), "photo.jpg should restore.")
    assert_condition((root / "paper.pdf").exists(), "paper.pdf should restore.")
    assert_condition((root / "archive.zip").exists(), "archive.zip should restore.")

    return {
        "scan_count": len(files),
        "moved_count": move_result["moved_count"],
        "manifest": move_result["manifest"],
    }


def test_download_watcher_startup_scan(sandbox: Path) -> dict[str, Any]:
    root = sandbox / "watcher"
    write_text(root / "watch_photo.png", "fake image")
    write_text(root / "watch_doc.pdf", "fake pdf")
    write_text(root / "partial.crdownload", "partial")

    original_wait = download_watcher.WAIT_AFTER_EVENT_SECONDS
    original_interval = download_watcher.STABLE_CHECK_INTERVAL
    original_times = download_watcher.STABLE_CHECK_TIMES

    try:
        download_watcher.WAIT_AFTER_EVENT_SECONDS = 0
        download_watcher.STABLE_CHECK_INTERVAL = 0
        download_watcher.STABLE_CHECK_TIMES = 1

        results = download_watcher.scan_existing_files_once(root)

    finally:
        download_watcher.WAIT_AFTER_EVENT_SECONDS = original_wait
        download_watcher.STABLE_CHECK_INTERVAL = original_interval
        download_watcher.STABLE_CHECK_TIMES = original_times

    moved = [
        item for item in results
        if item["status"] == "moved"
    ]
    skipped = [
        item for item in results
        if item["status"] == "skipped"
    ]

    assert_condition(len(moved) == 2, "Download Watcher should move ready files.")
    assert_condition(len(skipped) == 1, "Download Watcher should skip partial files.")
    assert_condition(
        (root / "partial.crdownload").exists(),
        "Partial download file should remain untouched.",
    )

    return {
        "moved_count": len(moved),
        "skipped_count": len(skipped),
    }


def test_media_organizer_roundtrip(sandbox: Path) -> dict[str, Any]:
    root = sandbox / "media"
    write_text(root / "song.mp3", "fake audio")
    write_text(root / "video.mp4", "fake video")
    write_text(root / "note.txt", "not media")
    write_text(root / "sub" / "clip.mkv", "fake clip")

    files = media_organizer.scan_media_files(str(root), recursive=True)
    extensions = sorted(item["extension"] for item in files)

    assert_condition(
        extensions == [".mkv", ".mp3", ".mp4"],
        "Media Organizer should only scan supported media files.",
    )

    move_result = media_organizer.move_media_files(
        selected_files=files,
        root=root,
        target=root / "Tat_ca_media",
        recursive=True,
        preview_report="behavior_test",
    )

    assert_condition(
        move_result["moved_count"] == 3,
        "Media Organizer should move all selected media files.",
    )

    media_organizer.restore_media_from_manifest(move_result["manifest"])

    assert_condition((root / "song.mp3").exists(), "song.mp3 should restore.")
    assert_condition((root / "video.mp4").exists(), "video.mp4 should restore.")
    assert_condition((root / "sub" / "clip.mkv").exists(), "clip.mkv should restore.")

    return {
        "scan_count": len(files),
        "moved_count": move_result["moved_count"],
        "manifest": move_result["manifest"],
    }


def test_empty_folder_finder_fake_delete(sandbox: Path) -> dict[str, Any]:
    root = sandbox / "empty"
    (root / "empty_a").mkdir(parents=True)
    (root / "empty_b").mkdir(parents=True)
    write_text(root / "not_empty" / "keep.txt", "keep")

    folders = empty_folder_finder.find_empty_folders(str(root))
    names = sorted(Path(item["path"]).name for item in folders)

    assert_condition(
        names == ["empty_a", "empty_b"],
        "Empty Folder Finder should not include non-empty folders.",
    )

    def fake_safe_delete(path: str | Path) -> dict[str, Any]:
        return {
            "path": str(path),
            "risk": "review_required",
            "reason": "Behavior test fake delete.",
            "status": "deleted",
        }

    with patch("builtins.input", side_effect=["review", "y", "y"]):
        with patch.object(empty_folder_finder, "safe_delete", side_effect=fake_safe_delete):
            empty_folder_finder.delete_empty_folders(folders)

    assert_condition(
        (root / "empty_a").exists() and (root / "empty_b").exists(),
        "Behavior test should fake delete without moving folders to Recycle Bin.",
    )

    return {
        "found_count": len(folders),
        "fake_deleted_count": len(folders),
    }


def test_restore_missing_manifest(sandbox: Path) -> dict[str, Any]:
    result = restore_from_manifest(sandbox / "missing_manifest.json")

    assert_condition(
        result["status"] == "missing",
        "Missing manifest should return missing status.",
    )

    return result


def test_startup_launcher_config_audit(sandbox: Path) -> dict[str, Any]:
    original_config_dir = startup_launcher.CONFIG_DIR
    original_config_file = startup_launcher.CONFIG_FILE

    try:
        startup_launcher.CONFIG_DIR = sandbox / "startup_config"
        startup_launcher.CONFIG_FILE = startup_launcher.CONFIG_DIR / "startup_profiles.json"

        result = startup_launcher.add_app_to_profile(
            profile_name="behavior",
            app_name="Fake App",
            app_path="fake-app.exe",
            args=["--dry-run"],
        )
        profiles = startup_launcher.load_profiles()

    finally:
        startup_launcher.CONFIG_DIR = original_config_dir
        startup_launcher.CONFIG_FILE = original_config_file

    assert_condition(
        "behavior" in profiles,
        "Startup Launcher should create the requested profile.",
    )
    assert_condition(
        profiles["behavior"][0]["path"] == "fake-app.exe",
        "Startup Launcher should persist app path in sandbox config.",
    )
    assert_condition(
        result["profile_app_count"] == 1,
        "Startup Launcher should report profile app count.",
    )

    return {
        "profile": "behavior",
        "profile_app_count": result["profile_app_count"],
        "config_file": result["config_file"],
    }


def test_read_only_system_snapshots(sandbox: Path) -> dict[str, Any]:
    disks = get_disk_info()
    processes = get_top_processes(limit=5, sort_by="ram")

    assert_condition(
        isinstance(disks, list),
        "Disk Checker snapshot should return a list.",
    )
    assert_condition(
        isinstance(processes, list),
        "Process Monitor snapshot should return a list.",
    )
    assert_condition(
        len(processes) <= 5,
        "Process Monitor should respect the requested limit.",
    )

    if disks:
        required_disk_keys = {"device", "mountpoint", "total", "used", "free", "percent", "status"}
        assert_condition(
            required_disk_keys.issubset(disks[0]),
            "Disk snapshot should include required keys.",
        )

    if processes:
        required_process_keys = {"pid", "name", "cpu_percent", "memory_bytes", "memory_percent"}
        assert_condition(
            required_process_keys.issubset(processes[0]),
            "Process snapshot should include required keys.",
        )

    return {
        "disk_count": len(disks),
        "process_count": len(processes),
    }


def test_config_system_snapshot(sandbox: Path) -> dict[str, Any]:
    validation = validate_user_settings()

    assert_condition(
        USER_SETTINGS_FILE.exists(),
        "User settings file should exist.",
    )
    assert_condition(
        validation["status"] == "valid",
        "User settings should validate with default config.",
    )

    return validation


def test_audit_center_snapshot(sandbox: Path) -> dict[str, Any]:
    snapshot = get_audit_snapshot(limit=20)

    assert_condition(
        isinstance(snapshot["logs"], list),
        "Audit Center should return logs as a list.",
    )
    assert_condition(
        isinstance(snapshot["reports"], list),
        "Audit Center should return report index as a list.",
    )
    assert_condition(
        "log_count" in snapshot and "report_count" in snapshot,
        "Audit Center snapshot should include counts.",
    )

    return {
        "log_count": snapshot["log_count"],
        "report_count": snapshot["report_count"],
    }


def test_undo_manager_roundtrip(sandbox: Path) -> dict[str, Any]:
    root = sandbox / "undo"
    source = root / "original" / "undo_me.txt"
    moved_target = root / "moved" / "undo_me.txt"

    write_text(source, "undo test")
    move_record = safe_move(source, moved_target)
    manifest = save_manifest("undo_manager_behavior_test", [move_record])

    preview = preview_manifest(manifest)
    assert_condition(
        preview["restorable_count"] == 1,
        "Undo Manager preview should find one restorable record.",
    )

    result = restore_manifest(manifest)
    assert_condition(
        result["status"] == "success",
        "Undo Manager restore should return success.",
    )
    assert_condition(
        result["restored_count"] == 1,
        "Undo Manager should restore one file.",
    )
    assert_condition(
        source.exists(),
        "Undo Manager should restore file to original path.",
    )
    assert_condition(
        not Path(move_record["new_path"]).exists(),
        "Moved path should no longer exist after restore.",
    )

    return {
        "manifest": str(manifest),
        "restored_count": result["restored_count"],
        "report": result["report"],
    }


def test_natural_command_router(sandbox: Path) -> dict[str, Any]:
    disk_route = natural_command.resolve_command("check disk")
    accented_disk_route = natural_command.resolve_command("ki\u1ec3m tra \u1ed5 c\u1ee9ng")
    search_route = natural_command.resolve_command("find naruto")
    cache_route = natural_command.resolve_command("don cache")
    full_test_route = natural_command.resolve_command("test tong")
    recommendation_route = natural_command.resolve_command("recommendation")
    queue_preview_route = natural_command.resolve_command("xem goi y")
    queue_open_route = natural_command.resolve_command("lam goi y so 1")
    queue_defer_route = natural_command.resolve_command("hoan muc 2")
    queue_handled_route = natural_command.resolve_command("danh dau muc 3 da xu ly")
    guided_route = natural_command.resolve_command("lam goi y")
    unknown_route = natural_command.resolve_command("khong hieu lenh nay")

    assert_condition(
        disk_route["type"] == "capability"
        and disk_route["capability"]["id"] == "disk_checker",
        "Natural Command should route check disk to Disk Checker.",
    )
    assert_condition(
        accented_disk_route["type"] == "capability"
        and accented_disk_route["capability"]["id"] == "disk_checker",
        "Natural Command should normalize Vietnamese accents.",
    )
    assert_condition(
        search_route["type"] == "search"
        and search_route["query"] == "naruto",
        "Natural Command should keep find <keyword> search behavior.",
    )
    assert_condition(
        cache_route["type"] == "capability"
        and cache_route["capability"]["id"] == "browser_cache_cleaner",
        "Natural Command should route cache cleanup.",
    )
    assert_condition(
        full_test_route["type"] == "capability"
        and full_test_route["capability"]["id"] == "full_system_tester",
        "Natural Command should route full system test.",
    )
    assert_condition(
        recommendation_route["type"] == "capability"
        and recommendation_route["capability"]["id"] == "recommendation_center",
        "Natural Command should route Recommendation Center.",
    )
    assert_condition(
        queue_preview_route["type"] == "recommendation_queue_preview",
        "Natural Command v3 should preview recommendation queue.",
    )
    assert_condition(
        queue_open_route["type"] == "recommendation_open"
        and queue_open_route["index"] == 1,
        "Natural Command v3 should route recommendation open by index.",
    )
    assert_condition(
        queue_defer_route["type"] == "recommendation_state_update"
        and queue_defer_route["index"] == 2
        and queue_defer_route["state"] == "deferred",
        "Natural Command v3 should route deferred state update.",
    )
    assert_condition(
        queue_handled_route["type"] == "recommendation_state_update"
        and queue_handled_route["index"] == 3
        and queue_handled_route["state"] == "handled",
        "Natural Command v3 should route handled state update.",
    )
    assert_condition(
        guided_route["type"] == "capability"
        and guided_route["capability"]["id"] == "guided_action_runner",
        "Natural Command should route Guided Action Runner.",
    )
    assert_condition(
        unknown_route["type"] == "unknown",
        "Natural Command should return unknown for unsupported commands.",
    )
    assert_condition(
        not natural_command.requires_confirmation(disk_route["capability"]),
        "Safe read-only commands should not require Natural Command confirmation.",
    )
    assert_condition(
        natural_command.requires_confirmation(cache_route["capability"]),
        "Mutating or risky commands should require Natural Command confirmation.",
    )
    assert_condition(
        natural_command.requires_confirmation(guided_route["capability"]),
        "Guided Action Runner should require Natural Command confirmation.",
    )

    return {
        "disk_route": disk_route["capability"]["id"],
        "search_query": search_route["query"],
        "cache_route": cache_route["capability"]["id"],
        "full_test_route": full_test_route["capability"]["id"],
        "recommendation_route": recommendation_route["capability"]["id"],
        "queue_preview_type": queue_preview_route["type"],
        "queue_open_index": queue_open_route["index"],
        "guided_route": guided_route["capability"]["id"],
        "unknown_type": unknown_route["type"],
    }


def test_system_advisor_v2_recommendations(sandbox: Path) -> dict[str, Any]:
    top_folders = [
        {
            "path": str(sandbox / "Downloads"),
            "size": 10 * 1024 * 1024 * 1024,
            "source": "test",
        }
    ]
    large_files = [
        {
            "path": str(sandbox / "Downloads" / "installer.zip"),
            "size": 2 * 1024 * 1024 * 1024,
            "extension": ".zip",
        },
        {
            "path": str(sandbox / "Media" / "clip.mp4"),
            "size": 3 * 1024 * 1024 * 1024,
            "extension": ".mp4",
        },
    ]
    processes = [
        {
            "pid": 1,
            "name": "chrome.exe",
            "cpu_percent": 2.0,
            "memory_bytes": 900 * 1024 * 1024,
            "memory_percent": 9.0,
            "system_memory_percent": 90.0,
        }
    ]
    disk_snapshot = {
        "disks": [
            {
                "device": "D:",
                "mountpoint": "D:\\",
                "percent": 92.0,
                "free": 8 * 1024 * 1024 * 1024,
                "status": "critical",
            }
        ],
        "smart_health": {
            "devices": [
                {
                    "device": "/dev/sda",
                    "smart_passed": False,
                }
            ]
        },
    }
    external_apps = {
        "enabled": True,
        "total": 2,
        "available": 1,
        "missing": 1,
        "apps": [
            {"name": "everything_cli", "available": True},
            {"name": "ffmpeg", "available": False},
        ],
    }
    audit_snapshot = {
        "log_count": 0,
        "report_count": 1,
        "reports": [
            {
                "tool": "fake_tool",
                "status": "error",
            }
        ],
    }

    result = system_advisor.build_system_advisor_result(
        root_drive=str(sandbox),
        storage_provider="python",
        wiztree_status="skipped",
        storage_scan_report=None,
        top_folders=top_folders,
        large_files=large_files,
        processes=processes,
        disk_snapshot=disk_snapshot,
        external_apps=external_apps,
        audit_snapshot=audit_snapshot,
    )

    recommendation_ids = {
        item["id"]
        for item in result["recommendations"]
    }
    severities = [
        item["severity"]
        for item in result["recommendations"]
    ]

    expected_ids = {
        "smart-health-failed",
        "ram-critical",
        "downloads-folder-heavy",
        "large-archive-files",
        "large-video-files",
        "external-apps-missing",
        "recent-report-issues",
    }

    assert_condition(
        expected_ids.issubset(recommendation_ids),
        f"System Advisor v2 missing expected recommendations: {expected_ids - recommendation_ids}",
    )
    assert_condition(
        severities == sorted(
            severities,
            key=lambda severity: system_advisor.SEVERITY_ORDER[severity],
        ),
        "System Advisor v2 recommendations should be sorted by severity.",
    )
    assert_condition(
        result["recommendation_summary"]["critical_count"] >= 2,
        "System Advisor v2 should count critical recommendations.",
    )
    assert_condition(
        all(item["suggestion_only"] for item in result["recommendations"]),
        "System Advisor v2 must only suggest actions, not execute them.",
    )

    return {
        "recommendation_count": len(result["recommendations"]),
        "summary": result["recommendation_summary"],
        "recommendation_ids": sorted(recommendation_ids),
    }


def test_recommendation_center_queue(sandbox: Path) -> dict[str, Any]:
    create_report(
        tool_name="system_advisor",
        action="analyze_system_v2",
        status="success",
        risk_level="safe",
        input_data={
            "sandbox": str(sandbox),
        },
        results={
            "recommendations": [
                {
                    "id": "behavior-recommendation-center",
                    "severity": "warning",
                    "title": "Behavior recommendation",
                    "detail": "Recommendation Center should collect Advisor recommendations.",
                    "source": "behavior_test",
                    "suggested_tool_id": "audit_center",
                    "suggestion_only": True,
                }
            ],
        },
        recommendations=[
            "[WARNING] Behavior recommendation.",
        ],
        summary={
            "total": 1,
            "warning_count": 1,
            "undo_available": False,
        },
        undo_available=False,
        tags=["system_advisor", "read_only", "v2", "behavior_test"],
    )

    queue = recommendation_center.collect_recommendation_queue(report_limit=15)
    summary = recommendation_center.summarize_recommendation_queue(queue)
    matching = [
        item for item in queue
        if item["id"] == "behavior-recommendation-center"
    ]

    assert_condition(matching, "Recommendation Center should collect System Advisor v2 recommendations.")
    assert_condition(
        matching[-1]["suggested_tool_name"] == "Audit Center",
        "Recommendation Center should enrich suggested tool metadata.",
    )
    assert_condition(
        all(item["suggestion_only"] for item in queue),
        "Recommendation Center should stay read-only/suggestion-only.",
    )

    return {
        "queue_count": len(queue),
        "summary": summary,
        "matched": matching[-1],
    }


def test_recommendation_workflow_state_transitions(sandbox: Path) -> dict[str, Any]:
    state_file = sandbox / "recommendation_queue.jsonl"
    seed = sandbox.name

    create_report(
        tool_name="system_advisor",
        action="workflow_state_test",
        status="success",
        risk_level="safe",
        input_data={
            "sandbox": str(sandbox),
        },
        results={
            "recommendations": [
                {
                    "id": f"workflow-deferred-{seed}",
                    "severity": "warning",
                    "title": "Workflow deferred",
                    "detail": f"Recommendation workflow deferred test {seed}.",
                    "source": "behavior_test",
                    "suggested_tool_id": "audit_center",
                    "suggestion_only": True,
                },
                {
                    "id": f"workflow-handled-{seed}",
                    "severity": "info",
                    "title": "Workflow handled",
                    "detail": f"Recommendation workflow handled test {seed}.",
                    "source": "behavior_test",
                    "suggested_tool_id": "audit_center",
                    "suggestion_only": True,
                },
                {
                    "id": f"workflow-ignored-{seed}",
                    "severity": "info",
                    "title": "Workflow ignored",
                    "detail": f"Recommendation workflow ignored test {seed}.",
                    "source": "behavior_test",
                    "suggested_tool_id": "audit_center",
                    "suggestion_only": True,
                },
            ],
        },
        recommendations=[],
        summary={
            "total": 3,
            "undo_available": False,
        },
        undo_available=False,
        tags=["recommendation_workflow", "behavior_test"],
    )

    sync_result = recommendation_center.sync_recommendation_queue(
        report_limit=20,
        state_file=state_file,
        states=None,
    )
    matching = {
        item["id"]: item
        for item in sync_result["all_queue"]
        if str(item["id"]).endswith(seed)
    }

    assert_condition(
        len(matching) == 3,
        "Recommendation workflow test should collect three seeded recommendations.",
    )
    assert_condition(
        state_file.exists(),
        "Recommendation workflow should persist state events to jsonl.",
    )

    recommendation_center.update_recommendation_state(
        matching[f"workflow-deferred-{seed}"]["fingerprint"],
        "deferred",
        note="behavior defer",
        state_file=state_file,
    )
    recommendation_center.update_recommendation_state(
        matching[f"workflow-handled-{seed}"]["fingerprint"],
        "handled",
        note="behavior handled",
        state_file=state_file,
    )
    recommendation_center.update_recommendation_state(
        matching[f"workflow-ignored-{seed}"]["fingerprint"],
        "ignored",
        note="behavior ignored",
        state_file=state_file,
    )

    all_queue = recommendation_center.collect_recommendation_queue(
        report_limit=20,
        state_file=state_file,
        states=None,
    )
    seeded = [
        item for item in all_queue
        if str(item["id"]).endswith(seed)
    ]
    summary = recommendation_center.summarize_recommendation_queue(seeded)
    visible = recommendation_center.collect_recommendation_queue(
        report_limit=20,
        state_file=state_file,
        states=recommendation_center.DEFAULT_VISIBLE_STATES,
    )
    visible_seeded = [
        item for item in visible
        if str(item["id"]).endswith(seed)
    ]

    assert_condition(summary["deferred_count"] == 1, "Deferred state should be counted.")
    assert_condition(summary["handled_count"] == 1, "Handled state should be counted.")
    assert_condition(summary["ignored_count"] == 1, "Ignored state should be counted.")
    assert_condition(
        len(visible_seeded) == 1 and visible_seeded[0]["workflow_state"] == "deferred",
        "Default visible queue should include deferred but hide handled/ignored.",
    )

    return {
        "state_file": str(state_file),
        "summary": summary,
        "visible_seeded_count": len(visible_seeded),
    }


def test_guided_action_runner_contract(sandbox: Path) -> dict[str, Any]:
    state_file = sandbox / "guided_action_queue.jsonl"
    seed = sandbox.name
    recommendation_id = f"guided-action-{seed}"

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
                    "title": "Guided action contract",
                    "detail": f"Guided runner should open this recommendation in dry-run only {seed}.",
                    "source": "behavior_test",
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
        tags=["guided_action", "behavior_test"],
    )

    preview = guided_action_runner.preview_guided_actions(
        report_limit=30,
        state_file=state_file,
    )
    context = guided_action_runner.find_guided_action_context(
        preview["contexts"],
        recommendation_id=recommendation_id,
    )

    assert_condition(context is not None, "Guided Action Runner should find seeded recommendation.")
    assert_condition(context["status"] == "ready", "Guided action context should be ready.")
    assert_condition(
        context["capability"]["id"] == "download_organizer",
        "Guided Action Runner should resolve suggested capability.",
    )
    assert_condition(
        context["capability"]["mutates_files"] is True,
        "Guided Action Runner should expose target mutating metadata.",
    )
    assert_condition(
        context["target_requires_confirmation"] is True,
        "Guided Action Runner should detect target confirmation requirement.",
    )

    dry_run = guided_action_runner.execute_guided_action(context, dry_run=True)
    assert_condition(dry_run["status"] == "dry_run", "Guided dry-run should not execute the target tool.")
    assert_condition(dry_run["executed"] is False, "Guided dry-run must not execute target tool.")
    assert_condition(Path(dry_run["report"]).exists(), "Guided dry-run should create a report.")

    handled_queue = recommendation_center.collect_recommendation_queue(
        report_limit=30,
        state_file=state_file,
        states={"handled"},
    )
    assert_condition(
        not any(item["id"] == recommendation_id for item in handled_queue),
        "Guided dry-run should not mark recommendation handled automatically.",
    )

    return {
        "recommendation_id": recommendation_id,
        "target_tool": context["capability"]["id"],
        "dry_run_report": dry_run["report"],
        "ready_count": preview["ready_count"],
    }


def test_natural_command_v3_queue_actions(sandbox: Path) -> dict[str, Any]:
    state_file = sandbox / "natural_command_v3_queue.jsonl"
    seed = sandbox.name
    recommendation_id = f"natural-command-v3-{seed}"

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
                    "title": "Natural command v3 contract",
                    "detail": f"Natural Command should control this queue item {seed}.",
                    "source": "behavior_test",
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
        tags=["natural_command_v3", "behavior_test"],
    )

    preview = guided_action_runner.preview_guided_actions(
        report_limit=30,
        state_file=state_file,
    )
    context = guided_action_runner.find_guided_action_context(
        preview["contexts"],
        recommendation_id=recommendation_id,
    )
    assert_condition(context is not None, "Natural Command v3 should have a seeded queue item.")

    index = preview["contexts"].index(context) + 1
    dry_run = natural_command.run_recommendation_open_command(
        index,
        report_limit=30,
        state_file=state_file,
        dry_run=True,
        require_confirmation=False,
    )
    assert_condition(dry_run["status"] == "dry_run", "Natural Command v3 open should support dry-run.")
    assert_condition(dry_run["executed"] is False, "Natural Command v3 dry-run should not execute target tool.")

    deferred = natural_command.run_recommendation_state_command(
        index,
        "deferred",
        report_limit=30,
        state_file=state_file,
    )
    assert_condition(deferred["status"] == "success", "Natural Command v3 should defer by index.")

    deferred_queue = recommendation_center.collect_recommendation_queue(
        report_limit=30,
        state_file=state_file,
        states={"deferred"},
    )
    assert_condition(
        any(item["id"] == recommendation_id for item in deferred_queue),
        "Natural Command v3 state update should persist deferred state.",
    )

    handled = natural_command.run_recommendation_state_command(
        index,
        "handled",
        report_limit=30,
        state_file=state_file,
    )
    assert_condition(handled["status"] == "success", "Natural Command v3 should mark handled by index.")

    visible = recommendation_center.collect_recommendation_queue(
        report_limit=30,
        state_file=state_file,
        states=recommendation_center.DEFAULT_VISIBLE_STATES,
    )
    assert_condition(
        not any(item["id"] == recommendation_id and item["workflow_state"] == "handled" for item in visible),
        "Handled recommendation should be hidden from default visible queue.",
    )

    return {
        "recommendation_id": recommendation_id,
        "index": index,
        "dry_run_report": dry_run["report"],
        "deferred_state": deferred["state"],
        "handled_state": handled["state"],
    }


def test_external_apps_health_v2_contract(sandbox: Path) -> dict[str, Any]:
    health = external_apps.build_external_apps_health(include_versions=False)
    apps_by_name = {
        item["name"]: item
        for item in health["apps"]
    }

    required_apps = {
        "everything_cli": "file_indexer",
        "everything_app": "natural_command",
        "wiztree": "system_advisor",
        "smartctl": "disk_checker",
        "ffprobe": "media_organizer",
        "exiftool": "media_organizer",
    }

    for app_name, expected_tool_id in required_apps.items():
        assert_condition(
            app_name in apps_by_name,
            f"External Apps Health v2 should include {app_name}.",
        )
        dependent_tool_ids = {
            tool["id"]
            for tool in apps_by_name[app_name]["dependent_tools"]
        }
        assert_condition(
            expected_tool_id in dependent_tool_ids,
            f"{app_name} should map to dependent tool {expected_tool_id}.",
        )

    assert_condition(
        health["schema"] == "external_apps_health_v2",
        "External Apps Health should expose v2 schema marker.",
    )
    assert_condition(
        health["summary"]["total"] == len(health["apps"]),
        "External Apps Health summary total should match app list.",
    )

    return {
        "summary": health["summary"],
        "checked_apps": sorted(required_apps),
        "impacted_tool_ids": health["impacted_tool_ids"],
    }


def run_single_test(
    name: str,
    test_func: Callable[[Path], dict[str, Any]],
    sandbox: Path,
) -> dict[str, Any]:
    try:
        details = test_func(sandbox)
        print(f"[PASS] {name}")
        return {
            "name": name,
            "status": "pass",
            "details": details,
        }

    except Exception as error:
        print(f"[FAIL] {name} -> {error}")
        return {
            "name": name,
            "status": "fail",
            "error": str(error),
        }


def run_behavior_tester() -> None:
    sandbox = make_sandbox()

    tests: list[tuple[str, Callable[[Path], dict[str, Any]]]] = [
        ("Risk Classifier and Safe Delete", test_risk_classifier_and_safe_delete),
        ("Download Organizer Roundtrip", test_download_organizer_roundtrip),
        ("Download Watcher Startup Scan", test_download_watcher_startup_scan),
        ("Media Organizer Roundtrip", test_media_organizer_roundtrip),
        ("Empty Folder Finder Fake Delete", test_empty_folder_finder_fake_delete),
        ("Missing Manifest Restore", test_restore_missing_manifest),
        ("Startup Launcher Config Audit", test_startup_launcher_config_audit),
        ("Read-only System Snapshots", test_read_only_system_snapshots),
        ("Config System Snapshot", test_config_system_snapshot),
        ("Audit Center Snapshot", test_audit_center_snapshot),
        ("Undo Manager Roundtrip", test_undo_manager_roundtrip),
        ("Natural Command Router", test_natural_command_router),
        ("System Advisor v2 Recommendations", test_system_advisor_v2_recommendations),
        ("Recommendation Center Queue", test_recommendation_center_queue),
        ("Recommendation Workflow State Transitions", test_recommendation_workflow_state_transitions),
        ("Guided Action Runner Contract", test_guided_action_runner_contract),
        ("Natural Command v3 Queue Actions", test_natural_command_v3_queue_actions),
        ("External Apps Health v2 Contract", test_external_apps_health_v2_contract),
    ]

    results = []
    cleanup_error = None

    print("\n========== BEHAVIOR TESTER ==========")
    print(f"Sandbox: {sandbox}")

    try:
        for name, test_func in tests:
            results.append(run_single_test(name, test_func, sandbox))

    finally:
        try:
            cleanup_sandbox(sandbox)
        except Exception as error:
            cleanup_error = str(error)

    passed = sum(1 for item in results if item["status"] == "pass")
    failed = sum(1 for item in results if item["status"] == "fail")
    status = "success" if failed == 0 and cleanup_error is None else "error"

    report = create_report(
        tool_name="behavior_tester",
        status=status,
        input_data={
            "sandbox": str(sandbox),
        },
        results={
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "cleanup_error": cleanup_error,
            "tests": results,
        },
        recommendations=[
            "Behavior tests use sandbox data only.",
            "These tests do not empty Recycle Bin or touch real Downloads.",
            "Add new regression tests before changing cleanup or move flows.",
        ],
    )

    print("\n========== BEHAVIOR SUMMARY ==========")
    print(f"Total : {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    if cleanup_error:
        print(f"Cleanup error: {cleanup_error}")
    print(f"Report: {report}")


if __name__ == "__main__":
    run_behavior_tester()
