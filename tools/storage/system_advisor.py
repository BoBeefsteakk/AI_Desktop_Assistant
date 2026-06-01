from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from config.settings import (
    DEFAULT_LARGE_FILE_MB,
    DEFAULT_RESULT_LIMIT,
    DEFAULT_SCAN_FOLDER,
    RAM_CRITICAL_PERCENT,
    RAM_WARNING_PERCENT,
    WIZTREE_PREFER_FOR_SYSTEM_ADVISOR,
)
from tools.core.assistant_logger import log_action
from tools.core.audit_center import get_audit_snapshot
from tools.core.capability_registry import get_capability_by_id
from tools.core.external_apps import (
    get_external_apps_status,
    get_smartctl_health,
    is_external_app_available,
)
from tools.core.report_manager import create_report
from tools.core.recommendation_center import is_test_report_record
from tools.core.safety_utils import ask_yes_no, format_size
from tools.storage.folder_size_analyzer import analyze_top_folders
from tools.storage.large_file_finder import find_large_files
from tools.storage.wiztree_adapter import is_wiztree_available, scan_storage_with_wiztree
from tools.system.disk_checker import get_disk_info
from tools.system.process_monitor import get_top_processes


ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".iso", ".img"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov"}
INSTALLER_EXTENSIONS = {".exe", ".msi"}
PROJECT_EXTENSIONS = {".psd", ".prproj", ".aep"}
SEVERITY_ORDER = {
    "critical": 0,
    "warning": 1,
    "info": 2,
}


def configure_console_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def print_divider() -> None:
    print("=" * 70)


def classify_file_advice(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    lower_path = file_path.lower()

    if "download" in lower_path or "downloads" in lower_path:
        return "Nam trong Downloads, nen xem co can giu lai khong."

    if suffix in ARCHIVE_EXTENSIONS:
        return "File nen/bo cai lon, nen backup hoac xoa neu da giai nen/cai xong."

    if suffix in VIDEO_EXTENSIONS:
        return "Video lon, nen gom vao media rieng hoac nen lai neu can."

    if suffix in INSTALLER_EXTENSIONS:
        return "File cai dat, neu da cai xong thi co the xoa/backup."

    if suffix in PROJECT_EXTENSIONS:
        return "File project/editing lon, nen backup truoc khi don."

    return "Kiem tra thu cong truoc khi xoa."


def get_disk_health_snapshot() -> dict[str, Any]:
    disks = get_disk_info()
    smart_health = {
        "status": "unavailable",
        "device_count": 0,
        "checked_count": 0,
        "devices": [],
    }

    if is_external_app_available("smartctl"):
        smart_health = get_smartctl_health()

    return {
        "disks": disks,
        "smart_health": smart_health,
    }


def make_recommendation(
    recommendation_id: str,
    severity: str,
    title: str,
    detail: str,
    *,
    suggested_tool_id: str | None = None,
    source: str = "system_advisor",
) -> dict[str, Any]:
    capability = get_capability_by_id(suggested_tool_id) if suggested_tool_id else None

    return {
        "id": recommendation_id,
        "severity": severity,
        "title": title,
        "detail": detail,
        "source": source,
        "suggested_tool_id": suggested_tool_id,
        "suggested_tool_name": capability["name"] if capability else None,
        "suggested_tool_risk": capability["risk_level"] if capability else None,
        "suggested_tool_needs_confirmation": capability["needs_confirmation"] if capability else None,
        "suggestion_only": True,
    }


def recommendation_to_text(recommendation: dict[str, Any]) -> str:
    tool_name = recommendation.get("suggested_tool_name")
    tool_risk = recommendation.get("suggested_tool_risk")
    tool_text = f" Suggested tool: {tool_name} (risk={tool_risk})." if tool_name else ""
    return (
        f"[{recommendation['severity'].upper()}] "
        f"{recommendation['title']}: {recommendation['detail']}{tool_text}"
    )


def format_recommendations(recommendations: list[dict[str, Any]]) -> list[str]:
    return [recommendation_to_text(item) for item in recommendations]


def summarize_recommendations(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total": len(recommendations),
        "critical_count": 0,
        "warning_count": 0,
        "info_count": 0,
    }

    for recommendation in recommendations:
        key = f"{recommendation['severity']}_count"
        if key in summary:
            summary[key] += 1

    return summary


def sort_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        recommendations,
        key=lambda item: (
            SEVERITY_ORDER.get(item["severity"], 99),
            item["id"],
        ),
    )


def build_structured_recommendations(
    top_folders: list[dict[str, Any]],
    large_files: list[dict[str, Any]],
    processes: list[dict[str, Any]],
    *,
    disks: list[dict[str, Any]] | None = None,
    smart_health: dict[str, Any] | None = None,
    external_apps: dict[str, Any] | None = None,
    audit_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    recommendations: dict[str, dict[str, Any]] = {}

    def add(item: dict[str, Any]) -> None:
        recommendations.setdefault(item["id"], item)

    for disk in disks or []:
        if disk.get("status") == "critical":
            add(make_recommendation(
                f"disk-critical-{disk.get('mountpoint') or disk.get('device')}",
                "critical",
                "O dia gan day",
                (
                    f"{disk.get('mountpoint') or disk.get('device')} dang dung "
                    f"{disk.get('percent')}%, con {format_size(disk.get('free', 0))}."
                ),
                suggested_tool_id="large_file_finder",
                source="disk_checker",
            ))
        elif disk.get("status") == "warning":
            add(make_recommendation(
                f"disk-warning-{disk.get('mountpoint') or disk.get('device')}",
                "warning",
                "O dia can theo doi",
                f"{disk.get('mountpoint') or disk.get('device')} dang dung {disk.get('percent')}%.",
                suggested_tool_id="folder_size_analyzer",
                source="disk_checker",
            ))

    failed_smart = [
        item for item in (smart_health or {}).get("devices", [])
        if item.get("smart_passed") is False
    ]
    if failed_smart:
        devices = ", ".join(item.get("device", "unknown") for item in failed_smart[:3])
        add(make_recommendation(
            "smart-health-failed",
            "critical",
            "SMART health co canh bao",
            f"Cac thiet bi khong PASS: {devices}. Nen backup du lieu quan trong som.",
            suggested_tool_id="disk_checker",
            source="smartctl",
        ))

    if top_folders:
        biggest = top_folders[0]
        add(make_recommendation(
            "largest-folder-review",
            "info",
            "Folder lon nhat can review",
            (
                f"{biggest['path']} dang chiem {format_size(biggest.get('size', 0))}. "
                "Neu o dia sap day, nen kiem tra folder nay truoc."
            ),
            suggested_tool_id="folder_size_analyzer",
            source=biggest.get("source", "storage"),
        ))

    downloads_folder = next(
        (item for item in top_folders if "downloads" in item["path"].lower()),
        None,
    )
    if downloads_folder:
        add(make_recommendation(
            "downloads-folder-heavy",
            "warning",
            "Downloads dang chiem dung luong",
            (
                f"Downloads dang chiem {format_size(downloads_folder.get('size', 0))}. "
                "Nen sap xep file tai ve va bo qua file dang tai do."
            ),
            suggested_tool_id="download_organizer",
            source=downloads_folder.get("source", "storage"),
        ))

    archive_files = [
        item for item in large_files
        if Path(item["path"]).suffix.lower() in ARCHIVE_EXTENSIONS
    ]
    if archive_files:
        total_archive = sum(item.get("size", 0) for item in archive_files)
        add(make_recommendation(
            "large-archive-files",
            "warning",
            "Co file nen/bo cai lon",
            (
                f"{len(archive_files)} file nen/bo cai lon, tong khoang "
                f"{format_size(total_archive)}. Nen review truoc khi xoa."
            ),
            suggested_tool_id="large_file_finder",
            source="large_file_finder",
        ))

    video_files = [
        item for item in large_files
        if Path(item["path"]).suffix.lower() in VIDEO_EXTENSIONS
    ]
    if video_files:
        total_video = sum(item.get("size", 0) for item in video_files)
        add(make_recommendation(
            "large-video-files",
            "info",
            "Co video lon",
            (
                f"{len(video_files)} video lon, tong khoang {format_size(total_video)}. "
                "Nen gom vao thu muc media rieng hoac chuyen sang o luu tru."
            ),
            suggested_tool_id="media_organizer",
            source="large_file_finder",
        ))

    if processes:
        system_ram = float(processes[0].get("system_memory_percent", 0))

        if system_ram >= RAM_CRITICAL_PERCENT:
            add(make_recommendation(
                "ram-critical",
                "critical",
                "RAM toan he thong rat cao",
                (
                    f"RAM dang dung {system_ram:.1f}%. Nen dong bot browser/tab nang "
                    "hoac app edit/game launcher neu khong dung."
                ),
                suggested_tool_id="process_monitor",
                source="process_monitor",
            ))
        elif system_ram >= RAM_WARNING_PERCENT:
            add(make_recommendation(
                "ram-warning",
                "warning",
                "RAM dang cao",
                f"RAM dang dung {system_ram:.1f}%. Nen theo doi neu may bat dau lag.",
                suggested_tool_id="process_monitor",
                source="process_monitor",
            ))

        heavy_process_bytes = DEFAULT_LARGE_FILE_MB * 1024 * 1024
        heavy_processes = [
            item for item in processes
            if item.get("memory_bytes", 0) >= heavy_process_bytes
        ]

        if heavy_processes:
            names = ", ".join(item.get("name", "Unknown") for item in heavy_processes[:5])
            add(make_recommendation(
                "heavy-processes",
                "info",
                "Co process an RAM nhieu",
                f"Cac process dang an RAM nhieu: {names}. Chi tat neu biet chac khong dang dung.",
                suggested_tool_id="process_monitor",
                source="process_monitor",
            ))

    if external_apps and external_apps.get("missing", 0) > 0:
        missing_names = [
            item["name"] for item in external_apps.get("apps", [])
            if not item.get("available")
        ]
        add(make_recommendation(
            "external-apps-missing",
            "warning",
            "Mot so app ngoai bi thieu",
            (
                f"Thieu {external_apps.get('missing')} app: {', '.join(missing_names[:5])}. "
                "Cap nhat path de tool scan/doc metadata chinh xac hon."
            ),
            suggested_tool_id="external_apps_manager",
            source="external_apps",
        ))

    reports = (audit_snapshot or {}).get("reports", [])
    bad_reports = [
        item for item in reports
        if item.get("status") in {"error", "warning"}
        and not is_test_report_record(item)
    ]
    if bad_reports:
        latest = bad_reports[-1]
        add(make_recommendation(
            "recent-report-issues",
            "warning",
            "Co report gan day can xem lai",
            (
                f"Report gan day cua {latest.get('tool')} co status {latest.get('status')}. "
                "Nen mo Audit Center de xem chi tiet truoc khi chay tiep."
            ),
            suggested_tool_id="audit_center",
            source="audit_center",
        ))

    if not recommendations:
        add(make_recommendation(
            "system-stable",
            "info",
            "He thong chua can can thiep manh",
            "Chua thay dau hieu bat thuong tu snapshot hien tai.",
            suggested_tool_id="audit_center",
            source="system_advisor",
        ))

    return sort_recommendations(list(recommendations.values()))


def build_recommendations(
    top_folders: list[dict],
    large_files: list[dict],
    processes: list[dict],
) -> list[str]:
    return format_recommendations(
        build_structured_recommendations(top_folders, large_files, processes)
    )


def build_advisor_snapshot(
    *,
    root_drive: str,
    storage_provider: str,
    wiztree_status: str,
    storage_scan_report: str | None,
    top_folders: list[dict[str, Any]],
    large_files: list[dict[str, Any]],
    processes: list[dict[str, Any]],
    disk_snapshot: dict[str, Any],
    external_apps: dict[str, Any],
    audit_snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "root_drive": root_drive,
        "storage": {
            "provider": storage_provider,
            "wiztree_status": wiztree_status,
            "storage_scan_report": storage_scan_report,
            "top_folders": top_folders,
            "large_files": large_files,
            "top_folder_count": len(top_folders),
            "large_file_count": len(large_files),
        },
        "disk": disk_snapshot,
        "processes": {
            "items": processes,
            "process_count": len(processes),
            "system_memory_percent": processes[0].get("system_memory_percent") if processes else None,
        },
        "external_apps": external_apps,
        "audit": {
            "log_count": audit_snapshot.get("log_count", 0),
            "report_count": audit_snapshot.get("report_count", 0),
            "recent_reports": audit_snapshot.get("reports", []),
        },
    }


def build_system_advisor_result(
    *,
    root_drive: str,
    storage_provider: str,
    wiztree_status: str,
    storage_scan_report: str | None,
    top_folders: list[dict[str, Any]],
    large_files: list[dict[str, Any]],
    processes: list[dict[str, Any]],
    disk_snapshot: dict[str, Any],
    external_apps: dict[str, Any],
    audit_snapshot: dict[str, Any],
) -> dict[str, Any]:
    snapshot = build_advisor_snapshot(
        root_drive=root_drive,
        storage_provider=storage_provider,
        wiztree_status=wiztree_status,
        storage_scan_report=storage_scan_report,
        top_folders=top_folders,
        large_files=large_files,
        processes=processes,
        disk_snapshot=disk_snapshot,
        external_apps=external_apps,
        audit_snapshot=audit_snapshot,
    )
    recommendations = build_structured_recommendations(
        top_folders,
        large_files,
        processes,
        disks=disk_snapshot.get("disks", []),
        smart_health=disk_snapshot.get("smart_health", {}),
        external_apps=external_apps,
        audit_snapshot=audit_snapshot,
    )
    recommendation_summary = summarize_recommendations(recommendations)

    return {
        "snapshot": snapshot,
        "recommendations": recommendations,
        "recommendation_text": format_recommendations(recommendations),
        "recommendation_summary": recommendation_summary,
    }


def show_system_advisor_result(result: dict[str, Any]) -> None:
    snapshot = result["snapshot"]
    storage = snapshot["storage"]
    disk = snapshot["disk"]
    processes = snapshot["processes"]["items"]
    external_apps = snapshot["external_apps"]
    recommendations = result["recommendations"]

    print_divider()
    print("DISK SNAPSHOT")
    print_divider()
    for item in disk.get("disks", []):
        print(
            f"{item['mountpoint']:<8} | {item['percent']:>5.1f}% used | "
            f"free {format_size(item['free']):>10} | {item['status']}"
        )

    smart_health = disk.get("smart_health", {})
    if smart_health.get("devices"):
        print("\nSMART:")
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

    print_divider()
    print(f"TOP FOLDER NANG ({storage['provider']})")
    print_divider()
    for item in storage["top_folders"]:
        print(f"{format_size(item['size']):>10} | {item['path']}")

    print_divider()
    print("LARGE FILES")
    print_divider()
    for item in storage["large_files"]:
        print(f"{format_size(item['size']):>10} | {item['path']}")
        print(f"           Goi y: {classify_file_advice(item['path'])}")

    print_divider()
    print("TOP RAM / CPU PROCESS")
    print_divider()
    for process in processes:
        print(
            f"RAM {format_size(process['memory_bytes']):>10} "
            f"({process['memory_percent']:>5.2f}%) | "
            f"CPU {process['cpu_percent']:>5.1f}% | "
            f"{process['name']}"
        )

    print_divider()
    print("EXTERNAL APPS")
    print_divider()
    print(f"Available: {external_apps['available']}/{external_apps['total']}")

    print_divider()
    print("ADVISOR RECOMMENDATIONS V2")
    print_divider()
    for index, recommendation in enumerate(recommendations, start=1):
        print(f"{index}. {recommendation_to_text(recommendation)}")


def run_system_advisor() -> None:
    configure_console_output()

    print_divider()
    print("SYSTEM ADVISOR V2 - SAFE READ-ONLY ANALYSIS")
    print_divider()

    root_drive = input(
        "Nhap o dia can phan tich: "
    ).strip().strip('"') or DEFAULT_SCAN_FOLDER

    storage_provider = "python"
    storage_scan_report = None
    wiztree_status = "unavailable"

    if is_wiztree_available():
        wiztree_status = "available"
        use_wiztree = ask_yes_no(
            "Dung WizTree de scan nhanh dung luong? Adapter chi doc CSV",
            default=WIZTREE_PREFER_FOR_SYSTEM_ADVISOR,
        )

        if use_wiztree:
            print("\nDang phan tich dung luong bang WizTree...")
            wiztree_result = scan_storage_with_wiztree(
                root_drive,
                min_size_mb=DEFAULT_LARGE_FILE_MB,
                limit=DEFAULT_RESULT_LIMIT,
                create_tool_report=True,
            )

            if wiztree_result["status"] == "success":
                top_folders = wiztree_result["top_folders"]
                large_files = wiztree_result["large_files"]
                storage_provider = "wiztree"
                storage_scan_report = wiztree_result.get("report")
                wiztree_status = "success"
            else:
                wiztree_status = wiztree_result["status"]
                print(
                    f"WizTree khong scan duoc ({wiztree_status}), "
                    "fallback sang Python scanner."
                )
        else:
            wiztree_status = "skipped"

    if storage_provider == "python":
        print("\nDang phan tich folder nang...")
        top_folders = analyze_top_folders(
            root_drive,
            limit=DEFAULT_RESULT_LIMIT,
        )

        print("\nDang phan tich file lon...")
        large_files = find_large_files(
            root_drive,
            min_size_mb=DEFAULT_LARGE_FILE_MB,
            limit=DEFAULT_RESULT_LIMIT,
        )

    print("\nDang doc disk/SMART snapshot...")
    disk_snapshot = get_disk_health_snapshot()

    print("\nDang phan tich process...")
    processes = get_top_processes(limit=10, sort_by="ram")

    print("\nDang doc external apps va audit snapshot...")
    external_apps = get_external_apps_status(include_versions=False)
    audit_snapshot = get_audit_snapshot(limit=20)

    result = build_system_advisor_result(
        root_drive=root_drive,
        storage_provider=storage_provider,
        wiztree_status=wiztree_status,
        storage_scan_report=storage_scan_report,
        top_folders=top_folders,
        large_files=large_files,
        processes=processes,
        disk_snapshot=disk_snapshot,
        external_apps=external_apps,
        audit_snapshot=audit_snapshot,
    )

    show_system_advisor_result(result)

    report = create_report(
        tool_name="system_advisor",
        action="analyze_system_v2",
        status="success",
        risk_level="safe",
        input_data={
            "root_drive": root_drive,
            "large_file_threshold_mb": DEFAULT_LARGE_FILE_MB,
            "result_limit": DEFAULT_RESULT_LIMIT,
            "ram_warning_percent": RAM_WARNING_PERCENT,
            "ram_critical_percent": RAM_CRITICAL_PERCENT,
            "storage_provider": storage_provider,
            "wiztree_status": wiztree_status,
        },
        results=result,
        recommendations=result["recommendation_text"],
        summary={
            "storage_provider": storage_provider,
            "top_folder_count": len(top_folders),
            "large_file_count": len(large_files),
            "process_count": len(processes),
            "disk_count": len(disk_snapshot.get("disks", [])),
            "external_apps_available": external_apps.get("available", 0),
            **result["recommendation_summary"],
            "undo_available": False,
        },
        undo_available=False,
        tags=["system_advisor", "read_only", "v2"],
    )

    print_divider()
    print(f"Da luu report: {report}")

    log_action(
        "system_advisor",
        "run_system_advisor_v2",
        "success",
        {
            "root_drive": root_drive,
            "report": str(report),
            "recommendation_count": result["recommendation_summary"]["total"],
            "critical_count": result["recommendation_summary"]["critical_count"],
            "warning_count": result["recommendation_summary"]["warning_count"],
            "storage_provider": storage_provider,
            "wiztree_status": wiztree_status,
        },
    )


if __name__ == "__main__":
    run_system_advisor()
