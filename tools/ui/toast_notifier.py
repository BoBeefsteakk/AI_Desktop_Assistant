"""Windows toast notifier (read-only, no extra dependency).

Hiển thị thông báo toast trên Windows 10/11 thông qua Windows Runtime
(`Windows.UI.Notifications`) gọi qua PowerShell. Không cần thư viện ngoài
(không winotify/win10toast/plyer); chỉ cần PowerShell có sẵn trên Windows.

Module này CHỈ hiển thị thông báo — không xóa, move hay đụng file của user.
Entry point: `run_toast_notifier()` (demo) và `show_toast(...)`.
"""

from __future__ import annotations

import base64
import subprocess

# AppUserModelID hiển thị tên nguồn trên toast. Dùng PowerShell làm host AUMID
# để không phải đăng ký shortcut riêng (đủ cho mục đích thông báo read-only).
_DEFAULT_APP_ID = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"
_APP_LABEL = "AI Desktop Assistant"


def _escape_xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_script(title: str, message: str, app_id: str) -> str:
    """Tạo script PowerShell bắn toast bằng Windows Runtime."""
    safe_title = _escape_xml(title)
    safe_message = _escape_xml(message)
    safe_label = _escape_xml(_APP_LABEL)
    toast_xml = (
        "<toast><visual><binding template='ToastGeneric'>"
        f"<text>{safe_title}</text>"
        f"<text>{safe_message}</text>"
        f"<text placement='attribution'>{safe_label}</text>"
        "</binding></visual></toast>"
    )
    return (
        "[Windows.UI.Notifications.ToastNotificationManager, "
        "Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, "
        "ContentType = WindowsRuntime] | Out-Null\n"
        "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
        f"$xml.LoadXml(@'\n{toast_xml}\n'@)\n"
        "$toast = New-Object Windows.UI.Notifications.ToastNotification $xml\n"
        f"$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app_id}')\n"
        "$notifier.Show($toast)\n"
    )


def show_toast(
    title: str,
    message: str,
    *,
    app_id: str = _DEFAULT_APP_ID,
    timeout: int = 15,
) -> dict:
    """Hiển thị một toast notification. Read-only, không đụng file user.

    Trả về dict: {shown, title, message, error, safety_contract}.
    """
    result = {
        "schema_version": "toast_notification_v1",
        "shown": False,
        "title": title,
        "message": message,
        "error": None,
        "safety_contract": {
            "read_only": True,
            "delete_enabled": False,
            "move_enabled": False,
        },
    }

    script = _build_script(title, message, app_id)
    # Truyền script qua -EncodedCommand (base64 UTF-16LE) để không cần temp file
    # và tránh mọi vấn đề escape dấu nháy.
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode == 0:
            result["shown"] = True
        else:
            result["error"] = (completed.stderr or completed.stdout or "").strip()
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result


def run_toast_notifier() -> dict:
    """Entry point demo: bắn một toast mẫu để kiểm tra môi trường."""
    return show_toast(
        "AI Desktop Assistant",
        "Toast hoạt động — trợ lý nền đã sẵn sàng thông báo.",
    )


if __name__ == "__main__":
    print(run_toast_notifier())
