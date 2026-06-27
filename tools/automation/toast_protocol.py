"""Đăng ký protocol cho toast click mở app (8.3) — dùng winotify.

Khi user bấm toast của trợ lý nền (launch=`CLEANUP_URI`), Windows kích hoạt
protocol `AI-Desktop-Assistant:` → chạy `pythonw open_cleanup.py` → mở Bot Panel
với `--cleanup` → nhảy thẳng banner Dọn 1 chạm.

Đăng ký do `winotify.Registry` ghi ở HKEY_CURRENT_USER (không cần admin, gỡ được).
Module này KHÔNG xóa/move file user — chỉ ghi/đọc registry key của protocol này.

Entry point: `register_toast_protocol()`, `unregister_toast_protocol()`,
`get_toast_protocol_status()`, `run_toast_protocol()`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

APP_ID = "AI Desktop Assistant"
PROTOCOL_NAME = "AI-Desktop-Assistant"  # winotify.format_name(APP_ID)
CLEANUP_URI = f"{PROTOCOL_NAME}:cleanup"

_BASE_DIR = Path(__file__).resolve().parents[2]
_LAUNCHER = _BASE_DIR / "open_cleanup.py"
_KEY_PATH = rf"SOFTWARE\Classes\{PROTOCOL_NAME}"
_COMMAND_KEY_PATH = rf"{_KEY_PATH}\shell\open\command"


def register_toast_protocol() -> dict[str, Any]:
    """Đăng ký protocol qua winotify.Registry (pythonw + open_cleanup.py)."""
    result: dict[str, Any] = {
        "schema_version": "toast_protocol_v1",
        "action": "register",
        "protocol": PROTOCOL_NAME,
        "launcher": str(_LAUNCHER),
        "registered": False,
        "error": None,
    }
    if not _LAUNCHER.exists():
        result["error"] = f"Khong tim thay launcher: {_LAUNCHER}"
        return result
    try:
        from winotify import PYW_EXE, Registry

        # force_override để cập nhật nếu trước đó đã đăng ký (vd trỏ .bat cũ).
        Registry(APP_ID, PYW_EXE, str(_LAUNCHER), force_override=True)
        result["registered"] = True
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def unregister_toast_protocol() -> dict[str, Any]:
    """Gỡ protocol khỏi HKCU."""
    result: dict[str, Any] = {
        "schema_version": "toast_protocol_v1",
        "action": "unregister",
        "protocol": PROTOCOL_NAME,
        "removed": False,
        "error": None,
    }
    try:
        import winreg

        for sub in (
            _COMMAND_KEY_PATH,
            rf"{_KEY_PATH}\shell\open",
            rf"{_KEY_PATH}\shell",
            _KEY_PATH,
        ):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except FileNotFoundError:
                pass
        result["removed"] = True
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def get_toast_protocol_status() -> dict[str, Any]:
    """Đọc trạng thái đăng ký protocol (read-only)."""
    status: dict[str, Any] = {
        "schema_version": "toast_protocol_v1",
        "action": "status",
        "protocol": PROTOCOL_NAME,
        "cleanup_uri": CLEANUP_URI,
        "registered": False,
        "command": None,
        "launcher_exists": _LAUNCHER.exists(),
    }
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _COMMAND_KEY_PATH) as cmd_key:
            status["command"] = winreg.QueryValueEx(cmd_key, None)[0]
            status["registered"] = True
    except FileNotFoundError:
        pass
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        status["error"] = f"{type(exc).__name__}: {exc}"
    return status


def run_toast_protocol() -> dict[str, Any]:
    """Entry point: in trạng thái hiện tại của protocol."""
    status = get_toast_protocol_status()
    print(
        f"Protocol {PROTOCOL_NAME}: "
        f"{'da dang ky' if status['registered'] else 'chua dang ky'}; "
        f"launcher {'OK' if status['launcher_exists'] else 'THIEU'}"
    )
    return status


if __name__ == "__main__":
    run_toast_protocol()
