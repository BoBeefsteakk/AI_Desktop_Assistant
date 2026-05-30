from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import REPORTS_DIR

REPORT_SCHEMA_VERSION = 2
REPORT_INDEX_FILE = REPORTS_DIR / "report_index.jsonl"
REQUIRED_REPORT_FIELDS = {
    "schema_version",
    "tool",
    "action",
    "risk_level",
    "created_at",
    "created_at_iso",
    "status",
    "summary",
    "input",
    "results",
    "manifest",
    "undo_available",
    "recommendations",
    "tags",
}


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]

    if isinstance(value, set):
        return sorted(to_jsonable(item) for item in value)

    return value


def extract_count_fields(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    summary = {}
    for key, item in value.items():
        if key in {"total", "passed", "failed"} or key.endswith("_count"):
            summary[key] = item

    return summary


def build_summary(
    status: str,
    results: Any,
    recommendations: list[str] | None,
    manifest: str | None,
    undo_available: bool,
) -> dict[str, Any]:
    summary = {
        "status": status,
        "result_type": type(results).__name__,
        "recommendation_count": len(recommendations or []),
        "undo_available": undo_available,
    }

    if isinstance(results, list):
        summary["item_count"] = len(results)
    elif isinstance(results, dict):
        summary.update(extract_count_fields(results))

    if manifest:
        summary["manifest"] = manifest

    return summary


def infer_manifest(results: Any) -> str | None:
    if not isinstance(results, dict):
        return None

    manifest = results.get("manifest")
    if manifest:
        return str(manifest)

    for key in ("restore", "preview"):
        nested = results.get(key)
        if isinstance(nested, dict) and nested.get("manifest"):
            return str(nested["manifest"])

    return None


def append_report_index(
    report_path: Path,
    tool_name: str,
    action: str,
    status: str,
    created_at: str,
    risk_level: str,
    summary: dict[str, Any],
    manifest: str | None,
    undo_available: bool,
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "created_at": created_at,
        "tool": tool_name,
        "action": action,
        "status": status,
        "risk_level": risk_level,
        "summary": summary,
        "manifest": manifest,
        "undo_available": undo_available,
        "report_path": str(report_path),
    }

    with REPORT_INDEX_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_recent_report_index(limit: int = 50) -> list[dict[str, Any]]:
    if not REPORT_INDEX_FILE.exists():
        return []

    with REPORT_INDEX_FILE.open("r", encoding="utf-8") as file:
        lines = file.readlines()

    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return records


def make_report_path(tool_name: str, timestamp: str) -> Path:
    report_path = REPORTS_DIR / f"{tool_name}_{timestamp}.json"

    if not report_path.exists():
        return report_path

    count = 1
    while True:
        candidate = REPORTS_DIR / f"{tool_name}_{timestamp}_{count}.json"
        if not candidate.exists():
            return candidate
        count += 1


def create_report(
    tool_name: str,
    status: str,
    input_data: dict,
    results,
    recommendations: list[str] | None = None,
    *,
    action: str | None = None,
    risk_level: str = "unknown",
    summary: dict[str, Any] | None = None,
    manifest: str | Path | None = None,
    undo_available: bool | None = None,
    tags: list[str] | None = None,
) -> Path:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    created_at_iso = datetime.now().isoformat(timespec="seconds")
    action_name = action or "run"
    manifest_path = str(manifest) if manifest else infer_manifest(results)
    can_undo = bool(manifest_path) if undo_available is None else undo_available
    report_summary = summary or build_summary(
        status=status,
        results=results,
        recommendations=recommendations,
        manifest=manifest_path,
        undo_available=can_undo,
    )

    report_data = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": tool_name,
        "action": action_name,
        "risk_level": risk_level,
        "created_at": timestamp,
        "created_at_iso": created_at_iso,
        "status": status,
        "summary": to_jsonable(report_summary),
        "input": to_jsonable(input_data),
        "results": to_jsonable(results),
        "manifest": manifest_path,
        "undo_available": can_undo,
        "recommendations": to_jsonable(recommendations or []),
        "tags": to_jsonable(tags or []),
    }

    report_path = make_report_path(tool_name, timestamp)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4, ensure_ascii=False)

    append_report_index(
        report_path=report_path,
        tool_name=tool_name,
        action=action_name,
        status=status,
        created_at=created_at_iso,
        risk_level=risk_level,
        summary=report_data["summary"],
        manifest=manifest_path,
        undo_available=can_undo,
    )

    return report_path


def validate_report_data(report_data: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_REPORT_FIELDS - set(report_data))
    issues = []

    if missing:
        issues.append(f"Missing fields: {missing}")

    if report_data.get("schema_version") != REPORT_SCHEMA_VERSION:
        issues.append(
            f"schema_version must be {REPORT_SCHEMA_VERSION}, "
            f"got {report_data.get('schema_version')}"
        )

    if not isinstance(report_data.get("summary"), dict):
        issues.append("summary must be a dict")

    if not isinstance(report_data.get("recommendations"), list):
        issues.append("recommendations must be a list")

    if not isinstance(report_data.get("tags"), list):
        issues.append("tags must be a list")

    return {
        "status": "valid" if not issues else "invalid",
        "issues": issues,
    }


def validate_report_file(report_path: str | Path) -> dict[str, Any]:
    path = Path(report_path)

    if not path.exists():
        return {
            "status": "missing",
            "report_path": str(path),
            "issues": ["Report file does not exist."],
        }

    try:
        with path.open("r", encoding="utf-8") as file:
            report_data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "report_path": str(path),
            "issues": [str(exc)],
        }

    result = validate_report_data(report_data)
    result["report_path"] = str(path)
    return result


if __name__ == "__main__":
    report = create_report(
        tool_name="test_report_manager",
        status="success",
        input_data={
            "test": True
        },
        results=[
            {
                "message": "Report manager working"
            }
        ],
        recommendations=[
            "Everything is OK."
        ],
        action="self_test",
        risk_level="safe",
        summary={
            "message": "Report manager working",
        },
        tags=["core", "self_test"],
    )

    print(f"Report created: {report}")
