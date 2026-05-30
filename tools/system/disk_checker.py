from __future__ import annotations

import psutil

from config.settings import DISK_CRITICAL_PERCENT, DISK_WARNING_PERCENT
from tools.core.assistant_logger import log_action
from tools.core.external_apps import get_smartctl_health, is_external_app_available
from tools.core.report_manager import create_report
from tools.core.safety_utils import format_size


def get_disk_info() -> list[dict]:
    results = []

    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        except OSError:
            continue

        if usage.percent >= DISK_CRITICAL_PERCENT:
            status = "critical"
            recommendation = "O nay gan day, nen uu tien don bot file."
        elif usage.percent >= DISK_WARNING_PERCENT:
            status = "warning"
            recommendation = (
                f"O nay dang dung tren {DISK_WARNING_PERCENT}%, "
                "nen theo doi va don dinh ky."
            )
        else:
            status = "ok"
            recommendation = "Chua can can thiep."

        results.append({
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "file_system": partition.fstype,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent,
            "status": status,
            "recommendation": recommendation,
        })

    return results


def check_disk() -> None:
    print("\n========== THONG TIN O CUNG ==========\n")

    disks = get_disk_info()

    if not disks:
        print("Khong doc duoc thong tin o cung.")
        log_action("disk_checker", "check_disk", "empty")
        return

    for disk in disks:
        print(f"O: {disk['device']}")
        print(f"Mountpoint       : {disk['mountpoint']}")
        print(f"File system      : {disk['file_system']}")
        print(f"Tong dung luong  : {format_size(disk['total'])}")
        print(f"Da su dung       : {format_size(disk['used'])}")
        print(f"Con trong        : {format_size(disk['free'])}")
        print(f"Phan tram dung   : {disk['percent']}%")

        if disk["status"] == "critical":
            print("Canh bao: O nay gan day, nen don bot file.")
        elif disk["status"] == "warning":
            print(f"Luu y: O nay dang dung tren {DISK_WARNING_PERCENT}%.")

        print("-" * 50)

    smart_health = {
        "status": "unavailable",
        "device_count": 0,
        "checked_count": 0,
        "devices": [],
    }

    if is_external_app_available("smartctl"):
        print("\n========== SMART HEALTH (smartctl) ==========\n")
        smart_health = get_smartctl_health()
        if smart_health["devices"]:
            for device in smart_health["devices"]:
                passed = device.get("smart_passed")
                health_text = "PASS" if passed is True else "WARN" if passed is False else "UNKNOWN"
                temp = device.get("temperature")
                temp_text = f" | Temp: {temp} C" if temp is not None else ""
                print(
                    f"[{health_text}] {device.get('device')} | "
                    f"{device.get('model') or device.get('comment') or 'Unknown'}"
                    f"{temp_text}"
                )
        else:
            print("Khong doc duoc SMART device hoac can quyen cao hon.")

    recommendations = [
        disk["recommendation"]
        for disk in disks
        if disk["status"] != "ok"
    ]

    failed_smart = [
        item for item in smart_health.get("devices", [])
        if item.get("smart_passed") is False
    ]
    if failed_smart:
        recommendations.append("Co o dia SMART health khong PASS. Nen backup du lieu quan trong som.")

    report = create_report(
        tool_name="disk_checker",
        status="success",
        input_data={
            "warning_percent": DISK_WARNING_PERCENT,
            "critical_percent": DISK_CRITICAL_PERCENT,
            "smartctl_available": is_external_app_available("smartctl"),
        },
        results={
            "disks": disks,
            "smart_health": smart_health,
        },
        recommendations=recommendations,
    )

    log_action(
        "disk_checker",
        "check_disk",
        "success",
        {
            "disk_count": len(disks),
            "warning_count": sum(1 for disk in disks if disk["status"] == "warning"),
            "critical_count": sum(1 for disk in disks if disk["status"] == "critical"),
            "smart_checked_count": smart_health.get("checked_count", 0),
            "report": str(report),
        },
    )

    print(f"Report: {report}")

if __name__ == "__main__":
    check_disk()
