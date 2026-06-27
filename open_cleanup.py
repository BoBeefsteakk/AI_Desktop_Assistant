"""Launcher cho protocol toast click (8.3).

Windows không chấp nhận file .bat làm handler cho URL protocol, nên protocol
`AI-Desktop-Assistant:` (đăng ký qua winotify) trỏ tới `pythonw <file này>`.
Script đặt cwd + sys.path về thư mục dự án rồi mở Bot Panel ở chế độ --cleanup
(nhảy thẳng banner Dọn 1 chạm).

Tham số cuối (vd "AI-Desktop-Assistant:cleanup") do Windows truyền vào, bỏ qua được.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ép cờ --cleanup để bot_panel focus banner Dọn sau khi auto-scan.
sys.argv = [sys.argv[0], "--cleanup"]

from tools.ui.bot_panel import run_bot_panel  # noqa: E402

if __name__ == "__main__":
    run_bot_panel()
