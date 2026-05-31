from __future__ import annotations

from pathlib import Path

from config.settings import (
    BROWSER_CACHE_DIR_NAMES as CONFIG_BROWSER_CACHE_DIR_NAMES,
    BROWSER_PATH_HINTS as CONFIG_BROWSER_PATH_HINTS,
    DEV_ARTIFACT_DIR_NAMES as CONFIG_DEV_ARTIFACT_DIR_NAMES,
    GUARDED_DIR_NAMES as CONFIG_GUARDED_DIR_NAMES,
    PROTECTED_DIR_NAMES as CONFIG_PROTECTED_DIR_NAMES,
    PROTECTED_FILE_NAMES as CONFIG_PROTECTED_FILE_NAMES,
    PROTECTED_ROOT_PATHS as CONFIG_PROTECTED_ROOT_PATHS,
    REVIEW_EXTENSIONS as CONFIG_REVIEW_EXTENSIONS,
    SAFE_JUNK_EXTENSIONS as CONFIG_SAFE_JUNK_EXTENSIONS,
    SAFE_ZONE_NAMES as CONFIG_SAFE_ZONE_NAMES,
)


SAFE_DELETE = "safe_delete"
REVIEW_REQUIRED = "review_required"
PROTECTED = "protected"


PROTECTED_ROOT_PATHS = tuple(CONFIG_PROTECTED_ROOT_PATHS)
PROTECTED_DIR_NAMES = set(CONFIG_PROTECTED_DIR_NAMES)
GUARDED_DIR_NAMES = set(CONFIG_GUARDED_DIR_NAMES)
DEV_ARTIFACT_DIR_NAMES = set(CONFIG_DEV_ARTIFACT_DIR_NAMES)
SAFE_ZONE_NAMES = set(CONFIG_SAFE_ZONE_NAMES)
BROWSER_CACHE_DIR_NAMES = set(CONFIG_BROWSER_CACHE_DIR_NAMES)
BROWSER_PATH_HINTS = tuple(CONFIG_BROWSER_PATH_HINTS)
DANGEROUS_FILE_NAMES = set(CONFIG_PROTECTED_FILE_NAMES)
SAFE_JUNK_EXTENSIONS = set(CONFIG_SAFE_JUNK_EXTENSIONS)
REVIEW_EXTENSIONS = set(CONFIG_REVIEW_EXTENSIONS)
CLEAR_CACHE_HINTS = {"cefcached", "gpucache", "dawncache", "code cache"}


def risk_result(
    risk: str,
    reason: str,
    category: str,
    matched_rule: str,
) -> dict:
    return {
        "risk": risk,
        "reason": reason,
        "category": category,
        "matched_rule": matched_rule,
        "can_auto_delete": risk == SAFE_DELETE,
        "can_user_confirm": risk != PROTECTED,
        "requires_review": risk == REVIEW_REQUIRED,
        "blocked": risk == PROTECTED,
    }


def resolve_path(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError:
        return path.absolute()


def is_same_or_child(path: Path, root: Path) -> bool:
    resolved_path = resolve_path(path)
    resolved_root = resolve_path(root)
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def get_path_parts(path: Path) -> set[str]:
    return {part.lower() for part in path.parts}


def get_matching_path_part(path: Path, names: set[str]) -> str | None:
    parts = get_path_parts(path)
    for name in sorted(names):
        if name in parts:
            return name
    return None


def get_matching_protected_root(path: Path) -> str | None:
    for root in PROTECTED_ROOT_PATHS:
        if is_same_or_child(path, root):
            return str(resolve_path(root))
    return None


def is_in_protected_zone(path: Path) -> bool:
    return (
        get_matching_protected_root(path) is not None
        or get_matching_path_part(path, PROTECTED_DIR_NAMES) is not None
    )


def is_in_safe_zone(path: Path) -> bool:
    lower_path = str(path).lower()
    parts = get_path_parts(path)

    if any(name in parts for name in SAFE_ZONE_NAMES):
        return True

    return any(name in lower_path for name in SAFE_ZONE_NAMES if " " in name)


def is_known_browser_cache_path(path: Path) -> bool:
    parts = get_path_parts(path)
    has_browser_hint = any(hint.issubset(parts) for hint in BROWSER_PATH_HINTS)
    has_cache_hint = any(name in parts for name in BROWSER_CACHE_DIR_NAMES)
    return has_browser_hint and has_cache_hint


def is_clear_cache_path(path: Path) -> bool:
    lower_path = str(path).lower()
    parts = get_path_parts(path)
    return any(name in parts or name in lower_path for name in CLEAR_CACHE_HINTS)


def classify_file_risk(path: str | Path) -> dict:
    file_path = Path(path)
    lower_name = file_path.name.lower()
    suffix = file_path.suffix.lower()

    if lower_name in DANGEROUS_FILE_NAMES:
        return risk_result(
            risk=PROTECTED,
            reason="File he thong hoac file dang duoc Windows su dung.",
            category="protected_system_file",
            matched_rule=f"protected_file_names:{lower_name}",
        )

    if is_known_browser_cache_path(file_path):
        return risk_result(
            risk=SAFE_DELETE,
            reason="Nam trong folder cache trinh duyet da biet.",
            category="safe_browser_cache",
            matched_rule="browser_cache.path_hints+cache_dir_names",
        )

    protected_root = get_matching_protected_root(file_path)
    if protected_root:
        return risk_result(
            risk=PROTECTED,
            reason="Nam trong root cua tool/project duoc bao ve.",
            category="protected_project_root",
            matched_rule=f"protected_root_paths:{protected_root}",
        )

    protected_part = get_matching_path_part(file_path, PROTECTED_DIR_NAMES)
    if protected_part:
        return risk_result(
            risk=PROTECTED,
            reason="Nam trong folder he thong hoac metadata duoc bao ve.",
            category="protected_system_dir",
            matched_rule=f"protected_dir_names:{protected_part}",
        )

    if is_clear_cache_path(file_path):
        return risk_result(
            risk=SAFE_DELETE,
            reason="Nam trong folder cache ro rang.",
            category="safe_cache",
            matched_rule="clear_cache_hints",
        )

    if is_in_safe_zone(file_path) and suffix in SAFE_JUNK_EXTENSIONS:
        return risk_result(
            risk=SAFE_DELETE,
            reason="File tam nam trong vung an toan.",
            category="safe_temp_file",
            matched_rule=f"safe_zone_names+safe_junk_extensions:{suffix}",
        )

    if is_in_safe_zone(file_path) and suffix in REVIEW_EXTENSIONS:
        return risk_result(
            risk=REVIEW_REQUIRED,
            reason="File co ve la rac/cache, nhung van can xem lai truoc khi xoa.",
            category="review_safe_zone_file",
            matched_rule=f"safe_zone_names+review_extensions:{suffix}",
        )

    guarded_part = get_matching_path_part(file_path, GUARDED_DIR_NAMES)
    if guarded_part:
        return risk_result(
            risk=REVIEW_REQUIRED,
            reason="Nam trong folder du lieu/app can review thu cong, khong auto cleanup.",
            category="review_guarded_dir",
            matched_rule=f"guarded_dir_names:{guarded_part}",
        )

    dev_part = get_matching_path_part(file_path, DEV_ARTIFACT_DIR_NAMES)
    if dev_part:
        return risk_result(
            risk=REVIEW_REQUIRED,
            reason="Nam trong folder dev/build artifact. Co the don, nhung can user chon ro.",
            category="review_dev_artifact",
            matched_rule=f"dev_artifact_dir_names:{dev_part}",
        )

    if suffix in REVIEW_EXTENSIONS or suffix in SAFE_JUNK_EXTENSIONS:
        return risk_result(
            risk=REVIEW_REQUIRED,
            reason="File co duoi nghi la rac, nhung khong nam trong vung an toan.",
            category="review_extension_only",
            matched_rule=f"extension:{suffix}",
        )

    return risk_result(
        risk=REVIEW_REQUIRED,
        reason="Khong du thong tin de xoa tu dong.",
        category="review_unknown",
        matched_rule="default_review",
    )
