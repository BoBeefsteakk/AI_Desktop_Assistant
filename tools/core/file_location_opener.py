import os
import subprocess


def open_file_location(file_path):
    if not os.path.exists(file_path):
        print("File không tồn tại.")
        return False

    subprocess.run(["explorer", "/select,", os.path.normpath(file_path)])
    return True