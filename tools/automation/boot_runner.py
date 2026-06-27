"""Boot Runner.

Entry point launched by the Startup Registration launcher on each Windows
login. It runs a read-only full-drive boot scan and, if configured, opens the
assistant UI so the user can review advice and decide.

It never deletes or moves files on its own. The scan is read-only; any real
file operation still goes through the guarded selection/dry-run/token flows.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from config.settings import (
    DEFAULT_LARGE_FILE_MB,
    DEFAULT_RESULT_LIMIT,
    DEFAULT_SCAN_FOLDER,
    STARTUP_AUTO_SCAN_ON_BOOT,
    STARTUP_DELAY_SECONDS,
    STARTUP_OPEN_UI,
    STARTUP_SCAN_MODE,
)
from tools.core.assistant_logger import log_action


def run_periodic_scan(
    *,
    root_drive: str | Path = DEFAULT_SCAN_FOLDER,
    scan_mode: str | None = None,
    large_file_mb: int = DEFAULT_LARGE_FILE_MB,
    result_limit: int = DEFAULT_RESULT_LIMIT,
    previous_result: dict[str, Any] | None = None,
    use_latest_baseline: bool = True,
) -> dict[str, Any]:
    """Run one scheduled read-only scan tick for the assistant UI."""
    from tools.core.startup_scan import export_periodic_scan_report

    export = export_periodic_scan_report(
        root_drive=root_drive,
        scan_mode=scan_mode,
        large_file_mb=large_file_mb,
        result_limit=result_limit,
        previous_result=previous_result,
        use_latest_baseline=use_latest_baseline,
    )
    notification = export["periodic"]["notification"]
    log_action(
        "boot_runner",
        "run_periodic_scan",
        "success",
        {
            "report": export.get("report"),
            "new_issue_count": notification["new_issue_count"],
            "highest_severity": notification["highest_severity"],
            "file_operations_executed": False,
        },
    )
    return export


def run_boot(*, open_ui: bool | None = None) -> dict[str, Any]:
    if not STARTUP_AUTO_SCAN_ON_BOOT:
        log_action("boot_runner", "run_boot", "skipped", {"reason": "auto_scan_on_boot is False"})
        print("Auto scan on boot da tat trong cau hinh. Bo qua.")
        return {"status": "skipped", "reason": "auto_scan_on_boot_disabled"}

    if STARTUP_DELAY_SECONDS > 0:
        time.sleep(STARTUP_DELAY_SECONDS)

    # Import here so a disabled boot run does not pay the heavy import cost.
    from tools.core.startup_scan import export_startup_scan_report

    export = export_startup_scan_report(scan_mode=STARTUP_SCAN_MODE)
    log_action(
        "boot_runner",
        "run_boot",
        "success",
        {
            "report": export.get("report"),
            "scan_mode": export["startup"]["scan_mode"],
            "delete_candidate_count": export["startup"]["advisory"]["delete_candidate_count"],
        },
    )

    should_open_ui = STARTUP_OPEN_UI if open_ui is None else open_ui
    if should_open_ui:
        try:
            from tools.ui.startup_window import run_startup_window

            run_startup_window(scan_mode=STARTUP_SCAN_MODE)
        except Exception as exc:  # UI is optional; never block boot on it.
            log_action("boot_runner", "open_ui", "error", {"error": str(exc)})
            print(f"Khong mo duoc UI: {exc}")

    return export


if __name__ == "__main__":
    run_boot()
