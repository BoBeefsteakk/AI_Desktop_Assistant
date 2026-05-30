from __future__ import annotations

from pathlib import Path

from config.settings import (
    BROWSER_CACHE_DIR_NAMES as CONFIG_BROWSER_CACHE_DIR_NAMES,
    BROWSER_PATH_HINTS as CONFIG_BROWSER_PATH_HINTS,
    PROTECTED_DIR_NAMES as CONFIG_PROTECTED_DIR_NAMES,
    PROTECTED_FILE_NAMES as CONFIG_PROTECTED_FILE_NAMES,
    REVIEW_EXTENSIONS as CONFIG_REVIEW_EXTENSIONS,
    SAFE_JUNK_EXTENSIONS as CONFIG_SAFE_JUNK_EXTENSIONS,
    SAFE_ZONE_NAMES as CONFIG_SAFE_ZONE_NAMES,
)


SAFE_DELETE = "safe_delete"
REVIEW_REQUIRED = "review_required"
PROTECTED = "protected"


PROTECTED_DIR_NAMES = set(CONFIG_PROTECTED_DIR_NAMES)
SAFE_ZONE_NAMES = set(CONFIG_SAFE_ZONE_NAMES)
BROWSER_CACHE_DIR_NAMES = set(CONFIG_BROWSER_CACHE_DIR_NAMES)
BROWSER_PATH_HINTS = tuple(CONFIG_BROWSER_PATH_HINTS)
DANGEROUS_FILE_NAMES = set(CONFIG_PROTECTED_FILE_NAMES)
SAFE_JUNK_EXTENSIONS = set(CONFIG_SAFE_JUNK_EXTENSIONS)
REVIEW_EXTENSIONS = set(CONFIG_REVIEW_EXTENSIONS)


def get_path_parts(path: Path) -> set[str]:
    return {part.lower() for part in path.parts}


def is_in_protected_zone(path: Path) -> bool:
    parts = get_path_parts(path)
    return any(name in parts for name in PROTECTED_DIR_NAMES)


def is_in_safe_zone(path: Path) -> bool:
    lower_path = str(path).lower()
    parts = get_path_parts(path)

    if any(name in parts for name in SAFE_ZONE_NAMES):
        return True

    return any(name in lower_path for name in SAFE_ZONE_NAMES)


def is_known_browser_cache_path(path: Path) -> bool:
    parts = get_path_parts(path)
    has_browser_hint = any(hint.issubset(parts) for hint in BROWSER_PATH_HINTS)
    has_cache_hint = any(name in parts for name in BROWSER_CACHE_DIR_NAMES)
    return has_browser_hint and has_cache_hint


def classify_file_risk(path: str | Path) -> dict:
    file_path = Path(path)
    lower_name = file_path.name.lower()
    lower_path = str(file_path).lower()
    suffix = file_path.suffix.lower()

    if lower_name in DANGEROUS_FILE_NAMES:
        return {
            "risk": PROTECTED,
            "reason": "File he thong hoac file dang duoc Windows su dung.",
        }

    if is_known_browser_cache_path(file_path):
        return {
            "risk": SAFE_DELETE,
            "reason": "Nam trong folder cache trinh duyet da biet.",
        }

    if is_in_protected_zone(file_path):
        return {
            "risk": PROTECTED,
            "reason": "Nam trong folder duoc bao ve, khong nen tu dong xu ly.",
        }

    if any(name in lower_path for name in ["cefcached", "gpucache", "dawncache", "code cache"]):
        return {
            "risk": SAFE_DELETE,
            "reason": "Nam trong folder cache ro rang.",
        }

    if is_in_safe_zone(file_path) and suffix in SAFE_JUNK_EXTENSIONS:
        return {
            "risk": SAFE_DELETE,
            "reason": "File tam nam trong vung an toan.",
        }

    if is_in_safe_zone(file_path) and suffix in REVIEW_EXTENSIONS:
        return {
            "risk": REVIEW_REQUIRED,
            "reason": "File co ve la rac/cache, nhung van can xem lai truoc khi xoa.",
        }

    if suffix in REVIEW_EXTENSIONS or suffix in SAFE_JUNK_EXTENSIONS:
        return {
            "risk": REVIEW_REQUIRED,
            "reason": "File co duoi nghi la rac, nhung khong nam trong vung an toan.",
        }

    return {
        "risk": REVIEW_REQUIRED,
        "reason": "Khong du thong tin de xoa tu dong.",
    }
