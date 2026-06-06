from __future__ import annotations

from pathlib import Path
from typing import Callable

import send2trash

from tools.core.risk_classifier import classify_file_risk, PROTECTED


def safe_delete(path: str | Path) -> dict:
    file_path = Path(path)

    if not file_path.exists():
        return {
            "path": str(file_path),
            "risk": "unknown",
            "reason": "File khong ton tai.",
            "status": "missing",
        }

    risk_data = classify_file_risk(file_path)

    result = {
        "path": str(file_path),
        "risk": risk_data["risk"],
        "reason": risk_data["reason"],
        "category": risk_data.get("category"),
        "matched_rule": risk_data.get("matched_rule"),
        "can_user_confirm": risk_data.get("can_user_confirm"),
        "status": "pending",
    }

    if risk_data["risk"] == PROTECTED:
        result["status"] = "blocked"
        return result

    try:
        send2trash.send2trash(str(file_path))
        result["status"] = "deleted"

    except Exception as error:
        result["status"] = "error"
        result["error"] = str(error)

    return result


def delete_managed_generated_file(
    path: str | Path,
    *,
    allowed_root: str | Path,
    marker_check: Callable[[Path], bool] | None = None,
) -> dict:
    file_path = Path(path)
    root_path = Path(allowed_root).resolve(strict=False)
    target_path = file_path.resolve(strict=False)

    result = {
        "path": str(file_path),
        "allowed_root": str(root_path),
        "status": "pending",
    }

    if not target_path.is_relative_to(root_path):
        result["status"] = "blocked"
        result["reason"] = "Target is outside the managed generated root."
        return result

    if not target_path.exists():
        result["status"] = "missing"
        result["reason"] = "Generated file does not exist."
        return result

    if not target_path.is_file():
        result["status"] = "blocked"
        result["reason"] = "Target is not a generated file."
        return result

    if marker_check is not None and not marker_check(target_path):
        result["status"] = "blocked"
        result["reason"] = "Generated marker check failed."
        return result

    try:
        target_path.unlink()
        result["status"] = "deleted"
    except OSError as error:
        result["status"] = "error"
        result["error"] = str(error)

    return result


def remove_empty_managed_dirs(root: str | Path) -> list[dict]:
    root_path = Path(root).resolve(strict=False)
    if not root_path.exists():
        return []

    removed = []
    for path in sorted(root_path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not path.is_dir():
            continue

        target_path = path.resolve(strict=False)
        if not target_path.is_relative_to(root_path):
            continue

        try:
            target_path.rmdir()
        except OSError:
            continue

        removed.append({
            "path": str(path),
            "status": "deleted_empty_dir",
        })

    return removed
