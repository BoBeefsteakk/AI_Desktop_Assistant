from __future__ import annotations

from pathlib import Path

from tools.storage.folder_size_analyzer import analyze_top_folders
from tools.storage.large_file_finder import find_large_files
from tools.system.process_monitor import get_top_processes
from tools.core.safety_utils import ask_yes_no, format_size
from tools.core.assistant_logger import log_action
from config.settings import (
    DEFAULT_SCAN_FOLDER,
    DEFAULT_LARGE_FILE_MB,
    DEFAULT_RESULT_LIMIT,
    RAM_CRITICAL_PERCENT,
    RAM_WARNING_PERCENT,
    WIZTREE_PREFER_FOR_SYSTEM_ADVISOR,
)
from tools.core.report_manager import create_report
from tools.storage.wiztree_adapter import is_wiztree_available, scan_storage_with_wiztree

def print_divider() -> None:
    print("=" * 70)


def classify_file_advice(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    lower_path = file_path.lower()

    if "download" in lower_path or "downloads" in lower_path:
        return "Nam trong Downloads, nen xem co can giu lai khong."

    if suffix in {".zip", ".rar", ".7z", ".iso", ".img"}:
        return "File nen/bo cai lon, nen backup hoac xoa neu da giai nen/cai xong."

    if suffix in {".mp4", ".mkv", ".avi", ".mov"}:
        return "Video lon, nen gom vao media rieng hoac nen lai neu can."

    if suffix in {".exe", ".msi"}:
        return "File cai dat, neu da cai xong thi co the xoa/backup."

    if suffix in {".psd", ".prproj", ".aep"}:
        return "File project/editing lon, nen backup truoc khi don."

    return "Kiem tra thu cong truoc khi xoa."


def build_recommendations(
    top_folders: list[dict],
    large_files: list[dict],
    processes: list[dict]
) -> list[str]:
    recommendations = []

    if top_folders:
        biggest = top_folders[0]
        recommendations.append(
            f"Folder nang nhat hien tai la {biggest['path']} ({format_size(biggest['size'])}). "
            f"Neu o dia sap day, nen uu tien kiem tra folder nay truoc."
        )

    downloads_folder = next(
        (item for item in top_folders if "downloads" in item["path"].lower()),
        None
    )
    if downloads_folder:
        recommendations.append(
            f"Downloads dang chiem {format_size(downloads_folder['size'])}. "
            f"Nen de Download Watcher tu phan loai va dinh ky don file cu."
        )

    archive_files = [
        item for item in large_files
        if Path(item["path"]).suffix.lower() in {".zip", ".rar", ".7z", ".iso", ".img"}
    ]
    if archive_files:
        total_archive = sum(item["size"] for item in archive_files)
        recommendations.append(
            f"Co {len(archive_files)} file nen/bo cai lon, tong khoang {format_size(total_archive)}. "
            f"Nen kiem tra cac file da giai nen/cai xong."
        )

    video_files = [
        item for item in large_files
        if Path(item["path"]).suffix.lower() in {".mp4", ".mkv", ".avi", ".mov"}
    ]
    if video_files:
        total_video = sum(item["size"] for item in video_files)
        recommendations.append(
            f"Co {len(video_files)} video lon, tong khoang {format_size(total_video)}. "
            f"Nen gom vao thu muc media rieng hoac chuyen sang o luu tru."
        )

    if processes:
        system_ram = processes[0]["system_memory_percent"]

        if system_ram >= RAM_CRITICAL_PERCENT:
            recommendations.append(
                f"RAM toan he thong dang rat cao ({system_ram:.1f}%). "
                f"Nen dong bot browser/tab nang, app edit video, launcher game."
            )
        elif system_ram >= RAM_WARNING_PERCENT:
            recommendations.append(
                f"RAM dang o muc kha cao ({system_ram:.1f}%). "
                f"Nen theo doi neu may bat dau lag."
            )

        large_process_bytes = DEFAULT_LARGE_FILE_MB * 1024 * 1024
        heavy_processes = [
            item for item in processes
            if item["memory_bytes"] >= large_process_bytes
        ]

        if heavy_processes:
            names = ", ".join(item["name"] for item in heavy_processes[:5])
            recommendations.append(
                f"Cac process dang an RAM nhieu: {names}. "
                f"Chi nen tat neu pri biet chac khong dang dung."
            )

    if not recommendations:
        recommendations.append(
            "He thong hien tai kha on. Chua co dau hieu can can thiep manh."
        )

    return recommendations


def run_system_advisor() -> None:
    print_divider()
    print("SYSTEM ADVISOR - SAFE ANALYSIS")
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
            limit=DEFAULT_RESULT_LIMIT
        )

        print("\nDang phan tich file lon...")
        large_files = find_large_files(
            root_drive,
            min_size_mb=DEFAULT_LARGE_FILE_MB,
            limit=DEFAULT_RESULT_LIMIT
        )

    print("\nDang phan tich process...")
    processes = get_top_processes(limit=10, sort_by="ram")

    print_divider()
    print("TOP FOLDER NANG")
    print_divider()

    for item in top_folders:
        print(
            f"{format_size(item['size']):>10} | "
            f"{item['path']}"
        )

    print_divider()
    print("LARGE FILES")
    print_divider()

    for item in large_files:
        print(
            f"{format_size(item['size']):>10} | "
            f"{item['path']}"
        )
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
    print("ADVISOR RECOMMENDATIONS")
    print_divider()

    recommendations = build_recommendations(top_folders, large_files, processes)

    for index, recommendation in enumerate(recommendations, start=1):
        print(f"{index}. {recommendation}")

    report = create_report(
        tool_name="system_advisor",
        status="success",
        input_data={
            "root_drive": root_drive,
            "large_file_threshold_mb": DEFAULT_LARGE_FILE_MB,
            "result_limit": DEFAULT_RESULT_LIMIT,
            "ram_warning_percent": RAM_WARNING_PERCENT,
            "ram_critical_percent": RAM_CRITICAL_PERCENT,
            "storage_provider": storage_provider,
            "wiztree_status": wiztree_status,
        },
        results={
            "storage_provider": storage_provider,
            "storage_scan_report": storage_scan_report,
            "top_folders": top_folders,
            "large_files": large_files,
            "processes": processes,
        },
        recommendations=recommendations,
    )

    print_divider()
    print(f"Da luu report: {report}")

    log_action(
        "system_advisor",
        "run_system_advisor",
        "success",
        {
            "root_drive": root_drive,
            "report": str(report),
            "recommendation_count": len(recommendations),
            "storage_provider": storage_provider,
            "wiztree_status": wiztree_status,
        }
    )


if __name__ == "__main__":
    run_system_advisor()
