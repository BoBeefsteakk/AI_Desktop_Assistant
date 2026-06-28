"""Tray Assistant (8.3 bản chắc ăn) — icon khay hệ thống + quét nền.

Thay cho toast-click (vướng quirk AUMID của Windows), trợ lý nền giờ có một icon
ở khay đồng hồ. Click icon (hoặc menu chuột phải → "Mở dọn dẹp") sẽ mở Bot Panel
tới banner Dọn 1 chạm — đây là callback Python thuần nên LUÔN chạy, không phụ
thuộc cơ chế kích hoạt của Windows.

Vòng quét nền vẫn read-only và vẫn bắn toast thông báo khi có vấn đề mới; điểm
khác là chỗ "click để mở" giờ là tray icon thay vì toast.

Entry: `run_tray_assistant()`. Chạy ẩn: `pythonw -m tools.ui.tray_assistant`.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parents[2]


def _pythonw_path() -> str:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate if candidate.exists() else exe)


def open_cleanup_panel() -> None:
    """Mở dashboard mới (tiến trình riêng, không chặn tray)."""
    try:
        subprocess.Popen(
            [_pythonw_path(), "-m", "tools.ui.dashboard_app"], cwd=str(BASE_DIR)
        )
    except Exception:
        pass


def _make_icon_image(alert: bool):
    """Tạo icon đơn giản: xanh = bình thường, cam = có vấn đề mới."""
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = (245, 158, 11, 255) if alert else (37, 99, 235, 255)  # cam / xanh
    d.ellipse((6, 6, size - 6, size - 6), fill=color)
    d.text((20, 20), "AI", fill=(255, 255, 255, 255))
    return img


class TrayAssistant:
    def __init__(self, *, interval_minutes: Optional[float] = None) -> None:
        if interval_minutes is None:
            try:
                from config.settings import get_setting

                interval_minutes = float(get_setting("background.interval_minutes", 60) or 60)
            except Exception:
                interval_minutes = 60.0
        self.interval_seconds = max(5.0, float(interval_minutes) * 60.0)
        self.icon = None
        self._stop = threading.Event()
        self._last_alert = False

    # --- tray actions ---
    def _on_open(self, icon=None, item=None) -> None:
        open_cleanup_panel()

    def _on_scan_now(self, icon=None, item=None) -> None:
        threading.Thread(target=self._run_one_cycle, daemon=True).start()

    def _on_quit(self, icon=None, item=None) -> None:
        self._stop.set()
        if self.icon is not None:
            self.icon.stop()

    # --- background scan ---
    def _run_one_cycle(self) -> dict[str, Any] | None:
        try:
            from tools.automation.background_assistant import run_background_assistant_cycle

            # scan_mode="python" = quét in-process, KHÔNG gọi WizTree (subprocess)
            # nên không nháy cửa sổ terminal khi chạy nền.
            result = run_background_assistant_cycle(scan_mode="python")
            alert = bool(result.get("notification", {}).get("should_notify"))
            self._set_alert(alert)
            return result
        except Exception:
            return None

    def _set_alert(self, alert: bool) -> None:
        if self.icon is None or alert == self._last_alert:
            return
        self._last_alert = alert
        try:
            self.icon.icon = _make_icon_image(alert)
            self.icon.title = (
                "AI Desktop Assistant — có vấn đề mới, bấm để dọn"
                if alert
                else "AI Desktop Assistant — đang theo dõi"
            )
        except Exception:
            pass

    def _loop(self) -> None:
        # Quét ngay 1 lần khi khởi động, rồi lặp theo chu kỳ.
        while not self._stop.is_set():
            self._run_one_cycle()
            self._stop.wait(self.interval_seconds)

    def run(self) -> None:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("Mở trợ lý", self._on_open, default=True),
            pystray.MenuItem("Quét ngay", self._on_scan_now),
            pystray.MenuItem("Thoát", self._on_quit),
        )
        self.icon = pystray.Icon(
            "ai_desktop_assistant",
            _make_icon_image(False),
            "AI Desktop Assistant — đang theo dõi",
            menu,
        )
        threading.Thread(target=self._loop, daemon=True).start()
        self.icon.run()


def run_tray_assistant() -> None:
    TrayAssistant().run()


if __name__ == "__main__":
    run_tray_assistant()
