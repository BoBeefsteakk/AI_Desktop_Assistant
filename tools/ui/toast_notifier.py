"""Windows toast notifier (read-only).

Hiển thị thông báo toast trên Windows 10/11. Ưu tiên thư viện `winotify` (toast
click mở được app qua protocol đã đăng ký — xem `tools.automation.toast_protocol`).
Nếu môi trường không có winotify thì fallback sang PowerShell + Windows Runtime
(toast vẫn hiện, nhưng click có thể không mở app).

Module này CHỈ hiển thị thông báo — không xóa, move hay đụng file của user.
Entry point: `run_toast_notifier()` (demo) và `show_toast(...)`.
"""

from __future__ import annotations

import base64
import subprocess

_APP_ID = "AI Desktop Assistant"
_APP_LABEL = "AI Desktop Assistant"
# AUMID host dùng cho fallback PowerShell.
_PS_APP_ID = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"


def _escape_xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _show_with_winotify(title: str, message: str, launch_arg: str) -> dict:
    """Bắn toast bằng winotify. Raise nếu winotify không khả dụng."""
    from winotify import Notification

    toast = Notification(
        app_id=_APP_ID,
        title=title,
        msg=message,
        launch=launch_arg or "",
    )
    toast.show()
    return {"backend": "winotify"}


def _show_with_powershell(title: str, message: str, launch_arg: str, timeout: int) -> dict:
    safe_title = _escape_xml(title)
    safe_message = _escape_xml(message)
    safe_label = _escape_xml(_APP_LABEL)
    launch_attr = (
        f" launch='{_escape_xml(launch_arg)}' activationType='protocol'"
        if launch_arg
        else ""
    )
    toast_xml = (
        f"<toast{launch_attr}><visual><binding template='ToastGeneric'>"
        f"<text>{safe_title}</text>"
        f"<text>{safe_message}</text>"
        f"<text placement='attribution'>{safe_label}</text>"
        "</binding></visual></toast>"
    )
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager, "
        "Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, "
        "ContentType = WindowsRuntime] | Out-Null\n"
        "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
        f"$xml.LoadXml(@'\n{toast_xml}\n'@)\n"
        "$toast = New-Object Windows.UI.Notifications.ToastNotification $xml\n"
        f"$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{_PS_APP_ID}')\n"
        "$notifier.Show($toast)\n"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
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
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "").strip())
    return {"backend": "powershell"}


def show_toast(
    title: str,
    message: str,
    *,
    launch_arg: str = "",
    timeout: int = 15,
) -> dict:
    """Hiển thị một toast notification. Read-only, không đụng file user.

    `launch_arg`: protocol kích hoạt khi user bấm vào toast (8.3),
    vd "AI-Desktop-Assistant:cleanup".
    Trả về dict: {shown, backend, title, message, error, safety_contract}.
    """
    result = {
        "schema_version": "toast_notification_v1",
        "shown": False,
        "backend": None,
        "title": title,
        "message": message,
        "error": None,
        "safety_contract": {
            "read_only": True,
            "delete_enabled": False,
            "move_enabled": False,
        },
    }

    try:
        info = _show_with_winotify(title, message, launch_arg)
        result["shown"] = True
        result["backend"] = info["backend"]
        return result
    except Exception as winotify_exc:
        # winotify thiếu hoặc lỗi -> thử PowerShell.
        try:
            info = _show_with_powershell(title, message, launch_arg, timeout)
            result["shown"] = True
            result["backend"] = info["backend"]
        except Exception as ps_exc:
            result["error"] = (
                f"winotify: {type(winotify_exc).__name__}: {winotify_exc}; "
                f"powershell: {type(ps_exc).__name__}: {ps_exc}"
            )

    return result


def run_toast_notifier() -> dict:
    """Entry point demo: bắn một toast mẫu để kiểm tra môi trường."""
    return show_toast(
        "AI Desktop Assistant",
        "Toast hoạt động — trợ lý nền đã sẵn sàng thông báo.",
    )


if __name__ == "__main__":
    print(run_toast_notifier())
