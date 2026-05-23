from __future__ import annotations

from pathlib import Path

from tools.core.safety_utils import safe_move, save_manifest, restore_from_manifest, ask_yes_no

from config.settings import DEFAULT_DOWNLOAD_FOLDER

MEDIA_EXTENSIONS = (
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mp3", ".wav", ".flac", ".aac", ".m4a"
)

def organize_media(folder: str, target_folder_name: str = "Tat_ca_media", recursive: bool = False) -> None:
    root = Path(folder)
    if not root.exists():
        print("Folder khong ton tai.")
        return

    target = root / target_folder_name
    target.mkdir(exist_ok=True)

    iterator = root.rglob("*") if recursive else root.iterdir()
    records = []

    for path in iterator:
        try:
            if not path.is_file():
                continue
            if target in path.parents:
                continue
            if path.suffix.lower() not in MEDIA_EXTENSIONS:
                continue

            record = safe_move(path, target / path.name)
            records.append(record)
            print(f"Moved: {record['old_path']} -> {record['new_path']}")
        except Exception as e:
            print(f"Loi: {path} | {e}")

    if records:
        manifest = save_manifest("media_organizer_backup", records)
        print(f"\nDa gom {len(records)} file.")
        print(f"Backup manifest: {manifest}")
    else:
        print("Khong co media can gom.")

def run_media_organizer() -> None:
    print("1. Gom media")
    print("2. Restore tu backup manifest")
    choice = input("Chon: ").strip()

    if choice == "1":
        folder = input("Nhap folder goc: ").strip().strip('"') or DEFAULT_DOWNLOAD_FOLDER
        recursive = ask_yes_no("Quet ca folder con?", default=False)
        organize_media(folder, recursive=recursive)
    elif choice == "2":
        manifest = input("Nhap duong dan file backup manifest .json: ").strip().strip('"')
        restore_from_manifest(manifest)
    else:
        print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_media_organizer()
