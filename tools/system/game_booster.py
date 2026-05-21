from __future__ import annotations

import os
import subprocess
import time

import psutil

from tools.core.safety_utils import ask_yes_no

BACKGROUND_APPS = {
    "OneDrive.exe",
    "Teams.exe",
    "ms-teams.exe",
    "Discord.exe",
    "Spotify.exe",
    "chrome.exe",
    "msedge.exe"
}

def set_high_priority(process_name: str) -> None:
    target = process_name.lower()
    found = False

    for p in psutil.process_iter(["pid", "name"]):
        try:
            name = (p.info["name"] or "").lower()
            if name == target:
                psutil.Process(p.info["pid"]).nice(psutil.HIGH_PRIORITY_CLASS)
                print(f"Da set High Priority: {p.info['name']} | PID {p.info['pid']}")
                found = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not found:
        print("Khong tim thay process game.")

def show_system_status() -> None:
    print("\n========== SYSTEM STATUS ==========")
    print(f"CPU: {psutil.cpu_percent(interval=0.5)}%")
    mem = psutil.virtual_memory()
    print(f"RAM: {mem.percent}% | Free: {mem.available / (1024**3):.2f} GB")

def kill_background_apps() -> None:
    print("\nDanh sach app nen co the tat:")
    for app in sorted(BACKGROUND_APPS):
        print("-", app)

    if not ask_yes_no("Ban muon tat cac app nen trong danh sach?", default=False):
        print("Da huy.")
        return

    killed = 0
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if p.info["name"] in BACKGROUND_APPS:
                psutil.Process(p.info["pid"]).terminate()
                print(f"Da tat: {p.info['name']}")
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    print(f"Da tat {killed} process.")

def enable_ultimate_performance() -> None:
    print("Dang bat Ultimate Performance...")
    commands = [
        ["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
        ["powercfg", "-setactive", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
    ]

    for cmd in commands:
        try:
            subprocess.run(cmd, check=False, capture_output=True, text=True)
        except Exception as e:
            print(f"Loi powercfg: {e}")

    print("Da gui lenh bat Ultimate Performance.")

def restore_balanced_power() -> None:
    print("Dang khoi phuc Balanced...")
    try:
        subprocess.run(
            ["powercfg", "-setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"],
            check=False,
            capture_output=True,
            text=True
        )
        print("Da khoi phuc Balanced.")
    except Exception as e:
        print(f"Loi: {e}")

def run_game_booster() -> None:
    while True:
        print("""
========== GAME BOOSTER SAFE ==========
1. Xem CPU/RAM hien tai
2. Set High Priority cho game dang chay
3. Tat app nen trong danh sach
4. Bat Ultimate Performance
5. Restore Balanced Power Plan
0. Thoat
""")
        choice = input("Chon: ").strip()

        if choice == "1":
            show_system_status()

        elif choice == "2":
            name = input("Nhap ten game .exe, VD: game.exe: ").strip()
            set_high_priority(name)

        elif choice == "3":
            kill_background_apps()

        elif choice == "4":
            enable_ultimate_performance()

        elif choice == "5":
            restore_balanced_power()

        elif choice == "0":
            break
        else:
            print("Lua chon khong hop le.")

if __name__ == "__main__":
    run_game_booster()
