from __future__ import annotations

import time
import psutil

from config.settings import RAM_CRITICAL_PERCENT, RAM_WARNING_PERCENT
from tools.core.assistant_logger import log_action
from tools.core.external_apps import is_external_app_available
from tools.core.report_manager import create_report
from tools.core.safety_utils import format_size


def get_top_processes(limit: int = 15, sort_by: str = "ram") -> list[dict]:
    """
    Lay top process theo RAM hoac CPU.

    memory_percent:
        % RAM cua rieng process.

    system_memory_percent:
        % RAM toan he thong.
    """
    processes = []

    # Goi lan dau de psutil co moc tinh CPU.
    for process in psutil.process_iter(["pid", "name", "username"]):
        try:
            process.cpu_percent(interval=None)
        except Exception:
            pass

    time.sleep(0.5)

    system_memory_percent = psutil.virtual_memory().percent

    for process in psutil.process_iter(["pid", "name", "username"]):
        try:
            ram_bytes = process.memory_info().rss
            cpu_percent = process.cpu_percent(interval=None)
            memory_percent = process.memory_percent()

            processes.append({
                "pid": process.info["pid"],
                "name": process.info["name"] or "Unknown",
                "username": process.info.get("username") or "",
                "cpu_percent": cpu_percent,
                "memory_bytes": ram_bytes,
                "memory_percent": memory_percent,
                "system_memory_percent": system_memory_percent,
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if sort_by.lower() == "cpu":
        processes.sort(key=lambda item: item["cpu_percent"], reverse=True)
    else:
        processes.sort(key=lambda item: item["memory_bytes"], reverse=True)

    return processes[:limit]


def show_top_process(limit: int = 15, sort_by: str = "ram") -> None:
    processes = get_top_processes(limit=limit, sort_by=sort_by)

    print("\n========== TOP PROCESS ==========\n")
    print(
        f"{'STT':>3} | "
        f"{'PID':>7} | "
        f"{'Name':<30} | "
        f"{'CPU':>7} | "
        f"{'RAM':>10} | "
        f"{'RAM %':>7}"
    )
    print("-" * 90)

    for index, item in enumerate(processes, start=1):
        print(
            f"{index:>3} | "
            f"{item['pid']:>7} | "
            f"{item['name'][:30]:<30} | "
            f"{item['cpu_percent']:>6.1f}% | "
            f"{format_size(item['memory_bytes']):>10} | "
            f"{item['memory_percent']:>6.2f}%"
        )

    if processes:
        print("-" * 90)
        print(f"RAM toan he thong dang dung: {processes[0]['system_memory_percent']:.1f}%")

    external_helpers = {
        "process_explorer": is_external_app_available("sysinternals_procexp"),
        "handle": is_external_app_available("sysinternals_handle"),
        "rammap": is_external_app_available("sysinternals_rammap"),
    }
    if any(external_helpers.values()):
        print("\nSysinternals helpers available:")
        for name, available in external_helpers.items():
            if available:
                print(f"- {name}")

    recommendations = []
    if processes:
        system_ram = processes[0]["system_memory_percent"]
        if system_ram >= RAM_CRITICAL_PERCENT:
            recommendations.append("RAM toan he thong dang cao, nen kiem tra cac process dung RAM nhieu.")
        elif system_ram >= RAM_WARNING_PERCENT:
            recommendations.append("RAM dang o muc kha cao, nen theo doi neu may bat dau lag.")

    report = create_report(
        tool_name="process_monitor",
        status="success",
        input_data={
            "limit": limit,
            "sort_by": sort_by,
            "ram_warning_percent": RAM_WARNING_PERCENT,
            "ram_critical_percent": RAM_CRITICAL_PERCENT,
            "external_helpers": external_helpers,
        },
        results=processes,
        recommendations=recommendations,
        tags=["process", "external_apps"] if any(external_helpers.values()) else ["process"],
    )

    log_action(
        "process_monitor",
        "show_top_process",
        "success",
        {
            "limit": limit,
            "sort_by": sort_by,
            "process_count": len(processes),
            "external_helpers": external_helpers,
            "report": str(report),
        },
    )

    print(f"Report: {report}")


if __name__ == "__main__":
    sort_by = input("Sap xep theo ram/cpu? [ram]: ").strip().lower() or "ram"
    show_top_process(sort_by=sort_by)
