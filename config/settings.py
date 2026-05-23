from pathlib import Path

# =========================
# BASE PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"

REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(exist_ok=True)

# =========================
# DEFAULT SCAN SETTINGS
# =========================

DEFAULT_SCAN_FOLDER = r"D:\\"

DEFAULT_DOWNLOAD_FOLDER = r"D:\Downloads"

DEFAULT_LARGE_FILE_MB = 500

DEFAULT_RESULT_LIMIT = 50

# =========================
# SAFETY SETTINGS
# =========================

SAFE_SYSTEM_FOLDERS = [
    "Windows",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "$Recycle.Bin",
    "System Volume Information",
]

SAFE_SYSTEM_FILES = [
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
]

# =========================
# WATCHER SETTINGS
# =========================

WATCHER_SCAN_INTERVAL = 5

# =========================
# LOG SETTINGS
# =========================

ENABLE_ACTION_LOG = True

ENABLE_JSON_REPORT = True