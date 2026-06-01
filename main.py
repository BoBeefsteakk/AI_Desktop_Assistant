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
from tools.storage.temp_cleaner import run_temp_cleaner
from tools.storage.empty_folder_finder import run_empty_folder_finder
from tools.storage.wiztree_adapter import run_wiztree_adapter

from tools.search.file_indexer import run_file_indexer
from tools.search.natural_command import run_natural_command

from tools.automation.startup_launcher import run_startup_launcher
from tools.automation.download_organizer import run_download_organizer
from tools.automation.download_watcher import run_download_watcher
from tools.core.assistant_logger import run_assistant_logger
from tools.core.audit_center import run_audit_center
from tools.core.behavior_tester import run_behavior_tester
from tools.core.capability_registry import run_capability_registry
from tools.core.config_manager import run_config_manager
from tools.core.external_apps import run_external_apps_manager
from tools.core.feed_readiness import run_feed_readiness
from tools.core.full_system_tester import run_full_system_tester
from tools.core.guided_action_runner import run_guided_action_runner
from tools.core.recommendation_center import run_recommendation_center
from tools.core.tool_tester import run_tool_tester
from tools.core.undo_manager import run_undo_manager


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
15. Temp Cleaner
16. Empty Folder Finder
17. Download Organizer
18. Download Watcher (Ctrl+C de dung)
19. Assistant Logs
20. Behavior Tester
21. Tool Tester
22. Config Manager
23. Audit Center
24. Undo Manager
25. Full System Tester
26. WizTree Adapter
27. External Apps Manager
28. Capability Registry
29. Recommendation Center
30. Guided Action Runner
31. Feed Assistant Readiness

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
            run_temp_cleaner()

        elif choice == "16":
            run_empty_folder_finder()

        elif choice == "17":
            run_download_organizer()

        elif choice == "18":
            run_download_watcher()

        elif choice == "19":
            run_assistant_logger()

        elif choice == "20":
            run_behavior_tester()

        elif choice == "21":
            run_tool_tester()

        elif choice == "22":
            run_config_manager()

        elif choice == "23":
            run_audit_center()

        elif choice == "24":
            run_undo_manager()

        elif choice == "25":
            run_full_system_tester()

        elif choice == "26":
            run_wiztree_adapter()

        elif choice == "27":
            run_external_apps_manager()

        elif choice == "28":
            run_capability_registry()

        elif choice == "29":
            run_recommendation_center()

        elif choice == "30":
            run_guided_action_runner()

        elif choice == "31":
            run_feed_readiness()

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    main()
