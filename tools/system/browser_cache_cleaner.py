from __future__ import annotations

import os
import shutil
from pathlib import Path

from tools.core.safety_utils import format_size, ask_yes_no, save_report

def get_browser_cache_paths() -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming = Path(os.environ.get("APPDATA", ""))

    paths = [
        local / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
        local / "Google" / "Chrome" / "User Data" / "Default" / "Code Cache",
        local / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
        local / "Microsoft" / "Edge" / "User Data" / "Default" / "Code Cache",
        local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Cache",
        local / "CocCoc" / "Browser" / "User Data" / "Default" / "Cache",
    ]

    firefox_profiles = roaming / "Mozilla" / "Firefox" / "Profiles"
    if firefox_profiles.exists():
        for profile in firefox_profiles.iterdir():
            paths.append(profile / "cache2")

    return [p for p in paths if p.exists()]

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
        results.append({
            "path": str(path),
            "size": size
        })
    return results

def show_browser_cache(results: list[dict]) -> None:
    print("\n========== BROWSER CACHE ==========")
    total = sum(x["size"] for x in results)

    if not results:
        print("Khong tim thay cache browser.")
        return

    for i, item in enumerate(results, start=1):
        print(f"{i:>2}. {format_size(item['size']):>10} | {item['path']}")

    print("-" * 80)
    print(f"Tong cache: {format_size(total)}")

def clean_browser_cache() -> None:
    results = scan_browser_cache()
    show_browser_cache(results)

    if not results:
        return

    report = save_report("browser_cache_before_clean", results)
    print(f"Da luu report: {report}")
    print("Nen dong Chrome/Edge/Firefox truoc khi don cache.")

    if not ask_yes_no("Ban muon xoa cac thu muc cache nay?", default=False):
        print("Da huy.")
        return

    cleaned = 0
    for item in results:
        path = Path(item["path"])
        try:
            shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
            cleaned += 1
            print(f"Da don: {path}")
        except Exception as e:
            print(f"Loi: {path} | {e}")

    print(f"Da don {cleaned}/{len(results)} cache folders.")

def run_browser_cache_cleaner() -> None:
    clean_browser_cache()

if __name__ == "__main__":
    run_browser_cache_cleaner()
