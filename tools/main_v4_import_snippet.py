# Them import vao main.py:
from tools.folder_size_analyzer import run_folder_size_analyzer
from tools.large_file_finder import run_large_file_finder
from tools.system_advisor import run_system_advisor

# Them vao menu:
# 17. Phan tich folder nang
# 18. Tim file lon
# 19. System Advisor

# Them vao if/elif:
elif choice == "17":
    run_folder_size_analyzer()
elif choice == "18":
    run_large_file_finder()
elif choice == "19":
    run_system_advisor()
