from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config.settings import REPORTS_DIR


def create_report(
    tool_name: str,
    status: str,
    input_data: dict,
    results,
    recommendations: list[str] | None = None,
) -> Path:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_data = {
        "tool": tool_name,
        "created_at": timestamp,
        "status": status,
        "input": input_data,
        "results": results,
        "recommendations": recommendations or [],
    }

    report_path = REPORTS_DIR / f"{tool_name}_{timestamp}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4, ensure_ascii=False)

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