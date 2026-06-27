"""Background assistant — quét nền định kỳ + thông báo toast (Phase 8).

Mục tiêu: trợ lý tự quét ngầm khi máy rảnh, KHÔNG mở UI; nếu phát hiện vấn đề
mới (file rác/file nặng so với baseline) thì bắn toast Windows mời user mở app
để dọn. Toàn bộ luồng này là READ-ONLY — chỉ scan và thông báo, không bao giờ
tự xóa/move/backup file của user.

Entry point:
- `run_background_assistant_cycle(...)`  → chạy 1 lần (1 tick)
- `run_background_assistant_loop(...)`    → chạy lặp theo lịch (8.1)
- `run_background_assistant()`            → alias 1 tick cho CLI/test
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from config.settings import DEFAULT_SCAN_FOLDER
from tools.automation.boot_runner import run_periodic_scan
from tools.core.assistant_logger import log_action
from tools.ui.toast_notifier import show_toast


def _is_quiet_mode() -> bool:
    """Quiet mode (8.4): bỏ qua thông báo khi đang fullscreen (game/phim/present).

    Phát hiện bằng cách so cửa sổ foreground với kích thước màn hình. Read-only;
    nếu không xác định được thì coi như KHÔNG quiet (vẫn thông báo bình thường).
    """
    try:
        import win32api
        import win32con
        import win32gui

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False
        # Desktop/shell không tính là fullscreen app.
        if hwnd in (win32gui.GetDesktopWindow(), win32gui.GetShellWindow()):
            return False
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        win_w, win_h = right - left, bottom - top
        screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        # Cửa sổ phủ kín (hoặc lớn hơn) toàn màn hình => đang fullscreen.
        return win_w >= screen_w and win_h >= screen_h
    except Exception:
        return False


def run_background_assistant_cycle(
    *,
    root_drive: str | Path = DEFAULT_SCAN_FOLDER,
    scan_mode: str | None = None,
    respect_quiet_mode: bool = True,
    notify: bool = True,
) -> dict[str, Any]:
    """Chạy 1 tick quét nền và (tùy chọn) bắn toast nếu có vấn đề mới.

    Trả về dict gồm `notification`, `notified`, `quiet_mode`, `report`,
    `safety_contract`. KHÔNG đụng file user.
    """
    result: dict[str, Any] = {
        "schema_version": "background_assistant_cycle_v1",
        "notified": False,
        "quiet_mode": False,
        "notification": None,
        "report": None,
        "toast": None,
        "safety_contract": {
            "read_only": True,
            "delete_enabled": False,
            "move_enabled": False,
            "backup_enabled": False,
        },
    }

    export = run_periodic_scan(
        root_drive=root_drive,
        scan_mode=scan_mode,
        use_latest_baseline=True,
    )
    notification = export["periodic"]["notification"]
    result["notification"] = notification
    result["report"] = export.get("report")

    quiet = respect_quiet_mode and _is_quiet_mode()
    result["quiet_mode"] = quiet

    should_notify = bool(notification.get("should_notify"))
    if notify and should_notify and not quiet:
        # launch_arg: click toast -> protocol aidesktop:cleanup -> mở app tới
        # banner Dọn 1 chạm (8.3). Chỉ có tác dụng nếu protocol đã đăng ký
        # (tools.automation.toast_protocol.register_toast_protocol); nếu chưa,
        # toast vẫn hiện bình thường, chỉ là click không mở app.
        toast = show_toast(
            notification["title"],
            notification["message"],
            launch_arg="aidesktop:cleanup",
        )
        result["toast"] = toast
        result["notified"] = bool(toast.get("shown"))

    log_action(
        "background_assistant",
        "run_cycle",
        "success",
        {
            "report": result["report"],
            "new_issue_count": notification.get("new_issue_count"),
            "highest_severity": notification.get("highest_severity"),
            "should_notify": should_notify,
            "quiet_mode": quiet,
            "notified": result["notified"],
            "file_operations_executed": False,
        },
    )
    return result


def run_background_assistant_loop(
    *,
    interval_minutes: float = 60.0,
    max_cycles: Optional[int] = None,
    root_drive: str | Path = DEFAULT_SCAN_FOLDER,
    scan_mode: str | None = None,
    respect_quiet_mode: bool = True,
) -> dict[str, Any]:
    """Quét nền lặp theo lịch (8.1). Read-only.

    `max_cycles=None` chạy mãi; truyền số nguyên để giới hạn (dùng cho test).
    """
    interval_seconds = max(1.0, interval_minutes * 60.0)
    cycles = 0
    last: dict[str, Any] | None = None
    try:
        while max_cycles is None or cycles < max_cycles:
            last = run_background_assistant_cycle(
                root_drive=root_drive,
                scan_mode=scan_mode,
                respect_quiet_mode=respect_quiet_mode,
            )
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        pass
    return {
        "schema_version": "background_assistant_loop_v1",
        "cycles_run": cycles,
        "last_cycle": last,
        "safety_contract": {"read_only": True, "delete_enabled": False, "move_enabled": False},
    }


def run_background_assistant() -> dict[str, Any]:
    """Alias entry point: chạy 1 tick (cho CLI/test)."""
    return run_background_assistant_cycle()


if __name__ == "__main__":
    print(run_background_assistant())
