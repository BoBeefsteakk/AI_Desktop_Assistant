"""Background Assistant Registration (8.1 — tự-chạy-khi-khởi-động).

Bật/tắt việc trợ lý nền tự chạy ẩn mỗi khi đăng nhập Windows. Khác với
`startup_registration` (chạy boot scan + mở UI), module này đăng ký một launcher
chạy `tools.automation.background_assistant --service` bằng `pythonw` (KHÔNG có
cửa sổ console) → quét nền im lặng theo chu kỳ, chỉ bắn toast khi có vấn đề mới.

Phương thức: thả launcher `.cmd` vào thư mục Startup của user (`shell:startup`).
Gỡ được hoàn toàn (xóa launcher); chỉ đụng tới launcher do chính nó quản lý, không
bao giờ đụng dữ liệu user. Đăng ký protocol click-to-open được bật kèm.

Entry point: `enable_background_autostart()`, `disable_background_autostart()`,
`get_background_autostart_status()`, `run_background_registration()` (menu CLI).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report

BACKGROUND_REGISTRATION_TOOL = "background_registration"
# Dùng .vbs để chạy ẩn HOÀN TOÀN khi đăng nhập (không nháy cửa sổ cmd/terminal).
LAUNCHER_NAME = "AI_Desktop_Assistant_Background.vbs"
# Chạy tray assistant (có icon khay để click mở) thay vì loop headless.
SERVICE_ENTRY = "tools.ui.tray_assistant"


def get_startup_folder() -> Path:
    appdata = os.environ.get("APPDATA", "")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_launcher_path() -> Path:
    return get_startup_folder() / LAUNCHER_NAME


def build_launcher_content() -> str:
    # VBS chạy pythonw với cửa sổ ẩn (0) -> không nháy terminal khi đăng nhập.
    base = str(BASE_DIR).replace('"', '""')
    return (
        'Set sh = CreateObject("WScript.Shell")\r\n'
        f'sh.CurrentDirectory = "{base}"\r\n'
        f'sh.Run "pythonw -m {SERVICE_ENTRY}", 0, False\r\n'
    )


def get_background_autostart_status() -> dict[str, Any]:
    launcher = get_launcher_path()
    status: dict[str, Any] = {
        "method": "shell_startup",
        "enabled": launcher.exists(),
        "startup_folder": str(get_startup_folder()),
        "launcher_path": str(launcher),
        "service_entry": SERVICE_ENTRY,
    }
    try:
        from tools.automation.toast_protocol import get_toast_protocol_status

        status["toast_protocol_registered"] = bool(
            get_toast_protocol_status().get("registered")
        )
    except Exception:
        status["toast_protocol_registered"] = None
    return status


def enable_background_autostart() -> dict[str, Any]:
    startup_folder = get_startup_folder()
    launcher = get_launcher_path()

    if not startup_folder.exists():
        startup_folder.mkdir(parents=True, exist_ok=True)

    launcher.write_text(build_launcher_content(), encoding="utf-8")

    # Bật luôn protocol click-to-open (8.3) để click toast mở được app.
    protocol_result = None
    try:
        from tools.automation.toast_protocol import register_toast_protocol

        protocol_result = register_toast_protocol()
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        protocol_result = {"registered": False, "error": str(exc)}

    status = get_background_autostart_status()
    report = create_report(
        tool_name=BACKGROUND_REGISTRATION_TOOL,
        action="enable_background_autostart",
        status="success",
        risk_level="medium",
        input_data={"method": "shell_startup"},
        results={"startup": status, "toast_protocol": protocol_result},
        recommendations=[
            "Tro ly nen se tu chay an moi lan dang nhap Windows (read-only).",
            "Tat bat ky luc nao bang cach go launcher khoi Startup folder.",
        ],
        summary={"enabled": True, "method": "shell_startup", "undo_available": True},
        undo_available=True,
        tags=["background_registration", "autorun", "shell_startup"],
    )
    log_action(BACKGROUND_REGISTRATION_TOOL, "enable_background_autostart", "success", status)
    print(f"Da bat tro ly nen tu chay khi khoi dong: {launcher}")
    print(f"Report: {report}")
    return {"status": "success", "report": str(report), "startup": status}


def disable_background_autostart() -> dict[str, Any]:
    launcher = get_launcher_path()
    existed = launcher.exists()

    if existed:
        # Managed launcher file only (never user data); safe to remove directly.
        launcher.unlink()

    status = get_background_autostart_status()
    report = create_report(
        tool_name=BACKGROUND_REGISTRATION_TOOL,
        action="disable_background_autostart",
        status="success",
        risk_level="safe",
        input_data={"method": "shell_startup", "launcher_existed": existed},
        results=status,
        recommendations=[
            "Tro ly nen se khong tu chay khi khoi dong nua.",
            "Bat lai bat ky luc nao tu Background Registration.",
        ],
        summary={"enabled": False, "removed": existed, "undo_available": False},
        undo_available=False,
        tags=["background_registration", "autorun", "shell_startup"],
    )
    log_action(
        BACKGROUND_REGISTRATION_TOOL,
        "disable_background_autostart",
        "success",
        {"removed": existed, **status},
    )
    if existed:
        print("Da tat tro ly nen tu chay khi khoi dong (da xoa launcher).")
    else:
        print("Tro ly nen tu chay von da tat.")
    print(f"Report: {report}")
    return {"status": "success", "report": str(report), "startup": status}


def print_background_status(status: dict[str, Any]) -> None:
    print("\n========== BACKGROUND ASSISTANT AUTOSTART ==========")
    print(f"Phuong thuc: {status['method']}")
    print(f"Trang thai: {'BAT' if status['enabled'] else 'TAT'}")
    print(f"Startup folder: {status['startup_folder']}")
    print(f"Launcher: {status['launcher_path']}")
    print(f"Service entry: {status['service_entry']}")
    print(f"Toast click-to-open (protocol): {status.get('toast_protocol_registered')}")


def run_background_registration() -> None:
    while True:
        status = get_background_autostart_status()
        print("""
========== BACKGROUND ASSISTANT AUTOSTART ==========
1. Xem trang thai tro ly nen tu chay
2. Bat tro ly nen tu chay khi khoi dong
3. Tat tro ly nen tu chay khi khoi dong
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            print_background_status(status)
        elif choice == "2":
            enable_background_autostart()
        elif choice == "3":
            disable_background_autostart()
        elif choice == "0":
            break
        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_background_registration()
