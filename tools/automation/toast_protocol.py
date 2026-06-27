"""Đăng ký custom URI protocol `aidesktop:` để toast click mở app (8.3).

Khi user bấm vào toast của trợ lý nền (launch='aidesktop:cleanup'), Windows kích
hoạt protocol này → chạy `open_cleanup.bat` → mở Bot Panel với `--cleanup` →
nhảy thẳng tới banner Dọn 1 chạm.

Đăng ký nằm ở HKEY_CURRENT_USER (không cần quyền admin, gỡ được). Module này KHÔNG
xóa/move file của user — chỉ ghi/đọc registry key của chính protocol này.

Entry point: `register_toast_protocol()`, `unregister_toast_protocol()`,
`get_toast_protocol_status()`, `run_toast_protocol()` (in trạng thái).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROTOCOL_NAME = "aidesktop"
_BASE_DIR = Path(__file__).resolve().parents[2]
# Windows KHÔNG chấp nhận .bat làm handler cho URL protocol -> dùng pythonw.exe
# (file thực thi) chạy script .py launcher.
_LAUNCHER = _BASE_DIR / "open_cleanup.py"
_KEY_PATH = rf"Software\Classes\{PROTOCOL_NAME}"
_COMMAND_KEY_PATH = rf"{_KEY_PATH}\shell\open\command"


def _pythonw_path() -> str:
    """Đường dẫn pythonw.exe (chạy không cửa sổ); fallback python.exe."""
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate if candidate.exists() else exe)


def _command_value() -> str:
    return f'"{_pythonw_path()}" "{_LAUNCHER}" "%1"'


def register_toast_protocol() -> dict[str, Any]:
    """Đăng ký protocol aidesktop: ở HKCU. Trả về dict trạng thái."""
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
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _KEY_PATH) as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "URL:AI Desktop Assistant")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _COMMAND_KEY_PATH) as cmd_key:
            winreg.SetValueEx(cmd_key, None, 0, winreg.REG_SZ, _command_value())
        result["registered"] = True
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def unregister_toast_protocol() -> dict[str, Any]:
    """Gỡ protocol aidesktop: khỏi HKCU."""
    result: dict[str, Any] = {
        "schema_version": "toast_protocol_v1",
        "action": "unregister",
        "protocol": PROTOCOL_NAME,
        "removed": False,
        "error": None,
    }
    try:
        import winreg

        # Xóa từ key con lên key cha (DeleteKey yêu cầu key rỗng con).
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
