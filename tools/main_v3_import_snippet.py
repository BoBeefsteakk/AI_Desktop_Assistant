# Them import vao main.py
from tools.temp_cleaner import run_temp_cleaner
from tools.download_organizer import run_download_organizer
from tools.empty_folder_finder import run_empty_folder_finder
from tools.assistant_logger import run_assistant_logger

# Them vao menu:
# 12. Don TEMP an toan
# 13. Sap xep Downloads theo ngay/loai file
# 14. Tim/xoa folder rong
# 15. Assistant logs / export AI

# Them vao if/elif:
elif choice == "12":
    run_temp_cleaner()
elif choice == "13":
    run_download_organizer()
elif choice == "14":
    run_empty_folder_finder()
elif choice == "15":
    run_assistant_logger()
