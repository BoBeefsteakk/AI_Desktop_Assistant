from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .safety_utils import ask_yes_no

APP_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = APP_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "startup_profiles.json"

DEFAULT_CONFIG = {
    "study": [
        {"name": "VS Code", "path": "code", "args": []},
        {"name": "Chrome", "path": "chrome", "args": ["https://chat.openai.com"]}
    ],
    "game": [],
    "work": []
}

def ensure_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)

def load_profiles() -> dict:
    ensure_config()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_profiles(profiles: dict) -> None:
    ensure_config()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def launch_profile(profile_name: str) -> None:
    profiles = load_profiles()

    if profile_name not in profiles:
        print("Khong tim thay profile.")
        return

    apps = profiles[profile_name]
    if not apps:
        print("Profile nay chua co app nao.")
        return

    print(f"Dang mo profile: {profile_name}")

    for app in apps:
        try:
            path = app["path"]
            args = app.get("args", [])
            subprocess.Popen([path, *args], shell=False)
            print(f"Da mo: {app.get('name', path)}")
        except Exception as e:
            print(f"Loi khi mo {app.get('name', app.get('path'))}: {e}")

def add_app_to_profile(profile_name: str, app_name: str, app_path: str, args: list[str] | None = None) -> None:
    profiles = load_profiles()

    if profile_name not in profiles:
        profiles[profile_name] = []

    profiles[profile_name].append({
        "name": app_name,
        "path": app_path,
        "args": args or []
    })

    save_profiles(profiles)
    print("Da them app vao profile.")

def show_profiles() -> None:
    profiles = load_profiles()

    print("\n========== STARTUP PROFILES ==========")
    for name, apps in profiles.items():
        print(f"\n[{name}]")
        if not apps:
            print("  Chua co app.")
        for app in apps:
            print(f"  - {app.get('name')} | {app.get('path')} | args={app.get('args', [])}")

def run_startup_launcher() -> None:
    while True:
        print("""
========== STARTUP LAUNCHER ==========
1. Xem profiles
2. Mo profile
3. Them app vao profile
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            show_profiles()

        elif choice == "2":
            profile = input("Nhap ten profile: ").strip()
            launch_profile(profile)

        elif choice == "3":
            profile = input("Nhap ten profile, VD study/game/work: ").strip()
            name = input("Ten app: ").strip()
            path = input("Duong dan app.exe hoac command, VD code/chrome: ").strip().strip('"')
            raw_args = input("Args neu co, cach nhau bang dau |, bo trong neu khong co: ").strip()
            args = [x.strip() for x in raw_args.split("|") if x.strip()]
            add_app_to_profile(profile, name, path, args)

        elif choice == "0":
            break
        else:
            print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_startup_launcher()
