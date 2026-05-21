from tools.system.disk_checker import check_disk
from tools.system.process_monitor import show_top_process
from tools.system.recycle_bin_cleaner import clear_recycle_bin
from tools.system.junk_file_cleaner import run_junk_cleaner
from tools.system.browser_cache_cleaner import run_browser_cache_cleaner
from tools.system.game_booster import run_game_booster

from tools.storage.duplicate_finder import run_duplicate_finder
from tools.storage.media_organizer import run_media_organizer
from tools.storage.folder_size_analyzer import run_folder_size_analyzer
from tools.storage.large_file_finder import run_large_file_finder
from tools.storage.system_advisor import run_system_advisor

from tools.search.file_indexer import run_file_indexer
from tools.search.natural_command import run_natural_command

from tools.automation.startup_launcher import run_startup_launcher
from tools.core.tool_tester import run_tool_tester


EXIT_COMMANDS = ["0", "out", "exit", "quit", "thoat", "thoát"]


def main():
    while True:
        print("""
========== AI DESKTOP ASSISTANT - SAFE V2 ==========

1. Check o cung
2. Xem process an RAM/CPU
3. Don Recycle Bin
4. Don file rac
5. Tim/xoa file trung lap
6. Gom media + co restore backup

7. File indexer
8. Startup launcher
9. Don cache trinh duyet
10. Game booster safe
11. Nhap lenh tu nhien

12. Folder Size Analyzer
13. Large File Finder
14. System Advisor
15. Tool Tester

0. Thoat

====================================================
""")

        choice = input("Nhap lua chon: ").strip()

        if choice.lower() in EXIT_COMMANDS:
            print("Da thoat assistant.")
            break

        if choice == "1":
            check_disk()

        elif choice == "2":
            sort_by = input("Sap xep theo ram/cpu? [ram]: ").strip().lower() or "ram"
            show_top_process(sort_by=sort_by)

        elif choice == "3":
            clear_recycle_bin()

        elif choice == "4":
            run_junk_cleaner()

        elif choice == "5":
            run_duplicate_finder()

        elif choice == "6":
            run_media_organizer()

        elif choice == "7":
            run_file_indexer()

        elif choice == "8":
            run_startup_launcher()

        elif choice == "9":
            run_browser_cache_cleaner()

        elif choice == "10":
            run_game_booster()

        elif choice == "11":
            run_natural_command()

        elif choice == "12":
            run_folder_size_analyzer()

        elif choice == "13":
            run_large_file_finder()

        elif choice == "14":
            run_system_advisor()

        elif choice == "15":
            run_tool_tester()

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    main()