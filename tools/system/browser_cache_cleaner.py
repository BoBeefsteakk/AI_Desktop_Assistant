from __future__ import annotations

from pathlib import Path

from config.settings import get_configured_browser_cache_paths
from tools.core.safety_utils import format_size, ask_yes_no, save_report
from tools.core.report_manager import create_report
from tools.core.assistant_logger import log_action
from tools.core.risk_classifier import classify_file_risk, PROTECTED
from tools.core.safe_executor import safe_delete

def get_browser_cache_paths() -> list[Path]:
    paths = get_configured_browser_cache_paths()
    return [path for path in paths if path.exists()]

def folder_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except (PermissionError, OSError):
            continue
    return total

def scan_browser_cache() -> list[dict]:
    results = []
    for path in get_browser_cache_paths():
        size = folder_size(path)
        risk_data = classify_file_risk(path)
        results.append({
            "path": str(path),
            "size": size,
            "risk": risk_data["risk"],
            "risk_reason": risk_data["reason"],
        })
    return results

def show_browser_cache(results: list[dict]) -> None:
    print("\n========== BROWSER CACHE ==========")
    total = sum(x["size"] for x in results)

    if not results:
        print("Khong tim thay cache browser.")
        return

    for i, item in enumerate(results, start=1):
        print(
            f"{i:>2}. {format_size(item['size']):>10} | "
            f"{item['risk']:<18} | {item['path']}"
        )

    print("-" * 80)
    print(f"Tong cache: {format_size(total)}")

def list_cache_entries(cache_path: Path) -> list[Path]:
    try:
        return [
            item for item in cache_path.iterdir()
            if item.exists()
        ]
    except (PermissionError, OSError):
        return []

def clean_browser_cache() -> None:
    results = scan_browser_cache()
    show_browser_cache(results)

    if not results:
        return

    blocked_folders = [
        item for item in results
        if item["risk"] == PROTECTED
    ]

    if blocked_folders:
        print("Co cache folder bi safety layer chan. Khong thuc hien cleanup.")
        log_action(
            "browser_cache_cleaner",
            "clean_browser_cache",
            "blocked",
            {"blocked_count": len(blocked_folders)},
        )
        return

    report = save_report("browser_cache_before_clean", results)
    print(f"Da luu report: {report}")
    print("Nen dong Chrome/Edge/Firefox truoc khi don cache.")

    if not ask_yes_no("Ban muon xoa cac thu muc cache nay?", default=False):
        print("Da huy.")
        log_action(
            "browser_cache_cleaner",
            "clean_browser_cache",
            "cancelled",
            {"cache_folder_count": len(results)},
        )
        return

    execution_results = []

    for item in results:
        cache_path = Path(item["path"])
        entries = list_cache_entries(cache_path)

        if not entries:
            execution_results.append({
                "path": str(cache_path),
                "status": "empty",
                "deleted_items": 0,
            })
            continue

        deleted_items = 0
        blocked_items = 0
        error_items = 0

        for entry in entries:
            result = safe_delete(entry)
            execution_results.append(result)

            if result["status"] == "deleted":
                deleted_items += 1
            elif result["status"] == "blocked":
                blocked_items += 1
            elif result["status"] == "error":
                error_items += 1

        cache_path.mkdir(parents=True, exist_ok=True)
        print(
            f"Da don: {cache_path} | "
            f"Deleted: {deleted_items} | Blocked: {blocked_items} | Errors: {error_items}"
        )

    deleted = sum(1 for item in execution_results if item["status"] == "deleted")
    blocked = sum(1 for item in execution_results if item["status"] == "blocked")
    errors = sum(1 for item in execution_results if item["status"] == "error")
    empty = sum(1 for item in execution_results if item["status"] == "empty")

    final_report = create_report(
        tool_name="browser_cache_cleaner",
        status="success",
        input_data={
            "cache_folder_count": len(results),
        },
        results={
            "deleted_count": deleted,
            "blocked_count": blocked,
            "error_count": errors,
            "empty_folder_count": empty,
            "cache_folders": results,
            "execution_results": execution_results,
        },
        recommendations=[
            "Cache entries were moved to Recycle Bin, not permanently deleted.",
            "If a browser was open, run the cleaner again after closing it.",
        ],
    )

    log_action(
        "browser_cache_cleaner",
        "clean_browser_cache",
        "success",
        {
            "deleted": deleted,
            "blocked": blocked,
            "errors": errors,
            "report": str(final_report),
        },
    )

    print(f"Report: {final_report}")

def run_browser_cache_cleaner() -> None:
    clean_browser_cache()

if __name__ == "__main__":
    run_browser_cache_cleaner()
