from __future__ import annotations

import os
import time
import shutil
from pathlib import Path
from datetime import datetime
from config.settings import DEFAULT_DOWNLOAD_FOLDER, WATCHER_SCAN_INTERVAL

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("Thieu thu vien watchdog.")
    print("Cai bang lenh:")
    print("pip install watchdog")
    raise


# ============================================================
# CAU HINH
# ============================================================

DOWNLOADS_DIR = Path(DEFAULT_DOWNLOAD_FOLDER)

# File moi tai ve se duoc gom vao:
# Downloads/YYYY-MM-DD/Loai_file/file.ext
DATE_FORMAT = "%Y-%m-%d"

# Cho them vai giay sau khi browser bao file da tai xong
# de tranh move khi file van dang bi khoa.
WAIT_AFTER_EVENT_SECONDS = 2

# Kiem tra file on dinh dung luong trong bao lau truoc khi move.
STABLE_CHECK_INTERVAL = 1
STABLE_CHECK_TIMES = 3

# Cac duoi file tam khi dang download.
TEMP_DOWNLOAD_EXTENSIONS = {
    ".crdownload",   # Chrome / Edge / Coc Coc
    ".part",         # Firefox
    ".tmp",
    ".download",
    ".idownload"
}

FILE_CATEGORIES = {
    "Anh": {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"
    },
    "Video": {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"
    },
    "Audio": {
        ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"
    },
    "Tai_lieu": {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"
    },
    "File_nen": {
        ".zip", ".rar", ".7z", ".tar", ".gz"
    },
    "Code": {
        ".py", ".js", ".ts", ".html", ".css", ".cpp", ".c",
        ".java", ".json", ".xml", ".sql", ".php", ".cs"
    },
    "Cai_dat": {
        ".exe", ".msi", ".apk", ".iso"
    }
}


# ============================================================
# HAM PHU
# ============================================================

def get_today_folder_name() -> str:
    return datetime.now().strftime(DATE_FORMAT)


def get_category(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    for category, extensions in FILE_CATEGORIES.items():
        if suffix in extensions:
            return category

    return "Khac"


def is_temp_download_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in TEMP_DOWNLOAD_EXTENSIONS


def is_inside_today_folder(file_path: Path) -> bool:
    """
    Neu file da nam trong Downloads/YYYY-MM-DD/... thi bo qua,
    tranh bi move lap lai.
    """
    try:
        relative_parts = file_path.relative_to(DOWNLOADS_DIR).parts
        if len(relative_parts) >= 2:
            first_folder = relative_parts[0]
            datetime.strptime(first_folder, DATE_FORMAT)
            return True
    except Exception:
        return False

    return False


def wait_until_file_ready(file_path: Path) -> bool:
    """
    Doi den khi:
    - file ton tai
    - khong phai file tam .crdownload/.part
    - dung luong on dinh trong vai lan check
    """
    time.sleep(WAIT_AFTER_EVENT_SECONDS)

    if not file_path.exists():
        return False

    if is_temp_download_file(file_path):
        return False

    last_size = -1
    stable_count = 0

    while stable_count < STABLE_CHECK_TIMES:
        try:
            current_size = file_path.stat().st_size
        except OSError:
            return False

        if current_size == last_size:
            stable_count += 1
        else:
            stable_count = 0
            last_size = current_size

        time.sleep(STABLE_CHECK_INTERVAL)

    return True


def make_unique_path(target_path: Path) -> Path:
    """
    Neu trung ten file thi them _1, _2, _3...
    """
    if not target_path.exists():
        return target_path

    count = 1
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent

    while True:
        new_path = parent / f"{stem}_{count}{suffix}"

        if not new_path.exists():
            return new_path

        count += 1


def organize_downloaded_file(file_path: Path) -> None:
    """
    Flow dung yeu cau:
    1. Khi file dau tien trong ngay duoc tai ve:
       tao folder Downloads/YYYY-MM-DD
    2. Neu file la anh:
       tao folder con Anh neu chua co
    3. Move file vao folder con theo loai
    4. Cac loai khac lam tuong tu
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return

    if not file_path.is_file():
        return

    if is_temp_download_file(file_path):
        return

    if is_inside_today_folder(file_path):
        return

    if not wait_until_file_ready(file_path):
        return

    category = get_category(file_path)

    today_folder = DOWNLOADS_DIR / get_today_folder_name()
    category_folder = today_folder / category

    category_folder.mkdir(parents=True, exist_ok=True)

    target_path = make_unique_path(category_folder / file_path.name)

    try:
        shutil.move(str(file_path), str(target_path))
        print(f"[OK] {file_path.name}")
        print(f"     -> {target_path}")

    except Exception as error:
        print(f"[LOI] Khong move duoc: {file_path}")
        print(f"      {error}")


def scan_existing_files_once() -> None:
    """
    Khi vua chay watcher, quet cac file dang co san trong Downloads.
    Neu co file moi chua duoc phan loai thi sap xep luon.
    """
    print("Dang quet file co san trong Downloads...")

    for item in DOWNLOADS_DIR.iterdir():
        try:
            if item.is_file():
                organize_downloaded_file(item)
        except Exception as error:
            print(f"[LOI] {item} | {error}")


# ============================================================
# WATCHDOG HANDLER
# ============================================================

class DownloadHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        organize_downloaded_file(file_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        # Browser thuong tai dang .crdownload/.part,
        # xong se rename/move thanh file that.
        file_path = Path(event.dest_path)
        organize_downloaded_file(file_path)

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Neu file tam vua doi xong thanh file that thi on_moved thuong bat duoc.
        # on_modified chi de backup.
        if not is_temp_download_file(file_path):
            organize_downloaded_file(file_path)


# ============================================================
# RUN
# ============================================================

def run_download_watcher() -> None:
    if not DOWNLOADS_DIR.exists():
        print(f"Khong tim thay Downloads folder: {DOWNLOADS_DIR}")
        return

    print("========== DOWNLOAD WATCHER ==========")
    print(f"Dang theo doi: {DOWNLOADS_DIR}")
    print("Khi tai file xong, tool se tu phan loai vao:")
    print("Downloads/YYYY-MM-DD/Loai_file/")
    print("Nhan Ctrl + C de dung.")
    print("=" * 40)

    scan_existing_files_once()

    event_handler = DownloadHandler()
    observer = Observer()
    observer.schedule(event_handler, str(DOWNLOADS_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(WATCHER_SCAN_INTERVAL)

    except KeyboardInterrupt:
        observer.stop()
        print("\nDa dung Download Watcher.")

    observer.join()


if __name__ == "__main__":
    run_download_watcher()
