from __future__ import annotations

from pathlib import Path

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