# Them cac dong import nay vao main.py
from tools.file_indexer import run_file_indexer
from tools.startup_launcher import run_startup_launcher
from tools.browser_cache_cleaner import run_browser_cache_cleaner
from tools.game_booster import run_game_booster
from tools.natural_command import run_natural_command

# Them vao menu:
# 7. File indexer
# 8. Startup launcher
# 9. Don cache trinh duyet
# 10. Game booster safe
# 11. Nhap lenh tu nhien

# Them vao if/elif:
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
