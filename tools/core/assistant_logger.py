from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any

from config.settings import LOGS_DIR

LOG_DIR = LOGS_DIR
LOG_FILE = LOG_DIR / "assistant_actions.jsonl"

def log_action(
    tool_name: str,
    action: str,
    status: str = "success",
    details: dict[str, Any] | None = None
) -> None:
    """
    Ghi log moi hanh dong cua assistant vao file JSONL.
    JSONL = moi dong la 1 JSON object, rat hop de feed AI sau nay.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "tool": tool_name,
        "action": action,
        "status": status,
        "details": details or {}
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_recent_logs(limit: int = 50) -> list[dict[str, Any]]:
    if not LOG_FILE.exists():
        return []

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return records

def show_recent_logs(limit: int = 30) -> None:
    logs = read_recent_logs(limit)

    if not logs:
        print("Chua co log nao.")
        return

    print("\n========== ASSISTANT LOGS ==========")
    for item in logs:
        print(
            f"[{item['time']}] "
            f"{item['tool']} | {item['action']} | {item['status']}"
        )
        if item.get("details"):
            print(f"  details: {item['details']}")

def export_logs_for_ai(output_file: str | None = None) -> None:
    """
    Xuat log thanh file .json de sau nay dua cho AI phan tich.
    """
    logs = read_recent_logs(limit=10000)

    if output_file is None:
        output_file = str(LOG_DIR / "assistant_logs_for_ai.json")

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    print(f"Da export log cho AI: {output_file}")

def run_assistant_logger() -> None:
    while True:
        print("""
========== ASSISTANT LOGGER ==========
1. Xem log gan day
2. Export log cho AI
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            limit = input("So log muon xem [30]: ").strip()
            show_recent_logs(int(limit) if limit.isdigit() else 30)

        elif choice == "2":
            export_logs_for_ai()

        elif choice == "0":
            break

        else:
            print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_assistant_logger()
