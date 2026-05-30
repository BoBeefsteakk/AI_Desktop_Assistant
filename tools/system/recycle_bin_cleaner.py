from __future__ import annotations

try:
    import winshell
except ImportError:
    winshell = None

from tools.core.assistant_logger import log_action
from tools.core.report_manager import create_report
from tools.core.safety_utils import ask_yes_no, format_size


def scan_recycle_bin() -> dict:
    if winshell is None:
        return {
            "available": False,
            "items": [],
            "item_count": 0,
            "total_size": 0,
            "error": "winshell is not installed.",
        }

    recycle_bin = winshell.recycle_bin()
    items = []
    total_size = 0

    try:
        for entry in recycle_bin.items():
            try:
                size = entry.getsize()
                recycle_date = entry.recycle_date()

                items.append({
                    "original_path": str(entry.original_filename()),
                    "recycle_bin_path": str(entry.real_filename()),
                    "size": size,
                    "recycled_at": recycle_date.isoformat()
                    if hasattr(recycle_date, "isoformat")
                    else str(recycle_date),
                })
                total_size += size

            except Exception as item_error:
                items.append({
                    "original_path": str(entry.as_string()),
                    "recycle_bin_path": "",
                    "size": 0,
                    "recycled_at": "",
                    "error": str(item_error),
                })

    except Exception as error:
        return {
            "available": False,
            "items": items,
            "item_count": len(items),
            "total_size": total_size,
            "error": str(error),
        }

    return {
        "available": True,
        "items": items,
        "item_count": len(items),
        "total_size": total_size,
    }


def show_recycle_bin_snapshot(snapshot: dict, limit: int = 20) -> None:
    print("\n========== RECYCLE BIN ==========")

    if not snapshot["available"]:
        print(f"Khong doc duoc Recycle Bin: {snapshot.get('error')}")
        return

    if snapshot["item_count"] == 0:
        print("Recycle Bin dang rong.")
        return

    print(f"Tong item: {snapshot['item_count']}")
    print(f"Tong dung luong: {format_size(snapshot['total_size'])}")
    print("-" * 80)

    for index, item in enumerate(snapshot["items"][:limit], start=1):
        print(
            f"{index:>2}. {format_size(item['size']):>10} | "
            f"{item['original_path']}"
        )

    hidden_count = snapshot["item_count"] - limit
    if hidden_count > 0:
        print(f"... con {hidden_count} item khac trong report.")


def confirm_empty_recycle_bin(snapshot: dict) -> bool:
    print("\nCANH BAO: Empty Recycle Bin se xoa gan nhu vinh vien.")
    print("Tool khong the tao backup noi dung Recycle Bin truoc khi empty.")

    if not ask_yes_no("Ban da kiem tra Recycle Bin thu cong neu can?", default=False):
        return False

    message = (
        f"Xac nhan empty {snapshot['item_count']} item "
        f"({format_size(snapshot['total_size'])})?"
    )
    if not ask_yes_no(message, default=False):
        return False

    confirm_text = input("Nhap EMPTY de xac nhan lan cuoi: ").strip()
    return confirm_text == "EMPTY"


def clear_recycle_bin() -> None:
    if winshell is None:
        print("Thieu thu vien. Cai bang lenh: pip install winshell pywin32")
        log_action(
            "recycle_bin_cleaner",
            "clear_recycle_bin",
            "error",
            {"error": "winshell is not installed."},
        )
        return

    snapshot = scan_recycle_bin()
    show_recycle_bin_snapshot(snapshot)

    preview_report = create_report(
        tool_name="recycle_bin_cleaner_preview",
        status="preview",
        input_data={},
        results=snapshot,
        recommendations=[
            "Open Recycle Bin manually before emptying if you are unsure.",
            "Emptying Recycle Bin is not reversible through this tool.",
        ],
    )

    print(f"Preview report: {preview_report}")

    if not snapshot["available"]:
        log_action(
            "recycle_bin_cleaner",
            "clear_recycle_bin",
            "error",
            {"error": snapshot.get("error"), "preview_report": str(preview_report)},
        )
        return

    if snapshot["item_count"] == 0:
        log_action(
            "recycle_bin_cleaner",
            "clear_recycle_bin",
            "empty",
            {"preview_report": str(preview_report)},
        )
        return

    if not confirm_empty_recycle_bin(snapshot):
        print("Da huy.")
        log_action(
            "recycle_bin_cleaner",
            "clear_recycle_bin",
            "cancelled",
            {
                "item_count": snapshot["item_count"],
                "total_size": snapshot["total_size"],
                "preview_report": str(preview_report),
            },
        )
        return

    try:
        winshell.recycle_bin().empty(confirm=False, show_progress=True, sound=True)
        print("Da xoa xong Recycle Bin.")

        final_report = create_report(
            tool_name="recycle_bin_cleaner",
            status="success",
            input_data={
                "preview_report": str(preview_report),
            },
            results={
                "emptied_item_count": snapshot["item_count"],
                "emptied_total_size": snapshot["total_size"],
                "items": snapshot["items"],
            },
            recommendations=[
                "Review reports before running future permanent cleanup actions.",
            ],
        )

        log_action(
            "recycle_bin_cleaner",
            "clear_recycle_bin",
            "success",
            {
                "item_count": snapshot["item_count"],
                "total_size": snapshot["total_size"],
                "preview_report": str(preview_report),
                "final_report": str(final_report),
            },
        )

        print(f"Report: {final_report}")

    except Exception as e:
        print(f"Loi khi xoa Recycle Bin: {e}")
        create_report(
            tool_name="recycle_bin_cleaner",
            status="error",
            input_data={
                "preview_report": str(preview_report),
            },
            results={
                "error": str(e),
                "attempted_item_count": snapshot["item_count"],
                "attempted_total_size": snapshot["total_size"],
            },
            recommendations=[
                "Close apps that may be using Recycle Bin and try again.",
            ],
        )
        log_action(
            "recycle_bin_cleaner",
            "clear_recycle_bin",
            "error",
            {
                "error": str(e),
                "item_count": snapshot["item_count"],
                "total_size": snapshot["total_size"],
                "preview_report": str(preview_report),
            },
        )

if __name__ == "__main__":
    clear_recycle_bin()
