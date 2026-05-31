from __future__ import annotations

from pathlib import Path

from tools.core.assistant_logger import log_action
from tools.core.external_apps import summarize_media_metadata
from tools.core.risk_classifier import classify_file_risk, PROTECTED
from tools.core.safety_utils import (
    ask_yes_no,
    format_size,
    is_system_path,
    restore_from_manifest,
    safe_move,
    save_manifest,
)

from config.settings import (
    DEFAULT_DOWNLOAD_FOLDER,
    MEDIA_EXTENSIONS as CONFIG_MEDIA_EXTENSIONS,
    MEDIA_ORGANIZER_TARGET_FOLDER_NAME,
)

from tools.core.report_manager import create_report

MEDIA_EXTENSIONS = CONFIG_MEDIA_EXTENSIONS

def scan_media_files(
    folder: str,
    target_folder_name: str = MEDIA_ORGANIZER_TARGET_FOLDER_NAME,
    recursive: bool = False,
) -> list[dict]:
    root = Path(folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return []

    if is_system_path(root):
        print("Khong nen quet truc tiep folder he thong.")
        return []

    root_risk = classify_file_risk(root)
    if root_risk["risk"] == PROTECTED:
        print("Folder goc nam trong vung duoc bao ve. Khong thuc hien media organizer.")
        return []

    target = root / target_folder_name
    iterator = root.rglob("*") if recursive else root.iterdir()
    results = []

    for path in iterator:
        try:
            if not path.is_file():
                continue
            if target in path.parents:
                continue
            if path.suffix.lower() not in MEDIA_EXTENSIONS:
                continue

            risk_data = classify_file_risk(path)
            results.append({
                "path": str(path),
                "target_path": str(target / path.name),
                "size": path.stat().st_size,
                "extension": path.suffix.lower(),
                "risk": risk_data["risk"],
                "risk_reason": risk_data["reason"],
                "risk_category": risk_data.get("category"),
                "risk_rule": risk_data.get("matched_rule"),
            })

        except (PermissionError, OSError):
            continue

    return results


def show_media_files(files: list[dict]) -> None:
    print("\n========== MEDIA FILES ==========")

    if not files:
        print("Khong co media can gom.")
        return

    total_size = sum(item["size"] for item in files)

    for index, item in enumerate(files, start=1):
        risk_category = item.get("risk_category") or item["risk"]
        print(
            f"{index:>3}. {format_size(item['size']):>10} | "
            f"{item['risk']:<15} | {risk_category:<24} | {item['path']}"
        )

    print("-" * 90)
    print(f"Tong file: {len(files)}")
    print(f"Tong dung luong: {format_size(total_size)}")


def scan_media_metadata(
    folder: str,
    recursive: bool = False,
    limit: int = 30,
) -> dict:
    files = scan_media_files(folder, recursive=recursive)
    selected_files = files[:limit]
    metadata_results = []

    print("\n========== MEDIA METADATA ==========")
    if not selected_files:
        print("Khong co media de doc metadata.")

    for item in selected_files:
        metadata = summarize_media_metadata(item["path"])
        summary = metadata["summary"]
        metadata_results.append({
            **item,
            "metadata": summary,
            "metadata_status": metadata["status"],
        })

        duration = summary.get("duration_seconds") or "unknown"
        video_codec = summary.get("video_codec") or "-"
        audio_codec = summary.get("audio_codec") or "-"
        resolution = "-"
        if summary.get("width") and summary.get("height"):
            resolution = f"{summary['width']}x{summary['height']}"

        print(f"{Path(item['path']).name}")
        print(f"  Status    : {metadata['status']}")
        print(f"  Type      : {summary.get('file_type') or summary.get('format_name') or '-'}")
        print(f"  Duration  : {duration}")
        print(f"  Video     : {video_codec} | {resolution}")
        print(f"  Audio     : {audio_codec}")
        print(f"  Path      : {item['path']}")

    report = create_report(
        tool_name="media_metadata",
        action="scan_metadata",
        status="success",
        risk_level="safe",
        input_data={
            "folder": folder,
            "recursive": recursive,
            "limit": limit,
        },
        results={
            "found_count": len(files),
            "scanned_count": len(metadata_results),
            "records": metadata_results,
        },
        recommendations=[
            "Metadata scan is read-only.",
            "Use Media Organizer move flow only after reviewing the file list.",
        ],
        summary={
            "found_count": len(files),
            "scanned_count": len(metadata_results),
            "undo_available": False,
        },
        undo_available=False,
        tags=["media", "metadata", "external_apps"],
    )

    log_action(
        "media_organizer",
        "scan_media_metadata",
        "success",
        {
            "folder": folder,
            "found_count": len(files),
            "scanned_count": len(metadata_results),
            "report": str(report),
        },
    )

    print(f"Report: {report}")
    return {
        "found_count": len(files),
        "scanned_count": len(metadata_results),
        "records": metadata_results,
        "report": str(report),
    }


def choose_media_files_to_move(files: list[dict]) -> list[dict]:
    if not files:
        return []

    movable_files = [
        item for item in files
        if item["risk"] != PROTECTED
    ]

    if not movable_files:
        print("Tat ca media tim thay deu bi chan boi safety layer.")
        return []

    while True:
        print("\nChon media muon gom:")
        print("- Nhap 0 de huy")
        print("- Nhap all de chon tat ca file khong PROTECTED")
        print("- Nhap so thu tu, cach nhau boi dau phay. VD: 1,3,5")

        choice = input("Lua chon: ").strip().lower()

        if choice == "0" or not choice:
            return []

        if choice == "all":
            if not ask_yes_no("Ban chac chan muon gom tat ca file khong PROTECTED?", default=False):
                continue

            return movable_files

        selected = []

        for raw_index in choice.split(","):
            raw_index = raw_index.strip()

            if not raw_index.isdigit():
                continue

            index = int(raw_index) - 1

            if 0 <= index < len(files):
                item = files[index]

                if item["risk"] == PROTECTED:
                    print(f"Bo qua file protected: {item['path']}")
                    continue

                selected.append(item)

        if selected:
            return selected

        print("Lua chon khong hop le. Vui long nhap lai.")


def move_media_files(
    selected_files: list[dict],
    root: Path,
    target: Path,
    recursive: bool,
    preview_report: str,
) -> dict:
    records = []
    blocked = 0
    errors = 0

    for item in selected_files:
        source = Path(item["path"])
        risk_data = classify_file_risk(source)

        if risk_data["risk"] == PROTECTED:
            blocked += 1
            records.append({
                **item,
                "status": "blocked",
                "risk": risk_data["risk"],
                "risk_reason": risk_data["reason"],
                "risk_category": risk_data.get("category"),
                "risk_rule": risk_data.get("matched_rule"),
            })
            continue

        try:
            record = safe_move(source, target / source.name)
            record.update({
                "size": item["size"],
                "extension": item["extension"],
                "risk": risk_data["risk"],
                "risk_reason": risk_data["reason"],
                "risk_category": risk_data.get("category"),
                "risk_rule": risk_data.get("matched_rule"),
                "status": "moved",
            })
            records.append(record)
            print(f"Moved: {record['old_path']} -> {record['new_path']}")

        except Exception as error:
            errors += 1
            records.append({
                **item,
                "status": "error",
                "error": str(error),
            })
            print(f"Loi: {item['path']} | {error}")

    moved_records = [
        item for item in records
        if item["status"] == "moved"
    ]

    manifest = None
    if moved_records:
        manifest = save_manifest("media_organizer_backup", moved_records)

    report = create_report(
        tool_name="media_organizer",
        status="success",
        input_data={
            "folder": str(root),
            "target_folder": str(target),
            "recursive": recursive,
            "preview_report": preview_report,
        },
        results={
            "moved_count": len(moved_records),
            "blocked_count": blocked,
            "error_count": errors,
            "records": records,
            "manifest": str(manifest) if manifest else None,
        },
        recommendations=[
            "Use restore option if files were moved incorrectly.",
            "Review backup manifest before deleting it.",
        ],
    )

    log_action(
        "media_organizer",
        "organize_media",
        "success",
        {
            "moved": len(moved_records),
            "blocked": blocked,
            "errors": errors,
            "manifest": str(manifest) if manifest else None,
            "report": str(report),
        },
    )

    print(f"\nDa gom {len(moved_records)} file.")
    if manifest:
        print(f"Backup manifest: {manifest}")
    print(f"Report: {report}")

    return {
        "moved_count": len(moved_records),
        "blocked_count": blocked,
        "error_count": errors,
        "records": records,
        "manifest": str(manifest) if manifest else None,
        "report": str(report),
    }


def organize_media(
    folder: str,
    target_folder_name: str = MEDIA_ORGANIZER_TARGET_FOLDER_NAME,
    recursive: bool = False,
) -> None:
    root = Path(folder)
    target = root / target_folder_name

    files = scan_media_files(
        folder,
        target_folder_name=target_folder_name,
        recursive=recursive,
    )
    show_media_files(files)

    selected_files = choose_media_files_to_move(files)

    if not selected_files:
        print("Da huy gom media.")
        log_action(
            "media_organizer",
            "organize_media",
            "cancelled",
            {"folder": str(root), "found_count": len(files)},
        )
        return

    preview_report = create_report(
        tool_name="media_organizer_preview",
        status="preview",
        input_data={
            "folder": str(root),
            "target_folder": str(target),
            "recursive": recursive,
        },
        results={
            "found_count": len(files),
            "selected_count": len(selected_files),
            "files": selected_files,
        },
        recommendations=[
            "Review target paths before confirming the move.",
            "Protected files are not selectable.",
        ],
    )

    print(f"Preview report: {preview_report}")

    if not ask_yes_no("Xac nhan gom cac file da chon?", default=False):
        print("Da huy gom media.")
        log_action(
            "media_organizer",
            "organize_media",
            "cancelled",
            {
                "folder": str(root),
                "selected_count": len(selected_files),
                "preview_report": str(preview_report),
            },
        )
        return

    move_media_files(
        selected_files=selected_files,
        root=root,
        target=target,
        recursive=recursive,
        preview_report=str(preview_report),
    )


def restore_media_from_manifest(manifest_path: str) -> None:
    result = restore_from_manifest(manifest_path)

    status = "success" if result["status"] == "success" else "error"
    report = create_report(
        tool_name="media_organizer_restore",
        status=status,
        input_data={
            "manifest": manifest_path,
        },
        results=result,
        recommendations=[
            "Review restored paths for rename-on-collision suffixes.",
        ],
    )

    log_action(
        "media_organizer",
        "restore_from_manifest",
        status,
        {
            "manifest": manifest_path,
            "restored": result["restored_count"],
            "skipped": result["skipped_count"],
            "report": str(report),
        },
    )

    print(f"Restore report: {report}")

def run_media_organizer() -> None:
    print("1. Gom media")
    print("2. Restore tu backup manifest")
    print("3. Doc metadata media (ExifTool/FFprobe, read-only)")
    choice = input("Chon: ").strip()

    if choice == "1":
        folder = input("Nhap folder goc: ").strip().strip('"') or DEFAULT_DOWNLOAD_FOLDER
        recursive = ask_yes_no("Quet ca folder con?", default=False)
        organize_media(folder, recursive=recursive)
    elif choice == "2":
        manifest = input("Nhap duong dan file backup manifest .json: ").strip().strip('"')
        restore_media_from_manifest(manifest)
    elif choice == "3":
        folder = input("Nhap folder goc: ").strip().strip('"') or DEFAULT_DOWNLOAD_FOLDER
        recursive = ask_yes_no("Quet ca folder con?", default=False)
        raw_limit = input("Doc metadata toi da bao nhieu file? [30]: ").strip()
        limit = int(raw_limit) if raw_limit.isdigit() else 30
        scan_media_metadata(folder, recursive=recursive, limit=limit)
    else:
        print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_media_organizer()
