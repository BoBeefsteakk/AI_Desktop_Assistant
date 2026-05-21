from __future__ import annotations

from pathlib import Path
import send2trash

from .safety_utils import ask_yes_no, save_report
from .assistant_logger import log_action

SKIP_NAMES = {
    "$Recycle.Bin", "System Volume Information", ".git", "__pycache__"
}

def is_skipped(path: Path) -> bool:
    return any(part in SKIP_NAMES for part in path.parts)

def find_empty_folders(root_folder: str) -> list[dict]:
    root = Path(root_folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return []

    empty_folders = []

    # Duyet bottom-up de bat duoc folder cha bi rong sau khi folder con rong.
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            if not path.is_dir():
                continue

            if is_skipped(path):
                continue

            if not any(path.iterdir()):
                empty_folders.append({
                    "path": str(path)
                })

        except (PermissionError, OSError):
            continue

    return empty_folders

def show_empty_folders(folders: list[dict]) -> None:
    print("\n========== EMPTY FOLDERS ==========")

    if not folders:
        print("Khong tim thay folder rong.")
        return

    for i, item in enumerate(folders, start=1):
        print(f"{i:>3}. {item['path']}")

    print("-" * 80)
    print(f"Tong folder rong: {len(folders)}")

def delete_empty_folders(folders: list[dict]) -> None:
    if not folders:
        return

    report = save_report("empty_folders_before_delete", folders)
    print(f"Da luu report: {report}")
    print("Folder rong se duoc dua vao Recycle Bin neu co the.")

    if not ask_yes_no("Ban muon xoa cac folder rong nay?", default=False):
        print("Da huy.")
        log_action("empty_folder_finder", "delete_empty_folders", "cancelled", {"count": len(folders)})
        return

    deleted = 0
    failed = 0

    for item in folders:
        path = Path(item["path"])

        try:
            if path.exists() and path.is_dir() and not any(path.iterdir()):
                send2trash.send2trash(str(path))
                deleted += 1
        except Exception:
            failed += 1

    print(f"Da dua {deleted} folder rong vao Recycle Bin. Loi: {failed}.")
    log_action(
        "empty_folder_finder",
        "delete_empty_folders",
        "success",
        {"deleted": deleted, "failed": failed}
    )

def run_empty_folder_finder() -> None:
    folder = input("Nhap folder can quet: ").strip().strip('"') or "D:\\"

    folders = find_empty_folders(folder)
    show_empty_folders(folders)
    delete_empty_folders(folders)

if __name__ == "__main__":
    run_empty_folder_finder()
