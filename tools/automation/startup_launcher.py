from __future__ import annotations

import json
import subprocess
from pathlib import Path

from config.settings import BASE_DIR
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report

CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "startup_profiles.json"

DEFAULT_CONFIG = {
    "study": [
        {"name": "VS Code", "path": "code", "args": []},
        {"name": "Chrome", "path": "chrome", "args": ["https://chat.openai.com"]}
    ],
    "game": [],
    "work": []
}

def ensure_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)

def load_profiles() -> dict:
    ensure_config()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_profiles(profiles: dict) -> None:
    ensure_config()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def launch_profile(profile_name: str) -> dict:
    profiles = load_profiles()

    if profile_name not in profiles:
        print("Khong tim thay profile.")
        result = {
            "profile": profile_name,
            "status": "missing",
            "launched_count": 0,
            "error_count": 0,
            "apps": [],
        }
        log_action("startup_launcher", "launch_profile", "missing", result)
        return result

    apps = profiles[profile_name]
    if not apps:
        print("Profile nay chua co app nao.")
        result = {
            "profile": profile_name,
            "status": "empty",
            "launched_count": 0,
            "error_count": 0,
            "apps": [],
        }
        log_action("startup_launcher", "launch_profile", "empty", result)
        return result

    print(f"Dang mo profile: {profile_name}")
    launch_results = []

    for app in apps:
        try:
            path = app["path"]
            args = app.get("args", [])
            process = subprocess.Popen([path, *args], shell=False)
            print(f"Da mo: {app.get('name', path)}")
            launch_results.append({
                "name": app.get("name", path),
                "path": path,
                "args": args,
                "pid": process.pid,
                "status": "launched",
            })
        except Exception as e:
            print(f"Loi khi mo {app.get('name', app.get('path'))}: {e}")
            launch_results.append({
                "name": app.get("name", app.get("path")),
                "path": app.get("path"),
                "args": app.get("args", []),
                "status": "error",
                "error": str(e),
            })

    launched = sum(1 for item in launch_results if item["status"] == "launched")
    errors = sum(1 for item in launch_results if item["status"] == "error")
    status = "success" if errors == 0 else "partial"

    report = create_report(
        tool_name="startup_launcher",
        status=status,
        input_data={
            "profile": profile_name,
        },
        results={
            "launched_count": launched,
            "error_count": errors,
            "apps": launch_results,
        },
        recommendations=[
            "Review failed app paths if any app did not open.",
        ],
    )

    result = {
        "profile": profile_name,
        "status": status,
        "launched_count": launched,
        "error_count": errors,
        "apps": launch_results,
        "report": str(report),
    }

    log_action("startup_launcher", "launch_profile", status, result)
    print(f"Report: {report}")
    return result

def add_app_to_profile(profile_name: str, app_name: str, app_path: str, args: list[str] | None = None) -> dict:
    profiles = load_profiles()

    if profile_name not in profiles:
        profiles[profile_name] = []

    app_record = {
        "name": app_name,
        "path": app_path,
        "args": args or []
    }

    profiles[profile_name].append(app_record)

    save_profiles(profiles)
    print("Da them app vao profile.")

    report = create_report(
        tool_name="startup_launcher_config",
        status="success",
        input_data={
            "profile": profile_name,
        },
        results={
            "added_app": app_record,
            "profile_app_count": len(profiles[profile_name]),
            "config_file": str(CONFIG_FILE),
        },
        recommendations=[
            "Use Startup Launcher to verify the profile opens correctly.",
        ],
    )

    result = {
        "profile": profile_name,
        "added_app": app_record,
        "profile_app_count": len(profiles[profile_name]),
        "config_file": str(CONFIG_FILE),
        "report": str(report),
    }

    log_action("startup_launcher", "add_app_to_profile", "success", result)
    print(f"Report: {report}")
    return result

def show_profiles() -> dict:
    profiles = load_profiles()

    print("\n========== STARTUP PROFILES ==========")
    for name, apps in profiles.items():
        print(f"\n[{name}]")
        if not apps:
            print("  Chua co app.")
        for app in apps:
            print(f"  - {app.get('name')} | {app.get('path')} | args={app.get('args', [])}")

    result = {
        "profile_count": len(profiles),
        "profiles": {
            name: len(apps)
            for name, apps in profiles.items()
        },
        "config_file": str(CONFIG_FILE),
    }
    log_action("startup_launcher", "show_profiles", "success", result)
    return result

def run_startup_launcher() -> None:
    while True:
        print("""
========== STARTUP LAUNCHER ==========
1. Xem profiles
2. Mo profile
3. Them app vao profile
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            show_profiles()

        elif choice == "2":
            profile = input("Nhap ten profile: ").strip()
            launch_profile(profile)

        elif choice == "3":
            profile = input("Nhap ten profile, VD study/game/work: ").strip()
            name = input("Ten app: ").strip()
            path = input("Duong dan app.exe hoac command, VD code/chrome: ").strip().strip('"')
            raw_args = input("Args neu co, cach nhau bang dau |, bo trong neu khong co: ").strip()
            args = [x.strip() for x in raw_args.split("|") if x.strip()]
            add_app_to_profile(profile, name, path, args)

        elif choice == "0":
            break
        else:
            print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_startup_launcher()
