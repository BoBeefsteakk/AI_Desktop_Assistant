"""Startup Registration.

Manage whether the assistant runs automatically when Windows starts.

Primary method: drop a small launcher script into the per-user Startup folder
(`shell:startup`). It is fully removable (delete the launcher) and only ever
touches its own managed launcher file, never user data.

The launcher runs `boot_assistant.py`, which performs a read-only boot scan and
optionally opens the assistant UI. Nothing is deleted or moved automatically.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report


STARTUP_REGISTRATION_TOOL = "startup_registration"
LAUNCHER_NAME = "AI_Desktop_Assistant_Boot.cmd"
BOOT_ENTRY = "tools.automation.boot_runner"


def get_startup_folder() -> Path:
    appdata = os.environ.get("APPDATA", "")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_launcher_path() -> Path:
    return get_startup_folder() / LAUNCHER_NAME


def build_launcher_content() -> str:
    return (
        "@echo off\r\n"
        f"cd /d \"{BASE_DIR}\"\r\n"
        f"start \"AI Desktop Assistant\" /min py -m {BOOT_ENTRY}\r\n"
    )


def get_startup_status() -> dict[str, Any]:
    launcher = get_launcher_path()
    return {
        "method": "shell_startup",
        "enabled": launcher.exists(),
        "startup_folder": str(get_startup_folder()),
        "launcher_path": str(launcher),
        "boot_entry": BOOT_ENTRY,
    }


def enable_startup() -> dict[str, Any]:
    startup_folder = get_startup_folder()
    launcher = get_launcher_path()

    if not startup_folder.exists():
        startup_folder.mkdir(parents=True, exist_ok=True)

    launcher.write_text(build_launcher_content(), encoding="utf-8")
    status = get_startup_status()

    report = create_report(
        tool_name=STARTUP_REGISTRATION_TOOL,
        action="enable_startup",
        status="success",
        risk_level="medium",
        input_data={"method": "shell_startup"},
        results=status,
        recommendations=[
            "The assistant will run a read-only boot scan on the next login.",
            "Disable any time by removing the launcher from the Startup folder.",
        ],
        summary={
            "enabled": True,
            "method": "shell_startup",
            "undo_available": True,
        },
        undo_available=True,
        tags=["startup_registration", "autorun", "shell_startup"],
    )
    log_action(STARTUP_REGISTRATION_TOOL, "enable_startup", "success", status)
    print(f"Da bat tu chay khi khoi dong: {launcher}")
    print(f"Report: {report}")
    return {"status": "success", "report": str(report), "startup": status}


def disable_startup() -> dict[str, Any]:
    launcher = get_launcher_path()
    existed = launcher.exists()

    if existed:
        # Managed launcher file only (never user data); safe to remove directly.
        launcher.unlink()

    status = get_startup_status()
    report = create_report(
        tool_name=STARTUP_REGISTRATION_TOOL,
        action="disable_startup",
        status="success",
        risk_level="safe",
        input_data={"method": "shell_startup", "launcher_existed": existed},
        results=status,
        recommendations=[
            "Auto-run on startup is now disabled.",
            "Re-enable any time from Startup Registration.",
        ],
        summary={
            "enabled": False,
            "removed": existed,
            "method": "shell_startup",
            "undo_available": False,
        },
        undo_available=False,
        tags=["startup_registration", "autorun", "shell_startup"],
    )
    log_action(
        STARTUP_REGISTRATION_TOOL,
        "disable_startup",
        "success",
        {"removed": existed, **status},
    )
    if existed:
        print("Da tat tu chay khi khoi dong (da xoa launcher).")
    else:
        print("Tu chay khi khoi dong von da tat.")
    print(f"Report: {report}")
    return {"status": "success", "report": str(report), "startup": status}


def print_startup_status(status: dict[str, Any]) -> None:
    print("\n========== STARTUP REGISTRATION ==========")
    print(f"Phuong thuc: {status['method']}")
    print(f"Trang thai: {'BAT' if status['enabled'] else 'TAT'}")
    print(f"Startup folder: {status['startup_folder']}")
    print(f"Launcher: {status['launcher_path']}")
    print(f"Boot entry: {status['boot_entry']}")


def run_startup_registration() -> None:
    while True:
        status = get_startup_status()
        print("""
========== STARTUP REGISTRATION ==========
1. Xem trang thai tu chay khi khoi dong
2. Bat tu chay khi khoi dong
3. Tat tu chay khi khoi dong
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_startup_status(status)

        elif choice == "2":
            enable_startup()

        elif choice == "3":
            disable_startup()

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_startup_registration()
