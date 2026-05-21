from __future__ import annotations

import psutil
from .safety_utils import format_size

def check_disk() -> None:
    print("\n========== THONG TIN O CUNG ==========\n")

    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        except OSError:
            continue

        print(f"O: {partition.device}")
        print(f"Mountpoint       : {partition.mountpoint}")
        print(f"File system      : {partition.fstype}")
        print(f"Tong dung luong  : {format_size(usage.total)}")
        print(f"Da su dung       : {format_size(usage.used)}")
        print(f"Con trong        : {format_size(usage.free)}")
        print(f"Phan tram dung   : {usage.percent}%")

        if usage.percent >= 90:
            print("Canh bao: O nay gan day, nen don bot file.")
        elif usage.percent >= 80:
            print("Luu y: O nay dang dung tren 80%.")

        print("-" * 50)

if __name__ == "__main__":
    check_disk()
