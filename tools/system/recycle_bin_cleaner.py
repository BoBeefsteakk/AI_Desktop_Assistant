from __future__ import annotations

try:
    import winshell
except ImportError:
    winshell = None

from tools.core.safety_utils import ask_yes_no

def clear_recycle_bin() -> None:
    if winshell is None:
        print("Thieu thu vien. Cai bang lenh: pip install winshell pywin32")
        return

    print("\nCANH BAO: Xoa Recycle Bin thi gan nhu khong co nut backup/undo trong tool.")
    print("Neu con file quan trong trong Recycle Bin, hay kiem tra thu cong truoc.")

    if not ask_yes_no("Ban chac chan muon xoa Recycle Bin?", default=False):
        print("Da huy.")
        return

    try:
        winshell.recycle_bin().empty(confirm=False, show_progress=True, sound=True)
        print("Da xoa xong Recycle Bin.")
    except Exception as e:
        print(f"Loi khi xoa Recycle Bin: {e}")

if __name__ == "__main__":
    clear_recycle_bin()
