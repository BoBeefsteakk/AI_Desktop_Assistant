from __future__ import annotations

from pathlib import Path


SAFE_DELETE = "safe_delete"
REVIEW_REQUIRED = "review_required"
PROTECTED = "protected"


PROTECTED_DIR_NAMES = {
    "$recycle.bin",
    "system volume information",
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    ".git",
    "__pycache__",
    "node_modules",
    "android",
    "ios",
    ".gradle",
    ".idea",
    ".vscode",
    "build",
    "dist",
    "riot games",
    "league of legends",
    "leagueoflegends",
    "league_of_legends",
    "lol",
    "garena",
    "fc online",
    "fco",
    "ea sports fc online",
    "mobile",
    "zalo data",
    "tool",
    "ai_desktop_assistant",
    "ai_desktop_assistant_optimized",
    "c nang cao",
    "hocmay",
    "cứu",
}

SAFE_ZONE_NAMES = {
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
}

DANGEROUS_FILE_NAMES = {
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
    "dumpstack.log.tmp",
}

SAFE_JUNK_EXTENSIONS = {
    ".tmp",
    ".temp",
}

REVIEW_EXTENSIONS = {
    ".log",
    ".bak",
    ".old",
}


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