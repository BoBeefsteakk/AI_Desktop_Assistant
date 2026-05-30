from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import (
    EXTERNAL_APP_PATHS,
    EXTERNAL_APP_TIMEOUT_SECONDS,
    EXTERNAL_APPS_ENABLED,
)
from tools.core.assistant_logger import log_action
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


def get_external_app_path(app_name: str) -> Path | None:
    return EXTERNAL_APP_PATHS.get(app_name)


def is_external_app_available(app_name: str) -> bool:
    path = get_external_app_path(app_name)
    return bool(EXTERNAL_APPS_ENABLED and path and path.exists())


def run_external_app(
    app_name: str,
    args: list[str],
    *,
    timeout: int | None = None,
) -> dict[str, Any]:
    path = get_external_app_path(app_name)

    if not EXTERNAL_APPS_ENABLED:
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

    for app_name, path in sorted(EXTERNAL_APP_PATHS.items()):
        record = {
            "name": app_name,
            "path": str(path),
            "available": EXTERNAL_APPS_ENABLED and path.exists(),
        }
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


def print_external_apps_status(include_versions: bool = False) -> None:
    status = get_external_apps_status(include_versions=include_versions)
    print("\n========== EXTERNAL APPS ==========")
    print(f"Enabled  : {status['enabled']}")
    print(f"Available: {status['available']}/{status['total']}")

    for item in status["apps"]:
        mark = "OK" if item["available"] else "MISS"
        version = f" | {item['version']}" if item.get("version") else ""
        print(f"[{mark}] {item['name']:<24} | {item['path']}{version}")


def export_external_apps_report(include_versions: bool = True) -> dict[str, Any]:
    status = get_external_apps_status(include_versions=include_versions)
    report_status = "success" if status["missing"] == 0 else "warning"
    report = create_report(
        tool_name="external_apps",
        action="status",
        status=report_status,
        risk_level="safe",
        input_data={
            "include_versions": include_versions,
        },
        results=status,
        recommendations=[
            "Keep external app paths stable or update config/user_settings.json.",
            "External apps are used as read-only helpers unless a tool explicitly asks for confirmation.",
        ],
        summary={
            "total": status["total"],
            "available_count": status["available"],
            "missing_count": status["missing"],
            "undo_available": False,
        },
        undo_available=False,
        tags=["external_apps", "config", "safe"],
    )

    log_action(
        "external_apps",
        "export_external_apps_report",
        report_status,
        {
            "available": status["available"],
            "total": status["total"],
            "report": str(report),
        },
    )

    print(f"Report: {report}")
    return {
        "status": report_status,
        "report": str(report),
        "external_apps": status,
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
3. Xuat report app ngoai
4. Test Everything search
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_external_apps_status(include_versions=False)

        elif choice == "2":
            print_external_apps_status(include_versions=True)

        elif choice == "3":
            export_external_apps_report(include_versions=True)

        elif choice == "4":
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
