"""Dashboard App (Phase 10) — giao diện Trang chủ phong cách Spotify + dashboard.

Cửa sổ desktop dùng `pywebview`: phần hiển thị là HTML/CSS (web/dashboard.html),
phần dữ liệu là Python thuần. JS gọi Python qua `window.pywebview.api.*`.

Backend an toàn KHÔNG đổi: dashboard chỉ đọc (dashboard_data, read-only); mọi
thao tác xóa/move thật vẫn mở Bot Panel cũ (token-gated) qua `open_cleanup`.

Entry point: `run_dashboard()`. Chạy: `python -m tools.ui.dashboard_app`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
HTML_PATH = BASE_DIR / "tools" / "ui" / "web" / "dashboard.html"
CLEANUP_LAUNCHER = BASE_DIR / "open_cleanup.py"


def _pythonw_path() -> str:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate if candidate.exists() else exe)


class DashboardApi:
    """Cầu nối JS -> Python. Mọi method ở đây gọi được từ web qua pywebview.api."""

    def get_dashboard(self) -> dict:
        """Trả về snapshot tình trạng máy (read-only)."""
        from tools.ui.dashboard_data import get_dashboard_snapshot

        return get_dashboard_snapshot()

    def get_live(self) -> dict:
        """Số liệu nhanh CPU/RAM (read-only) cho biểu đồ thời gian thực."""
        from tools.ui.dashboard_data import get_live_metrics

        return get_live_metrics()

    def get_clean(self) -> dict:
        """Danh sách file rác an toàn (read-only)."""
        from tools.ui.dashboard_data import get_clean_details

        return get_clean_details()

    def get_organizer(self) -> dict:
        """Tổng quan các tác vụ sắp xếp (read-only)."""
        from tools.ui.dashboard_data import get_organizer_overview

        return get_organizer_overview()

    def get_history(self) -> dict:
        """Lịch sử + hiệu quả (read-only)."""
        from tools.ui.dashboard_data import get_history_overview

        return get_history_overview()

    def open_cleanup(self) -> dict:
        """Mở Bot Panel cũ ở chế độ dọn dẹp (flow token-gated, an toàn)."""
        try:
            subprocess.Popen([_pythonw_path(), str(CLEANUP_LAUNCHER)], cwd=str(BASE_DIR))
            return {"opened": True}
        except Exception as exc:
            return {"opened": False, "error": str(exc)}


def run_dashboard() -> None:
    import webview

    api = DashboardApi()
    webview.create_window(
        "AI Desktop Assistant",
        str(HTML_PATH),
        js_api=api,
        width=920,
        height=600,
        min_size=(820, 540),
        background_color="#0d0d12",
    )
    webview.start()


if __name__ == "__main__":
    run_dashboard()
