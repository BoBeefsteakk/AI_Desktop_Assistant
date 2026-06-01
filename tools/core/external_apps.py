from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import (
    DATA_DIR,
    EXTERNAL_APP_PATHS,
    EXTERNAL_APP_TIMEOUT_SECONDS,
    EXTERNAL_APPS_ENABLED,
    WIZTREE_ENABLED,
    WIZTREE_EXE_PATH,
)
from tools.core.assistant_logger import log_action
from tools.core.capability_registry import get_capabilities
from tools.core.report_manager import create_report


VERSION_COMMANDS: dict[str, list[str]] = {
    "everything_cli": ["-version"],
    "ffmpeg": ["-version"],
    "ffprobe": ["-version"],
    "exiftool": ["-ver"],
    "rclone": ["version"],
    "smartctl": ["--version"],
    "seven_zip": ["i"],
}

APP_IMPACT_DESCRIPTIONS: dict[str, str] = {
    "everything_app": "Everything service/app giup Everything CLI tra ket qua nhanh va day du.",
    "everything_cli": "File search va Natural Command se fallback cham hon neu thieu CLI.",
    "wiztree": "Storage scan se fallback sang Python scanner, cham hon tren o lon.",
    "smartctl": "Disk Checker va Advisor mat SMART health/temperature.",
    "crystaldiskinfo": "Chi con SMART CLI qua smartctl, mat GUI helper de doi chieu nhanh.",
    "exiftool": "Media metadata mat EXIF/container tag chi tiet.",
    "ffmpeg": "Chua dung truc tiep trong flow chinh, nhung can cho xu ly media sau nay.",
    "ffprobe": "Media metadata mat duration/codec/resolution chuan.",
    "seven_zip": "Archive validation/extract workflow sau nay se bi giam chat luong.",
    "rclone": "Backup/sync cloud sau nay chua san sang.",
    "sysinternals_autoruns": "Startup diagnostics sau nay mat autoruns CLI.",
    "sysinternals_handle": "Process/file-lock diagnostics mat Handle helper.",
    "sysinternals_procexp": "Process diagnostics mat Process Explorer helper.",
    "sysinternals_rammap": "RAM diagnostics mat RAMMap helper.",
    "sysinternals_du": "Disk usage diagnostics mat DU helper.",
    "sysinternals_sigcheck": "Signature/security diagnostics mat Sigcheck helper.",
}

INDIRECT_APP_DEPENDENCIES: dict[str, list[str]] = {
    "everything_app": ["file_indexer", "natural_command"],
}
EXTERNAL_APPS_HEALTH_STATE_FILE = DATA_DIR / "external_apps_health_state.json"


def get_external_app_path(app_name: str) -> Path | None:
    if app_name == "wiztree":
        return WIZTREE_EXE_PATH
    return EXTERNAL_APP_PATHS.get(app_name)


def is_external_app_available(app_name: str) -> bool:
    path = get_external_app_path(app_name)
    if app_name == "wiztree":
        return bool(WIZTREE_ENABLED and path and path.exists())
    return bool(EXTERNAL_APPS_ENABLED and path and path.exists())


def get_configured_external_app_paths() -> dict[str, Path]:
    paths = dict(EXTERNAL_APP_PATHS)
    paths.setdefault("wiztree", WIZTREE_EXE_PATH)
    return paths


def get_external_app_enabled(app_name: str) -> bool:
    if app_name == "wiztree":
        return WIZTREE_ENABLED
    return EXTERNAL_APPS_ENABLED


def run_external_app(
    app_name: str,
    args: list[str],
    *,
    timeout: int | None = None,
) -> dict[str, Any]:
    path = get_external_app_path(app_name)

    if not get_external_app_enabled(app_name):
        return {
            "status": "disabled",
            "app": app_name,
        }

    if not path or not path.exists():
        return {
            "status": "missing",
            "app": app_name,
            "path": str(path) if path else None,
        }

    command = [str(path), *args]

    try:
        completed = subprocess.run(
            command,
            cwd=str(path.parent),
            text=True,
            capture_output=True,
            timeout=timeout or EXTERNAL_APP_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "app": app_name,
            "path": str(path),
            "command": command,
            "error": str(exc),
        }
    except OSError as exc:
        return {
            "status": "error",
            "app": app_name,
            "path": str(path),
            "command": command,
            "error": str(exc),
        }

    return {
        "status": "success" if completed.returncode == 0 else "error",
        "app": app_name,
        "path": str(path),
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def first_output_line(result: dict[str, Any]) -> str | None:
    stdout = str(result.get("stdout") or "").strip()
    stderr = str(result.get("stderr") or "").strip()
    text = stdout or stderr
    if not text:
        return None
    return text.splitlines()[0].strip()


def get_external_app_version(app_name: str) -> str | None:
    if app_name == "everything_app":
        if not is_external_app_available("everything_cli"):
            return None
        result = run_external_app("everything_cli", ["-get-everything-version"], timeout=10)
        return first_output_line(result) if result["status"] == "success" else None

    args = VERSION_COMMANDS.get(app_name)
    if not args:
        return None

    result = run_external_app(app_name, args, timeout=10)
    return first_output_line(result) if result["status"] == "success" else None


def get_external_apps_status(include_versions: bool = False) -> dict[str, Any]:
    apps = []

    for app_name, path in sorted(get_configured_external_app_paths().items()):
        enabled = get_external_app_enabled(app_name)
        path_exists = path.exists()
        record = {
            "name": app_name,
            "path": str(path),
            "enabled": enabled,
            "available": enabled and path_exists,
            "path_exists": path_exists,
        }
        if path_exists:
            try:
                stat = path.stat()
                record.update({
                    "path_size": stat.st_size,
                    "path_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                })
            except OSError:
                record.update({
                    "path_size": None,
                    "path_modified": None,
                })
        if include_versions and record["available"]:
            record["version"] = get_external_app_version(app_name)
        apps.append(record)

    available_count = sum(1 for item in apps if item["available"])

    return {
        "enabled": EXTERNAL_APPS_ENABLED,
        "total": len(apps),
        "available": available_count,
        "missing": len(apps) - available_count,
        "apps": apps,
    }


def get_external_app_dependency_map() -> dict[str, list[dict[str, Any]]]:
    dependency_map: dict[str, list[dict[str, Any]]] = {}
    capabilities_by_id = {item["id"]: item for item in get_capabilities()}

    for capability in capabilities_by_id.values():
        for app_name in capability.get("external_apps", []):
            dependency_map.setdefault(app_name, []).append({
                "id": capability["id"],
                "name": capability["name"],
                "category": capability["category"],
                "risk_level": capability["risk_level"],
                "mutates_files": capability["mutates_files"],
                "needs_confirmation": capability["needs_confirmation"],
            })

    for app_name, capability_ids in INDIRECT_APP_DEPENDENCIES.items():
        for capability_id in capability_ids:
            capability = capabilities_by_id.get(capability_id)
            if capability is None:
                continue
            dependency_map.setdefault(app_name, []).append({
                "id": capability["id"],
                "name": capability["name"],
                "category": capability["category"],
                "risk_level": capability["risk_level"],
                "mutates_files": capability["mutates_files"],
                "needs_confirmation": capability["needs_confirmation"],
                "relation": "indirect",
            })

    for app_name, dependent_tools in dependency_map.items():
        seen = set()
        unique_tools = []
        for tool in dependent_tools:
            if tool["id"] in seen:
                continue
            seen.add(tool["id"])
            unique_tools.append(tool)
        dependency_map[app_name] = sorted(unique_tools, key=lambda item: item["id"])

    return dependency_map


def build_external_app_recommendations(health: dict[str, Any]) -> list[dict[str, Any]]:
    recommendations = []

    for app in health["apps"]:
        if app["state"] == "available":
            continue

        dependent_tool_ids = [tool["id"] for tool in app["dependent_tools"]]
        severity = "warning" if dependent_tool_ids else "info"

        if app["state"] == "disabled":
            title = "External app dang bi disable"
            detail = (
                f"{app['name']} dang bi disable. "
                f"Anh huong tool: {', '.join(dependent_tool_ids) or 'chua co tool phu thuoc truc tiep'}."
            )
        elif app["state"] == "unconfigured":
            title = "External app chua co path cau hinh"
            detail = (
                f"{app['name']} duoc capability registry nhac toi nhung chua co path cau hinh. "
                f"Anh huong tool: {', '.join(dependent_tool_ids) or 'chua ro'}."
            )
        else:
            title = "External app bi thieu hoac sai path"
            detail = (
                f"{app['name']} khong tim thay tai {app.get('path') or '<missing path>'}. "
                f"Anh huong tool: {', '.join(dependent_tool_ids) or 'chua co tool phu thuoc truc tiep'}."
            )

        recommendations.append({
            "id": f"external-app-{app['name']}-{app['state']}",
            "severity": severity,
            "title": title,
            "detail": detail,
            "source": "external_apps",
            "app_name": app["name"],
            "state": app["state"],
            "dependent_tool_ids": dependent_tool_ids,
            "suggested_tool_id": "external_apps_manager",
            "suggestion_only": True,
        })

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(
        recommendations,
        key=lambda item: (severity_order.get(item["severity"], 99), item["id"]),
    )


def build_external_apps_health_state(health: dict[str, Any]) -> dict[str, Any]:
    apps = {}

    for app in health.get("apps", []):
        apps[app["name"]] = {
            "name": app["name"],
            "path": app.get("path"),
            "enabled": bool(app.get("enabled")),
            "available": bool(app.get("available")),
            "state": app.get("state"),
            "version": app.get("version"),
            "path_size": app.get("path_size"),
            "path_modified": app.get("path_modified"),
        }

    return {
        "schema": "external_apps_health_state_v1",
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "apps": apps,
    }


def load_external_apps_health_state(
    state_file: str | Path | None = None,
) -> dict[str, Any] | None:
    path = Path(state_file) if state_file is not None else EXTERNAL_APPS_HEALTH_STATE_FILE
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def save_external_apps_health_state(
    health: dict[str, Any],
    state_file: str | Path | None = None,
) -> Path:
    path = Path(state_file) if state_file is not None else EXTERNAL_APPS_HEALTH_STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    state = build_external_apps_health_state(health)

    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)

    return path


def normalize_previous_apps(previous_state: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not previous_state:
        return {}

    apps = previous_state.get("apps", {})
    if isinstance(apps, dict):
        return {
            str(name): item
            for name, item in apps.items()
            if isinstance(item, dict)
        }

    if isinstance(apps, list):
        return {
            str(item.get("name")): item
            for item in apps
            if isinstance(item, dict) and item.get("name")
        }

    return {}


def make_external_app_drift_event(
    app: dict[str, Any],
    drift_type: str,
    severity: str,
    title: str,
    detail: str,
    previous: dict[str, Any],
) -> dict[str, Any]:
    dependent_tool_ids = [tool["id"] for tool in app.get("dependent_tools", [])]
    return {
        "id": f"external-app-{app['name']}-{drift_type}",
        "severity": severity,
        "title": title,
        "detail": detail,
        "source": "external_apps_drift",
        "app_name": app["name"],
        "state": app.get("state"),
        "drift_type": drift_type,
        "previous": previous,
        "current": {
            "path": app.get("path"),
            "available": bool(app.get("available")),
            "state": app.get("state"),
            "version": app.get("version"),
            "path_size": app.get("path_size"),
            "path_modified": app.get("path_modified"),
        },
        "dependent_tool_ids": dependent_tool_ids,
        "suggested_tool_id": "external_apps_manager",
        "suggestion_only": True,
    }


def detect_external_app_drift(
    health: dict[str, Any],
    previous_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    previous_apps = normalize_previous_apps(previous_state)
    if not previous_apps:
        return []

    events = []

    for app in health.get("apps", []):
        previous = previous_apps.get(app["name"])
        if not previous:
            continue

        previous_path = str(previous.get("path") or "")
        current_path = str(app.get("path") or "")
        previous_available = bool(previous.get("available"))
        current_available = bool(app.get("available"))
        dependent_tool_ids = [tool["id"] for tool in app.get("dependent_tools", [])]
        severity = "warning" if dependent_tool_ids else "info"

        if previous_path != current_path:
            events.append(make_external_app_drift_event(
                app,
                "path_changed",
                severity,
                "External app path da doi",
                (
                    f"{app['name']} doi path tu {previous_path or '<missing>'} "
                    f"sang {current_path or '<missing>'}. "
                    f"Anh huong tool: {', '.join(dependent_tool_ids) or 'chua co tool phu thuoc truc tiep'}."
                ),
                previous,
            ))

        if previous_available != current_available:
            state_text = "available" if current_available else "missing"
            events.append(make_external_app_drift_event(
                app,
                "availability_changed",
                severity,
                "External app availability da doi",
                (
                    f"{app['name']} chuyen tu "
                    f"{'available' if previous_available else 'missing'} sang {state_text}. "
                    f"Path hien tai: {current_path or '<missing>'}."
                ),
                previous,
            ))

        previous_version = previous.get("version")
        current_version = app.get("version")
        if previous_version and current_version and previous_version != current_version:
            events.append(make_external_app_drift_event(
                app,
                "version_changed",
                "info",
                "External app version da doi",
                (
                    f"{app['name']} doi version tu {previous_version} sang {current_version}. "
                    "Nen biet de doi chieu neu tool hanh xu khac truoc."
                ),
                previous,
            ))

        same_path = previous_path == current_path
        previous_size = previous.get("path_size")
        current_size = app.get("path_size")
        previous_modified = previous.get("path_modified")
        current_modified = app.get("path_modified")
        if (
            same_path
            and previous_available
            and current_available
            and (
                (previous_size is not None and current_size is not None and previous_size != current_size)
                or (
                    previous_modified
                    and current_modified
                    and previous_modified != current_modified
                )
            )
        ):
            events.append(make_external_app_drift_event(
                app,
                "binary_changed",
                "info",
                "External app file da thay doi",
                (
                    f"{app['name']} van o cung path nhung file size/modified da doi. "
                    "Co the do update app; neu tool loi, hay xem lai app nay truoc."
                ),
                previous,
            ))

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(events, key=lambda item: (severity_order.get(item["severity"], 99), item["id"]))


def external_app_recommendation_to_text(recommendation: dict[str, Any]) -> str:
    return (
        f"[{recommendation['severity'].upper()}] "
        f"{recommendation['title']}: {recommendation['detail']}"
    )


def build_external_apps_health(
    include_versions: bool = False,
    previous_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = get_external_apps_status(include_versions=include_versions)
    dependency_map = get_external_app_dependency_map()
    apps_by_name = {item["name"]: item for item in status["apps"]}
    all_app_names = sorted(set(apps_by_name) | set(dependency_map))
    apps = []

    for app_name in all_app_names:
        base = apps_by_name.get(app_name)
        dependent_tools = dependency_map.get(app_name, [])

        if base is None:
            record = {
                "name": app_name,
                "path": None,
                "enabled": False,
                "available": False,
                "configured": False,
                "state": "unconfigured",
            }
        else:
            available = bool(base["available"])
            enabled = bool(base.get("enabled", EXTERNAL_APPS_ENABLED))
            if available:
                state = "available"
            elif not enabled:
                state = "disabled"
            else:
                state = "missing"

            record = {
                **base,
                "configured": True,
                "state": state,
            }

        record.update({
            "dependent_tools": dependent_tools,
            "dependent_tool_count": len(dependent_tools),
            "impact": APP_IMPACT_DESCRIPTIONS.get(app_name, "Helper app cho diagnostics hoac workflow mo rong."),
        })
        apps.append(record)

    impacted_tool_ids = {
        tool["id"]
        for app in apps
        if app["state"] != "available"
        for tool in app["dependent_tools"]
    }
    recommendations = build_external_app_recommendations({
        "apps": apps,
    })
    drift_events = detect_external_app_drift(
        {
            "apps": apps,
        },
        previous_state,
    )
    recommendations = sorted(
        [*recommendations, *drift_events],
        key=lambda item: ({"critical": 0, "warning": 1, "info": 2}.get(item["severity"], 99), item["id"]),
    )

    summary = {
        "total": len(apps),
        "available": sum(1 for app in apps if app["state"] == "available"),
        "missing": sum(1 for app in apps if app["state"] == "missing"),
        "disabled": sum(1 for app in apps if app["state"] == "disabled"),
        "unconfigured": sum(1 for app in apps if app["state"] == "unconfigured"),
        "with_dependents": sum(1 for app in apps if app["dependent_tool_count"] > 0),
        "impacted_tool_count": len(impacted_tool_ids),
        "recommendation_count": len(recommendations),
        "drift_event_count": len(drift_events),
        "warning_drift_count": sum(1 for item in drift_events if item["severity"] == "warning"),
        "path_drift_count": sum(1 for item in drift_events if item.get("drift_type") == "path_changed"),
        "availability_drift_count": sum(1 for item in drift_events if item.get("drift_type") == "availability_changed"),
        "version_drift_count": sum(1 for item in drift_events if item.get("drift_type") == "version_changed"),
        "binary_drift_count": sum(1 for item in drift_events if item.get("drift_type") == "binary_changed"),
    }

    return {
        "enabled": EXTERNAL_APPS_ENABLED,
        "schema": "external_apps_health_v2",
        "drift_schema": "external_apps_drift_v1",
        "previous_state_loaded": bool(previous_state),
        "summary": summary,
        "total": summary["total"],
        "available": summary["available"],
        "missing": summary["missing"] + summary["disabled"] + summary["unconfigured"],
        "apps": apps,
        "dependency_map": dependency_map,
        "impacted_tool_ids": sorted(impacted_tool_ids),
        "drift_events": drift_events,
        "recommendations": recommendations,
        "recommendation_text": [
            external_app_recommendation_to_text(item)
            for item in recommendations
        ],
    }


def print_external_apps_status(include_versions: bool = False) -> None:
    status = get_external_apps_status(include_versions=include_versions)
    print("\n========== EXTERNAL APPS ==========")
    print(f"Enabled  : {status['enabled']}")
    print(f"Available: {status['available']}/{status['total']}")

    for item in status["apps"]:
        mark = "OK" if item["available"] else "MISS"
        version = f" | {item['version']}" if item.get("version") else ""
        print(f"[{mark}] {item['name']:<24} | {item['path']}{version}")


def print_external_apps_health(include_versions: bool = False) -> None:
    previous_state = load_external_apps_health_state()
    health = build_external_apps_health(
        include_versions=include_versions,
        previous_state=previous_state,
    )
    summary = health["summary"]

    print("\n========== EXTERNAL APPS HEALTH V2 ==========")
    print(f"Available: {summary['available']}/{summary['total']}")
    print(f"Missing/disabled/unconfigured: {health['missing']}")
    print(f"Impacted tools: {summary['impacted_tool_count']}")
    print(f"Drift events: {summary['drift_event_count']}")

    for item in health["apps"]:
        mark = "OK" if item["state"] == "available" else item["state"].upper()
        version = f" | {item['version']}" if item.get("version") else ""
        tools = ", ".join(tool["id"] for tool in item["dependent_tools"]) or "-"
        print(
            f"[{mark:<12}] {item['name']:<24} | "
            f"tools: {tools} | {item.get('path') or '<unconfigured>'}{version}"
        )

    if health["recommendations"]:
        print("\nRecommendations:")
        for recommendation in health["recommendation_text"]:
            print(f"- {recommendation}")


def export_external_apps_report(
    include_versions: bool = True,
    *,
    update_state: bool = True,
    state_file: str | Path | None = None,
) -> dict[str, Any]:
    previous_state = load_external_apps_health_state(state_file)
    health = build_external_apps_health(
        include_versions=include_versions,
        previous_state=previous_state,
    )
    summary = health["summary"]
    report_status = "success" if health["missing"] == 0 and summary["warning_drift_count"] == 0 else "warning"
    report = create_report(
        tool_name="external_apps",
        action="health_v2",
        status=report_status,
        risk_level="safe",
        input_data={
            "include_versions": include_versions,
            "state_file": str(Path(state_file) if state_file is not None else EXTERNAL_APPS_HEALTH_STATE_FILE),
            "previous_state_loaded": bool(previous_state),
            "update_state": update_state,
        },
        results=health,
        recommendations=health["recommendation_text"],
        summary={
            "total": summary["total"],
            "available_count": summary["available"],
            "missing_count": summary["missing"],
            "disabled_count": summary["disabled"],
            "unconfigured_count": summary["unconfigured"],
            "with_dependents": summary["with_dependents"],
            "impacted_tool_count": summary["impacted_tool_count"],
            "recommendation_count": summary["recommendation_count"],
            "drift_event_count": summary["drift_event_count"],
            "warning_drift_count": summary["warning_drift_count"],
            "path_drift_count": summary["path_drift_count"],
            "undo_available": False,
        },
        undo_available=False,
        tags=["external_apps", "config", "safe", "health_v2", "drift_v1"],
    )
    saved_state_file = save_external_apps_health_state(health, state_file) if update_state else None

    log_action(
        "external_apps",
        "export_external_apps_report",
        report_status,
        {
            "available": summary["available"],
            "total": summary["total"],
            "missing": health["missing"],
            "impacted_tool_count": summary["impacted_tool_count"],
            "drift_event_count": summary["drift_event_count"],
            "report": str(report),
            "state_file": str(saved_state_file) if saved_state_file else None,
        },
    )

    print(f"Report: {report}")
    if saved_state_file:
        print(f"State: {saved_state_file}")
    return {
        "status": report_status,
        "report": str(report),
        "state_file": str(saved_state_file) if saved_state_file else None,
        "external_apps": health,
    }


def search_everything(keyword: str, limit: int = 30) -> dict[str, Any]:
    keyword = keyword.strip()
    if not keyword:
        return {
            "status": "empty",
            "results": [],
        }

    result = run_external_app("everything_cli", ["-n", str(limit), keyword], timeout=20)
    if result["status"] != "success":
        return {
            "status": result["status"],
            "error": result.get("stderr") or result.get("error"),
            "results": [],
            "external_result": result,
        }

    records = []
    for line in str(result.get("stdout") or "").splitlines():
        raw_path = line.strip()
        if not raw_path:
            continue

        path = Path(raw_path)
        record = {
            "name": path.name,
            "suffix": path.suffix.lower(),
            "path": str(path),
            "size": 0,
            "modified": "",
            "source": "everything",
        }

        try:
            if path.exists():
                stat = path.stat()
                record["size"] = stat.st_size
                record["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
        except OSError:
            pass

        records.append(record)

    return {
        "status": "success",
        "results": records[:limit],
        "source": "everything",
    }


def get_smartctl_devices() -> list[dict[str, Any]]:
    result = run_external_app("smartctl", ["--scan-open"], timeout=20)
    if result["status"] != "success":
        return []

    devices = []
    for line in str(result.get("stdout") or "").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue

        left, _, comment = text.partition("#")
        parts = left.strip().split()
        if not parts:
            continue

        devices.append({
            "device": parts[0],
            "args": parts[1:],
            "comment": comment.strip(),
        })

    return devices


def get_smartctl_health(max_devices: int = 12) -> dict[str, Any]:
    devices = get_smartctl_devices()
    results = []

    for device in devices[:max_devices]:
        command_args = ["-j", "-H", device["device"], *device["args"]]
        result = run_external_app("smartctl", command_args, timeout=20)
        record = {
            **device,
            "status": result["status"],
        }

        if result["status"] == "success":
            try:
                data = json.loads(result.get("stdout") or "{}")
            except json.JSONDecodeError:
                data = {}

            record.update({
                "model": data.get("model_name") or data.get("device", {}).get("model_name"),
                "serial": data.get("serial_number"),
                "smart_passed": data.get("smart_status", {}).get("passed"),
                "temperature": data.get("temperature", {}).get("current"),
            })
        else:
            record["error"] = result.get("stderr") or result.get("error")

        results.append(record)

    return {
        "status": "success" if results else "empty",
        "device_count": len(devices),
        "checked_count": len(results),
        "devices": results,
    }


def read_exiftool_metadata(path: str | Path) -> dict[str, Any]:
    result = run_external_app("exiftool", ["-j", "-n", str(path)], timeout=20)
    if result["status"] != "success":
        return {
            "status": result["status"],
            "error": result.get("stderr") or result.get("error"),
        }

    try:
        data = json.loads(result.get("stdout") or "[]")
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "error": str(exc),
        }

    return {
        "status": "success",
        "metadata": data[0] if data else {},
    }


def read_ffprobe_metadata(path: str | Path) -> dict[str, Any]:
    result = run_external_app(
        "ffprobe",
        ["-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(path)],
        timeout=20,
    )
    if result["status"] != "success":
        return {
            "status": result["status"],
            "error": result.get("stderr") or result.get("error"),
        }

    try:
        data = json.loads(result.get("stdout") or "{}")
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "error": str(exc),
        }

    return {
        "status": "success",
        "metadata": data,
    }


def summarize_media_metadata(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    ffprobe = read_ffprobe_metadata(path)
    exiftool = read_exiftool_metadata(path)

    summary: dict[str, Any] = {
        "path": str(path),
        "ffprobe_status": ffprobe["status"],
        "exiftool_status": exiftool["status"],
    }

    if ffprobe["status"] == "success":
        data = ffprobe.get("metadata", {})
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
        audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
        summary.update({
            "duration_seconds": fmt.get("duration"),
            "format_name": fmt.get("format_name"),
            "bit_rate": fmt.get("bit_rate"),
            "video_codec": video_stream.get("codec_name"),
            "audio_codec": audio_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
        })

    if exiftool["status"] == "success":
        metadata = exiftool.get("metadata", {})
        summary.update({
            "file_type": metadata.get("FileType"),
            "mime_type": metadata.get("MIMEType"),
            "create_date": metadata.get("CreateDate"),
            "image_width": metadata.get("ImageWidth"),
            "image_height": metadata.get("ImageHeight"),
        })

    return {
        "status": "success" if ffprobe["status"] == "success" or exiftool["status"] == "success" else "error",
        "summary": summary,
        "ffprobe": ffprobe,
        "exiftool": exiftool,
    }


def run_external_apps_manager() -> None:
    while True:
        print("""
========== EXTERNAL APPS MANAGER ==========
1. Xem trang thai app ngoai
2. Xem trang thai + version
3. Xem health v2 + dependency map
4. Xuat health report v2
5. Test Everything search
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_external_apps_status(include_versions=False)

        elif choice == "2":
            print_external_apps_status(include_versions=True)

        elif choice == "3":
            print_external_apps_health(include_versions=True)

        elif choice == "4":
            export_external_apps_report(include_versions=True)

        elif choice == "5":
            keyword = input("Nhap tu khoa search: ").strip()
            result = search_everything(keyword, limit=10)
            print(f"Status: {result['status']}")
            for item in result.get("results", []):
                print(item["path"])

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_external_apps_manager()
