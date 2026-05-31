from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

# =========================
# BASE PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
USER_SETTINGS_FILE = CONFIG_DIR / "user_settings.json"

REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
DATA_DIR = BASE_DIR / "data"

REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# =========================
# USER CONFIG
# =========================

DEFAULT_USER_SETTINGS: dict[str, Any] = {
    "paths": {
        "default_scan_folder": r"D:\\",
        "downloads_folder": r"D:\Downloads",
    },
    "thresholds": {
        "large_file_mb": 500,
        "result_limit": 50,
        "disk_warning_percent": 80,
        "disk_critical_percent": 90,
        "ram_warning_percent": 70,
        "ram_critical_percent": 85,
    },
    "safety": {
        "protected_root_paths": [
            "{BASE_DIR}",
        ],
        "protected_dir_names": [
            "$Recycle.Bin",
            "System Volume Information",
            "Windows",
            "Program Files",
            "Program Files (x86)",
            "ProgramData",
            ".git",
            "cứu",
        ],
        "guarded_dir_names": [
            "AppData",
            "Riot Games",
            "League of Legends",
            "LeagueOfLegends",
            "league_of_legends",
            "lol",
            "Garena",
            "FC Online",
            "FCO",
            "EA SPORTS FC Online",
            "Mobile",
            "Zalo Data",
            "tool",
            "AI_Desktop_Assistant",
            "AI_Desktop_Assistant_optimized",
            "C nang cao",
            "HocMay",
            "cuu",
        ],
        "dev_artifact_dir_names": [
            "__pycache__",
            "node_modules",
            "android",
            "ios",
            ".gradle",
            ".idea",
            ".vscode",
            "build",
            "dist",
        ],
        "protected_file_names": [
            "pagefile.sys",
            "hiberfil.sys",
            "swapfile.sys",
            "dumpstack.log.tmp",
        ],
        "safe_zone_names": [
            "downloads",
            "temp",
            "tmp",
            "cache",
            "caches",
            "cached",
            "cefcached",
            "gpucache",
            "dawncache",
            "code cache",
            "logs",
        ],
        "safe_junk_extensions": [
            ".tmp",
            ".temp",
        ],
        "review_extensions": [
            ".log",
            ".bak",
            ".old",
        ],
    },
    "browser_cache": {
        "path_templates": [
            "{LOCALAPPDATA}/Google/Chrome/User Data/Default/Cache",
            "{LOCALAPPDATA}/Google/Chrome/User Data/Default/Code Cache",
            "{LOCALAPPDATA}/Microsoft/Edge/User Data/Default/Cache",
            "{LOCALAPPDATA}/Microsoft/Edge/User Data/Default/Code Cache",
            "{LOCALAPPDATA}/BraveSoftware/Brave-Browser/User Data/Default/Cache",
            "{LOCALAPPDATA}/CocCoc/Browser/User Data/Default/Cache",
        ],
        "firefox_profiles_dir": "{APPDATA}/Mozilla/Firefox/Profiles",
        "firefox_cache_dirs": [
            "cache2",
        ],
        "cache_dir_names": [
            "cache",
            "cache2",
            "cached",
            "cefcached",
            "gpucache",
            "dawncache",
            "code cache",
        ],
        "path_hints": [
            ["google", "chrome", "user data"],
            ["microsoft", "edge", "user data"],
            ["bravesoftware", "brave-browser", "user data"],
            ["coccoc", "browser", "user data"],
            ["mozilla", "firefox", "profiles"],
        ],
    },
    "download_organizer": {
        "temporary_extensions": [
            ".crdownload",
            ".part",
            ".tmp",
            ".download",
            ".idownload",
        ],
        "file_categories": {
            "Anh": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"],
            "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"],
            "Tai_lieu": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"],
            "Nen": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".java", ".json", ".xml", ".sql"],
            "Cai_dat": [".exe", ".msi", ".apk", ".iso"],
        },
    },
    "download_watcher": {
        "scan_interval_seconds": 5,
        "wait_after_event_seconds": 2,
        "stable_check_interval_seconds": 1,
        "stable_check_times": 3,
        "temporary_extensions": [
            ".crdownload",
            ".part",
            ".tmp",
            ".download",
            ".idownload",
        ],
        "file_categories": {
            "Anh": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"],
            "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"],
            "Tai_lieu": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"],
            "File_nen": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".java", ".json", ".xml", ".sql", ".php", ".cs"],
            "Cai_dat": [".exe", ".msi", ".apk", ".iso"],
        },
    },
    "media_organizer": {
        "target_folder_name": "Tat_ca_media",
        "media_extensions": [
            ".mp4",
            ".mkv",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".mp3",
            ".wav",
            ".flac",
            ".aac",
            ".m4a",
        ],
    },
    "wiztree": {
        "enabled": True,
        "exe_path": r"D:\WizTree\WizTree\WizTree64.exe",
        "export_dir": "{BASE_DIR}/data/wiztree_exports",
        "use_admin": False,
        "timeout_seconds": 300,
        "prefer_for_system_advisor": False,
    },
    "external_apps": {
        "enabled": True,
        "default_timeout_seconds": 30,
        "paths": {
            "everything_app": r"D:\SearchEverything\Everything\Everything.exe",
            "everything_cli": r"{BASE_DIR}\external\everything\es.exe",
            "seven_zip": r"C:\Program Files\7-Zip\7z.exe",
            "smartctl": r"C:\Program Files\smartmontools\bin\smartctl.exe",
            "crystaldiskinfo": r"C:\Program Files\CrystalDiskInfo\DiskInfo64.exe",
            "exiftool": r"{BASE_DIR}\external\exiftool\exiftool.exe",
            "ffmpeg": r"{BASE_DIR}\external\ffmpeg\bin\ffmpeg.exe",
            "ffprobe": r"{BASE_DIR}\external\ffmpeg\bin\ffprobe.exe",
            "rclone": r"{BASE_DIR}\external\rclone\rclone.exe",
            "sysinternals_autoruns": r"{BASE_DIR}\external\sysinternals\autorunsc64.exe",
            "sysinternals_handle": r"{BASE_DIR}\external\sysinternals\handle64.exe",
            "sysinternals_procexp": r"{BASE_DIR}\external\sysinternals\procexp64.exe",
            "sysinternals_rammap": r"{BASE_DIR}\external\sysinternals\RAMMap64.exe",
            "sysinternals_du": r"{BASE_DIR}\external\sysinternals\du64.exe",
            "sysinternals_sigcheck": r"{BASE_DIR}\external\sysinternals\sigcheck64.exe",
        },
    },
}


def merge_settings(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults)

    for key, value in overrides.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = merge_settings(merged[key], value)
        else:
            merged[key] = value

    return merged


def ensure_user_settings_file() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if USER_SETTINGS_FILE.exists():
        return

    with USER_SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(DEFAULT_USER_SETTINGS, file, ensure_ascii=False, indent=4)


def load_user_settings() -> dict[str, Any]:
    ensure_user_settings_file()

    try:
        with USER_SETTINGS_FILE.open("r", encoding="utf-8") as file:
            user_settings = json.load(file)
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_USER_SETTINGS)

    if not isinstance(user_settings, dict):
        return deepcopy(DEFAULT_USER_SETTINGS)

    return merge_settings(DEFAULT_USER_SETTINGS, user_settings)


USER_SETTINGS = load_user_settings()


def get_setting(path: str, default: Any = None) -> Any:
    current: Any = USER_SETTINGS

    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]

    return current


def get_setting_list(path: str) -> list:
    value = get_setting(path, [])
    return value if isinstance(value, list) else []


def get_setting_dict(path: str) -> dict:
    value = get_setting(path, {})
    return value if isinstance(value, dict) else {}


def get_int_setting(path: str, default: int) -> int:
    try:
        return int(get_setting(path, default))
    except (TypeError, ValueError):
        return default


def get_bool_setting(path: str, default: bool) -> bool:
    value = get_setting(path, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    return bool(value)


def normalize_extensions(values: list[str]) -> set[str]:
    return {
        item.lower() if item.startswith(".") else f".{item.lower()}"
        for item in values
        if isinstance(item, str) and item.strip()
    }


def normalize_category_map(path: str) -> dict[str, set[str]]:
    categories = get_setting_dict(path)
    return {
        str(category): normalize_extensions(extensions)
        for category, extensions in categories.items()
        if isinstance(extensions, list)
    }


def expand_config_path(template: str) -> Path:
    variables = {
        "APPDATA": os.environ.get("APPDATA", ""),
        "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
        "HOME": str(Path.home()),
        "BASE_DIR": str(BASE_DIR),
    }
    try:
        rendered = template.format(**variables)
    except KeyError:
        rendered = template
    return Path(rendered)


def get_configured_browser_cache_paths() -> list[Path]:
    paths = [
        expand_config_path(template)
        for template in get_setting_list("browser_cache.path_templates")
    ]

    firefox_profiles_dir = expand_config_path(
        str(get_setting("browser_cache.firefox_profiles_dir", ""))
    )
    firefox_cache_dirs = get_setting_list("browser_cache.firefox_cache_dirs")

    if firefox_profiles_dir.exists():
        for profile in firefox_profiles_dir.iterdir():
            if profile.is_dir():
                for cache_dir in firefox_cache_dirs:
                    paths.append(profile / str(cache_dir))

    return paths


def validate_user_settings() -> dict[str, Any]:
    issues = []
    warnings = []

    downloads_folder = Path(str(get_setting("paths.downloads_folder", "")))
    if not downloads_folder.exists():
        warnings.append(f"Downloads folder does not exist: {downloads_folder}")

    warning_percent = get_int_setting("thresholds.disk_warning_percent", 80)
    critical_percent = get_int_setting("thresholds.disk_critical_percent", 90)
    if warning_percent >= critical_percent:
        issues.append("disk_warning_percent must be lower than disk_critical_percent")

    result_limit = get_int_setting("thresholds.result_limit", 50)
    if result_limit <= 0:
        issues.append("result_limit must be greater than 0")

    large_file_mb = get_int_setting("thresholds.large_file_mb", 500)
    if large_file_mb <= 0:
        issues.append("large_file_mb must be greater than 0")

    wiztree_enabled = get_bool_setting("wiztree.enabled", False)
    wiztree_exe = Path(str(get_setting("wiztree.exe_path", "")))
    if wiztree_enabled and not wiztree_exe.exists():
        warnings.append(f"WizTree executable does not exist: {wiztree_exe}")

    if get_bool_setting("external_apps.enabled", True):
        external_app_paths = get_setting_dict("external_apps.paths")
        for app_name, raw_path in external_app_paths.items():
            app_path = expand_config_path(str(raw_path))
            if not app_path.exists():
                warnings.append(f"External app does not exist: {app_name} -> {app_path}")

    return {
        "status": "valid" if not issues else "invalid",
        "config_file": str(USER_SETTINGS_FILE),
        "issues": issues,
        "warnings": warnings,
    }


def get_config_snapshot() -> dict[str, Any]:
    return {
        "config_file": str(USER_SETTINGS_FILE),
        "base_dir": str(BASE_DIR),
        "reports_dir": str(REPORTS_DIR),
        "logs_dir": str(LOGS_DIR),
        "backups_dir": str(BACKUPS_DIR),
        "data_dir": str(DATA_DIR),
        "paths": USER_SETTINGS["paths"],
        "thresholds": USER_SETTINGS["thresholds"],
        "watcher": {
            "scan_interval_seconds": WATCHER_SCAN_INTERVAL,
            "wait_after_event_seconds": WATCHER_WAIT_AFTER_EVENT_SECONDS,
            "stable_check_interval_seconds": WATCHER_STABLE_CHECK_INTERVAL,
            "stable_check_times": WATCHER_STABLE_CHECK_TIMES,
        },
        "browser_cache_path_count": len(get_setting_list("browser_cache.path_templates")),
        "protected_root_count": len(PROTECTED_ROOT_PATHS),
        "protected_dir_count": len(PROTECTED_DIR_NAMES),
        "guarded_dir_count": len(GUARDED_DIR_NAMES),
        "dev_artifact_dir_count": len(DEV_ARTIFACT_DIR_NAMES),
        "wiztree": {
            "enabled": WIZTREE_ENABLED,
            "exe_path": str(WIZTREE_EXE_PATH),
            "available": WIZTREE_EXE_PATH.exists(),
            "export_dir": str(WIZTREE_EXPORT_DIR),
            "prefer_for_system_advisor": WIZTREE_PREFER_FOR_SYSTEM_ADVISOR,
        },
        "external_apps": {
            "enabled": EXTERNAL_APPS_ENABLED,
            "configured_count": len(EXTERNAL_APP_PATHS),
            "available_count": sum(1 for path in EXTERNAL_APP_PATHS.values() if path.exists()),
            "paths": {name: str(path) for name, path in EXTERNAL_APP_PATHS.items()},
        },
    }

# =========================
# DEFAULT SCAN SETTINGS
# =========================

DEFAULT_SCAN_FOLDER = str(get_setting("paths.default_scan_folder", r"D:\\"))

DEFAULT_DOWNLOAD_FOLDER = str(get_setting("paths.downloads_folder", r"D:\Downloads"))

DEFAULT_LARGE_FILE_MB = get_int_setting("thresholds.large_file_mb", 500)

DEFAULT_RESULT_LIMIT = get_int_setting("thresholds.result_limit", 50)

DISK_WARNING_PERCENT = get_int_setting("thresholds.disk_warning_percent", 80)
DISK_CRITICAL_PERCENT = get_int_setting("thresholds.disk_critical_percent", 90)
RAM_WARNING_PERCENT = get_int_setting("thresholds.ram_warning_percent", 70)
RAM_CRITICAL_PERCENT = get_int_setting("thresholds.ram_critical_percent", 85)

# =========================
# SAFETY SETTINGS
# =========================

SAFE_SYSTEM_FOLDERS = get_setting_list("safety.protected_dir_names")
SAFE_SYSTEM_FILES = get_setting_list("safety.protected_file_names")

PROTECTED_ROOT_PATHS = [
    expand_config_path(str(item))
    for item in get_setting_list("safety.protected_root_paths")
]
PROTECTED_DIR_NAMES = {
    str(item).lower()
    for item in get_setting_list("safety.protected_dir_names")
}
GUARDED_DIR_NAMES = {
    str(item).lower()
    for item in get_setting_list("safety.guarded_dir_names")
}
DEV_ARTIFACT_DIR_NAMES = {
    str(item).lower()
    for item in get_setting_list("safety.dev_artifact_dir_names")
}
PROTECTED_FILE_NAMES = {
    str(item).lower()
    for item in get_setting_list("safety.protected_file_names")
}
SAFE_ZONE_NAMES = {
    str(item).lower()
    for item in get_setting_list("safety.safe_zone_names")
}
SAFE_JUNK_EXTENSIONS = normalize_extensions(get_setting_list("safety.safe_junk_extensions"))
REVIEW_EXTENSIONS = normalize_extensions(get_setting_list("safety.review_extensions"))

BROWSER_CACHE_DIR_NAMES = {
    str(item).lower()
    for item in get_setting_list("browser_cache.cache_dir_names")
}
BROWSER_PATH_HINTS = tuple(
    {str(part).lower() for part in hint}
    for hint in get_setting_list("browser_cache.path_hints")
    if isinstance(hint, list)
)

# =========================
# WATCHER SETTINGS
# =========================

WATCHER_SCAN_INTERVAL = get_int_setting("download_watcher.scan_interval_seconds", 5)
WATCHER_WAIT_AFTER_EVENT_SECONDS = get_int_setting("download_watcher.wait_after_event_seconds", 2)
WATCHER_STABLE_CHECK_INTERVAL = get_int_setting("download_watcher.stable_check_interval_seconds", 1)
WATCHER_STABLE_CHECK_TIMES = get_int_setting("download_watcher.stable_check_times", 3)
DOWNLOAD_WATCHER_TEMP_EXTENSIONS = normalize_extensions(
    get_setting_list("download_watcher.temporary_extensions")
)
DOWNLOAD_WATCHER_FILE_CATEGORIES = normalize_category_map("download_watcher.file_categories")
DOWNLOAD_ORGANIZER_TEMP_EXTENSIONS = normalize_extensions(
    get_setting_list("download_organizer.temporary_extensions")
)
DOWNLOAD_ORGANIZER_FILE_CATEGORIES = normalize_category_map("download_organizer.file_categories")
MEDIA_ORGANIZER_TARGET_FOLDER_NAME = str(
    get_setting("media_organizer.target_folder_name", "Tat_ca_media")
)
MEDIA_EXTENSIONS = normalize_extensions(get_setting_list("media_organizer.media_extensions"))

# =========================
# WIZTREE SETTINGS
# =========================

WIZTREE_ENABLED = get_bool_setting("wiztree.enabled", True)
WIZTREE_EXE_PATH = Path(str(get_setting("wiztree.exe_path", r"D:\WizTree\WizTree\WizTree64.exe")))
WIZTREE_EXPORT_DIR = expand_config_path(str(get_setting("wiztree.export_dir", "{BASE_DIR}/data/wiztree_exports")))
WIZTREE_USE_ADMIN = get_bool_setting("wiztree.use_admin", False)
WIZTREE_TIMEOUT_SECONDS = get_int_setting("wiztree.timeout_seconds", 300)
WIZTREE_PREFER_FOR_SYSTEM_ADVISOR = get_bool_setting("wiztree.prefer_for_system_advisor", False)

WIZTREE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# EXTERNAL APP SETTINGS
# =========================

EXTERNAL_APPS_ENABLED = get_bool_setting("external_apps.enabled", True)
EXTERNAL_APP_TIMEOUT_SECONDS = get_int_setting("external_apps.default_timeout_seconds", 30)
EXTERNAL_APP_PATHS = {
    name: expand_config_path(str(path))
    for name, path in get_setting_dict("external_apps.paths").items()
}

# =========================
# LOG SETTINGS
# =========================

ENABLE_ACTION_LOG = True

ENABLE_JSON_REPORT = True
