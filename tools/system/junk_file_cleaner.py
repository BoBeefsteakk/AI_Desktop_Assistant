from __future__ import annotations

from pathlib import Path

from tools.core.safety_utils import format_size, ask_yes_no, save_report, is_system_path
from tools.core.report_manager import create_report
from tools.core.risk_classifier import classify_file_risk, SAFE_DELETE, PROTECTED
from tools.core.safe_executor import safe_delete
from config.settings import DEFAULT_SCAN_FOLDER


DEFAULT_JUNK_EXTENSIONS = (".tmp", ".log", ".bak", ".old", ".temp")

SKIP_FILES = {
    "dumpstack.log.tmp",
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
}


def scan_junk_files(
    folder: str,
    extensions: tuple[str, ...] = DEFAULT_JUNK_EXTENSIONS,
    recursive: bool = False,
    include_empty: bool = False,
) -> list[dict]:
    root = Path(folder)

    if not root.exists():
        print("Folder khong ton tai.")
        return []

    if is_system_path(root):
        print("Khong nen quet truc tiep folder he thong.")
        return []

    results = []
    iterator = root.rglob("*") if recursive else root.iterdir()

    for path in iterator:
        try:
            if not path.is_file():
                continue

            if path.name.lower() in SKIP_FILES:
                continue

            suffix_match = path.name.lower().endswith(extensions) if extensions else False
            empty_match = include_empty and path.stat().st_size == 0

            if suffix_match or empty_match:
                risk_data = classify_file_risk(path)

                if risk_data["risk"] == PROTECTED:
                    continue

                results.append({
                    "path": str(path),
                    "size": path.stat().st_size,
                    "reason": "empty" if empty_match and not suffix_match else "extension",
                    "risk": risk_data["risk"],
                    "risk_reason": risk_data["reason"],
                    "risk_category": risk_data.get("category"),
                    "risk_rule": risk_data.get("matched_rule"),
                })

        except (PermissionError, OSError):
            continue

    return results


def show_junk_files(files: list[dict]) -> None:
    print("\n========== FILE RAC TIM THAY ==========")

    if not files:
        print("Khong tim thay file rac phu hop.")
        return

    total = sum(item["size"] for item in files)

    for i, item in enumerate(files, start=1):
        risk_category = item.get("risk_category") or item["risk"]
        print(
            f"{i:>3}. {format_size(item['size']):>10} | "
            f"{item['risk']:<15} | {risk_category:<24} | {item['path']}"
        )

    print("-" * 80)
    print(f"Tong file: {len(files)}")
    print(f"Tong dung luong: {format_size(total)}")


def choose_files_to_delete(files: list[dict]) -> list[dict]:
    if not files:
        return []

    while True:
        print("\nChon file muon dua vao Recycle Bin:")
        print("- Nhap 0 de huy")
        print("- Nhap all de chon tat ca SAFE_DELETE")
        print("- Nhap so thu tu, cach nhau boi dau phay. VD: 1,3,5")

        choice = input("Lua chon: ").strip().lower()

        if choice == "0" or not choice:
            return []

        if choice == "all":
            risky_files = [
                file for file in files
                if file["risk"] != SAFE_DELETE
            ]

            if risky_files:
                print("Co file can review thu cong. Khong cho phep chon ALL.")
                print("Vui long chon tung file hoac nhap 0 de huy.")
                continue

            if not ask_yes_no("Ban chac chan muon chon tat ca file SAFE_DELETE?", default=False):
                continue

            return files

        selected = []

        for raw_index in choice.split(","):
            raw_index = raw_index.strip()

            if not raw_index.isdigit():
                continue

            index = int(raw_index) - 1

            if 0 <= index < len(files):
                selected.append(files[index])

        if selected:
            return selected

        print("Lua chon khong hop le. Vui long nhap lai.")


def delete_junk_files(files: list[dict]) -> None:
    if not files:
        print("Khong co file de xoa.")
        return

    selected_files = choose_files_to_delete(files)

    if not selected_files:
        print("Da huy xoa.")
        return

    report_path = save_report("junk_files_before_delete", selected_files)
    print(f"Da luu report backup: {report_path}")
    print("File se duoc dua vao Recycle Bin, khong xoa vinh vien.")

    if not ask_yes_no("Xac nhan dua cac file da chon vao Recycle Bin?", default=False):
        print("Da huy xoa.")
        return

    results = []

    for item in selected_files:
        result = safe_delete(item["path"])
        results.append(result)

    deleted = sum(1 for item in results if item["status"] == "deleted")
    blocked = sum(1 for item in results if item["status"] == "blocked")
    missing = sum(1 for item in results if item["status"] == "missing")
    errors = sum(1 for item in results if item["status"] == "error")
    total_size = sum(item["size"] for item in selected_files)

    print(f"Deleted: {deleted} | Blocked: {blocked} | Missing: {missing} | Errors: {errors}")

    report = create_report(
        tool_name="junk_file_cleaner",
        status="success",
        input_data={
            "selected_count": len(selected_files),
        },
        results={
            "deleted_count": deleted,
            "blocked_count": blocked,
            "missing_count": missing,
            "error_count": errors,
            "total_size": total_size,
            "files": selected_files,
            "execution_results": results,
        },
        recommendations=[
            "Files were moved to Recycle Bin, not permanently deleted.",
            "Review Recycle Bin before emptying it.",
        ],
    )

    print(f"Report: {report}")


def run_junk_cleaner() -> None:
    folder = input("Nhap folder can quet: ").strip().strip('"') or DEFAULT_SCAN_FOLDER
    recursive = ask_yes_no("Quet ca folder con?", default=False)
    include_empty = ask_yes_no("Bao gom file rong 0KB?", default=False)

    files = scan_junk_files(
        folder,
        recursive=recursive,
        include_empty=include_empty
    )

    show_junk_files(files)
    delete_junk_files(files)


if __name__ == "__main__":
    run_junk_cleaner()
