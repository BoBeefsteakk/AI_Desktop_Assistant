from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import REPORTS_DIR

REPORT_INDEX_FILE = REPORTS_DIR / "report_index.jsonl"


def append_report_index(
    report_path: Path,
    tool_name: str,
    status: str,
    created_at: str,
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "created_at": created_at,
        "tool": tool_name,
        "status": status,
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
) -> Path:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    created_at_iso = datetime.now().isoformat(timespec="seconds")

    report_data = {
        "schema_version": 1,
        "tool": tool_name,
        "created_at": timestamp,
        "created_at_iso": created_at_iso,
        "status": status,
        "input": input_data,
        "results": results,
        "recommendations": recommendations or [],
    }

    report_path = make_report_path(tool_name, timestamp)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4, ensure_ascii=False)

    append_report_index(
        report_path=report_path,
        tool_name=tool_name,
        status=status,
        created_at=created_at_iso,
    )

    return report_path


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
        ]
    )

    print(f"Report created: {report}")
