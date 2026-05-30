from __future__ import annotations

from tools.system.disk_checker import check_disk
from tools.system.process_monitor import show_top_process
from tools.system.recycle_bin_cleaner import clear_recycle_bin
from tools.system.junk_file_cleaner import run_junk_cleaner
from tools.system.browser_cache_cleaner import run_browser_cache_cleaner
from tools.system.game_booster import run_game_booster

from tools.storage.duplicate_finder import run_duplicate_finder
from tools.storage.media_organizer import run_media_organizer

from tools.search.file_indexer import (
    run_file_indexer,
    search_file_index,
    show_search_results,
)
from tools.automation.startup_launcher import run_startup_launcher

def handle_command(command: str) -> bool:
    cmd = command.lower().strip()

    if cmd in ("exit", "quit", "thoat", "0"):
        return False

    if "ổ" in cmd or "o cung" in cmd or "disk" in cmd:
        check_disk()

    elif "ram" in cmd or "cpu" in cmd or "process" in cmd or "tiến trình" in cmd:
        show_top_process()

    elif "recycle" in cmd or "thùng rác" in cmd:
        clear_recycle_bin()

    elif "file rác" in cmd or "junk" in cmd or "temp" in cmd:
        run_junk_cleaner()

    elif "trùng" in cmd or "duplicate" in cmd:
        run_duplicate_finder()

    elif "gom" in cmd or "media" in cmd or "video" in cmd:
        run_media_organizer()

    elif "cache" in cmd or "browser" in cmd or "trình duyệt" in cmd:
        run_browser_cache_cleaner()

    elif "startup" in cmd or "launcher" in cmd or "mở app" in cmd:
        run_startup_launcher()

    elif "game" in cmd or "booster" in cmd:
        run_game_booster()

    elif cmd.startswith("find ") or cmd.startswith("tìm "):
        keyword = command.split(" ", 1)[1]
        results = search_file_index(keyword)
        show_search_results(results)

    elif "index" in cmd:
        run_file_indexer()

    else:
        print("Chua hieu lenh. Thu: disk, ram, cache, duplicate, index, find <ten file>, game.")

    return True

def run_natural_command() -> None:
    print("Nhap lenh tu nhien. VD: 'check disk', 'find naruto', 'don cache', 'game booster'.")
    while True:
        command = input("\nAssistant> ")
        if not handle_command(command):
            break

if __name__ == "__main__":
    run_natural_command()
