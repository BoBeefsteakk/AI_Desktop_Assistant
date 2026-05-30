from __future__ import annotations

from typing import Any

from tools.core.assistant_logger import read_recent_logs
from tools.core.report_manager import create_report, read_recent_report_index


def get_audit_snapshot(limit: int = 50) -> dict[str, Any]:
    logs = read_recent_logs(limit=limit)
    reports = read_recent_report_index(limit=limit)

    return {
        "log_count": len(logs),
        "report_count": len(reports),
        "logs": logs,
        "reports": reports,
    }


def show_audit_summary(limit: int = 30) -> None:
    snapshot = get_audit_snapshot(limit=limit)

    print("\n========== AUDIT CENTER ==========")
    print(f"Recent logs   : {snapshot['log_count']}")
    print(f"Recent reports: {snapshot['report_count']}")

    if snapshot["reports"]:
        print("\nReports:")
        for item in snapshot["reports"]:
            print(
                f"[{item.get('created_at')}] "
                f"{item.get('tool')} | {item.get('status')} | {item.get('report_path')}"
            )

    if snapshot["logs"]:
        print("\nLogs:")
        for item in snapshot["logs"]:
            print(
                f"[{item.get('time')}] "
                f"{item.get('tool')} | {item.get('action')} | {item.get('status')}"
            )


def export_audit_snapshot(limit: int = 200) -> dict[str, Any]:
    snapshot = get_audit_snapshot(limit=limit)

    report = create_report(
        tool_name="audit_center",
        status="success",
        input_data={
            "limit": limit,
        },
        results=snapshot,
        recommendations=[
            "Use this audit snapshot as the first feed source for assistant context.",
            "Inspect report_path entries for detailed tool outputs.",
        ],
    )

    print(f"Audit report: {report}")
    return {
        "status": "success",
        "report": str(report),
        "log_count": snapshot["log_count"],
        "report_count": snapshot["report_count"],
    }


def run_audit_center() -> None:
    while True:
        print("""
========== AUDIT CENTER ==========
1. Xem audit summary
2. Xuat audit snapshot report
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            raw_limit = input("So item muon xem [30]: ").strip()
            limit = int(raw_limit) if raw_limit.isdigit() else 30
            show_audit_summary(limit=limit)

        elif choice == "2":
            raw_limit = input("So item muon export [200]: ").strip()
            limit = int(raw_limit) if raw_limit.isdigit() else 200
            export_audit_snapshot(limit=limit)

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")


if __name__ == "__main__":
    run_audit_center()
