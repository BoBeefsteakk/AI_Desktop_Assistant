from __future__ import annotations

import os
import shutil
import subprocess
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, TOP, X, Y, filedialog, messagebox
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import DANGER, PRIMARY, SUCCESS

# ttkbootstrap exposes the themed label frame as `Labelframe`; `LabelFrame` falls back
# to the unthemed tk widget that rejects `padding`/`bootstyle`. Alias so existing
# `ttk.LabelFrame(...)` calls use the themed widget.
ttk.LabelFrame = ttk.Labelframe
from typing import Any, Callable

from config.settings import (
    DEFAULT_LARGE_FILE_MB,
    DEFAULT_RESULT_LIMIT,
    DEFAULT_SCAN_FOLDER,
    REPORTS_DIR,
)
from tools.core.auto_scan_session import export_auto_scan_session_report
from tools.core.bot_controller import (
    build_bot_controller_result,
    build_selection_session,
    export_backup_selection_flow_report,
    export_move_later_selection_flow_report,
    export_safe_delete_selection_flow_report,
    export_selection_decision_report,
)
from tools.core.backup_adapter import FINAL_BACKUP_TOKEN
from tools.core.file_operation_adapter import FINAL_MOVE_TOKEN
from tools.core.safe_delete_adapter import FINAL_DELETE_TOKEN
from tools.core.issue_classifier import export_issue_classifier_report
from tools.core.report_manager import read_recent_report_index
from tools.core.safety_utils import format_size
from tools.core.undo_manager import restore_manifest
from tools.storage.wiztree_adapter import is_wiztree_available


BOT_PANEL_SCHEMA = "bot_panel_ui_v2"
BOT_PANEL_TITLE = "AI Desktop Assistant"
DEMO_SANDBOX_ROOT = Path(r"D:\_ai_desktop_assistant_ui_demo")
ASSISTANT_RESULT_PANEL_MIN_HEIGHT_PX = 520
ASSISTANT_HISTORY_PANEL_ROWS = 10
ASSISTANT_HISTORY_PANEL_SCOPE = "bottom_full_height"
SELECTION_DECISIONS = [
    "keep",
    "manual_review",
    "needs_backup",
    "move_later",
    "delete_candidate",
    "skip",
]


def build_bot_panel_snapshot() -> dict[str, Any]:
    return {
        "schema": BOT_PANEL_SCHEMA,
        "title": BOT_PANEL_TITLE,
        "entrypoint": "python -m tools.ui.bot_panel",
        "executes_file_operations_directly": False,
        "can_call_backup_adapter": True,
        "can_call_file_operation_adapter": True,
        "can_call_safe_delete_adapter": True,
        "backup_apply_requires_token": FINAL_BACKUP_TOKEN,
        "move_apply_requires_token": FINAL_MOVE_TOKEN,
        "safe_delete_apply_requires_token": FINAL_DELETE_TOKEN,
        "supports_demo_sandbox": True,
        "supports_assistant_dashboard": True,
        "supports_issue_cards": True,
        "supports_full_demo_flow": True,
        "supports_one_click_ai_plan": True,
        "supports_assistant_activity_log": True,
        "supports_run_history_panel": True,
        "assistant_result_panel_scope": "full_width",
        "assistant_result_panel_min_height_px": ASSISTANT_RESULT_PANEL_MIN_HEIGHT_PX,
        "assistant_history_panel_rows": ASSISTANT_HISTORY_PANEL_ROWS,
        "assistant_history_panel_scope": ASSISTANT_HISTORY_PANEL_SCOPE,
        "assistant_history_panel_min_height_px": ASSISTANT_RESULT_PANEL_MIN_HEIGHT_PX,
        "assistant_bottom_panel_anchor": "bottom_visible",
        "supports_backup_flow": True,
        "supports_move_later_flow": True,
        "supports_move_undo": True,
        "supports_safe_delete_flow": True,
        "demo_sandbox_root": str(DEMO_SANDBOX_ROOT),
    }


def create_demo_sandbox() -> Path:
    root = DEMO_SANDBOX_ROOT / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    files = {
        root / "cache" / "old_cache.tmp": 1024 * 1024,
        root / "logs" / "review_me.log": 1024 * 1024,
        root / "media" / "selected_video.mp4": 2 * 1024 * 1024,
        root / "work" / "edit_project.prproj": 1024 * 1024,
    }
    for path, size in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as file:
            file.write(b"0" * size)
    (root / "_move_destination").mkdir(parents=True, exist_ok=True)
    return root


def cleanup_demo_sandbox(sandbox: str | Path) -> None:
    root = DEMO_SANDBOX_ROOT.resolve()
    target = Path(sandbox).resolve()

    if target == root or root not in target.parents or not target.name.startswith("run_"):
        raise RuntimeError(f"Refuse to cleanup unsafe UI demo sandbox path: {target}")

    if target.exists():
        shutil.rmtree(target)


def default_storage_mode() -> str:
    """Pick a storage-aware default so the assistant surfaces heavy/junk files on open."""
    try:
        if is_wiztree_available():
            return "wiztree"
    except Exception:
        pass
    return "python"


def run_bot_panel() -> None:
    root = ttk.Window(themename="cosmo")
    BotPanel(root)
    root.mainloop()


class BotPanel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(BOT_PANEL_TITLE)
        self.root.geometry("1680x1040")
        self.root.minsize(1360, 920)

        self.busy = False
        self.bot_result: dict[str, Any] | None = None
        self.selection_session: dict[str, Any] | None = None
        self.item_by_id: dict[str, dict[str, Any]] = {}
        self.decisions: dict[str, str] = {}
        self.last_scan_report: str | None = None
        self.last_classifier_report: str | None = None
        self.last_decision_report: str | None = None
        self.last_flow_report: str | None = None
        self.last_backup_manifest: str | None = None
        self.last_backup_dir: str | None = None
        self.pending_backup_run_dir: str | None = None
        self.last_move_manifest: str | None = None
        self.latest_report_path: str | None = None
        self.last_scan_data: dict[str, Any] | None = None
        self.quick_item_by_id: dict[str, dict[str, Any]] = {}
        self.quick_kept_ids: set[str] = set()
        self.last_backup_dry_run_signature: tuple[tuple[str, str], ...] | None = None
        self.last_dry_run_signature: tuple[tuple[str, str], ...] | None = None
        self.last_move_dry_run_signature: tuple[tuple[str, str], ...] | None = None
        self.last_plan_preview_signature: tuple[tuple[str, str], ...] | None = None

        self.scan_path_var = tk.StringVar(value=DEFAULT_SCAN_FOLDER)
        self.move_destination_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value=default_storage_mode())
        self.large_file_mb_var = tk.StringVar(value=str(DEFAULT_LARGE_FILE_MB))
        self.limit_var = tk.StringVar(value=str(DEFAULT_RESULT_LIMIT))
        self.group_filter_var = tk.StringVar(value="all")
        self.decision_filter_var = tk.StringVar(value="all")
        self.status_var = tk.StringVar(value="Ready.")
        self.summary_var = tk.StringVar(value="No scan loaded yet.")
        self.guide_var = tk.StringVar(value=self.default_guide_text())
        self.assistant_status_var = tk.StringVar(value="No scan loaded yet.")
        self.assistant_next_step_var = tk.StringVar(value="Choose a folder or try the demo sandbox, then run scan.")
        self.assistant_counts_var = tk.StringVar(value="Backup 0 | Move 0 | Safe cleanup 0 | Review 0 | Protected 0")
        self.view_mode_var = tk.StringVar(value="Đang xem: chưa quét")
        self.confirm_backup_var = tk.BooleanVar(value=False)
        self.confirm_move_var = tk.BooleanVar(value=False)
        self.confirm_delete_var = tk.BooleanVar(value=False)
        self.confirm_plan_var = tk.BooleanVar(value=False)
        self.note_var = tk.StringVar(value="Bot Panel UI decision")

        self._build_layout()
        self.refresh_from_latest()
        self.root.after(600, self.auto_start_scan)

    def _build_layout(self) -> None:
        self._configure_style()

        header = ttk.Frame(self.root, padding=(16, 12), bootstyle=PRIMARY)
        header.pack(side=TOP, fill=X)

        ttk.Label(
            header,
            text=BOT_PANEL_TITLE,
            font=("Segoe UI", 16, "bold"),
            bootstyle="inverse-primary",
        ).pack(side=LEFT)
        ttk.Label(
            header,
            textvariable=self.status_var,
            bootstyle="inverse-primary",
        ).pack(side=RIGHT)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=12, pady=(0, 12))

        self.assistant_tab = ttk.Frame(self.notebook, padding=10)
        self.advanced_tab = ttk.Frame(self.notebook, padding=(0, 8, 0, 0))
        self.notebook.add(self.assistant_tab, text="Trợ lý")
        self.notebook.add(self.advanced_tab, text="Chi tiết")

        self._build_assistant_panel(self.assistant_tab)

        self._build_advanced_scan_controls(self.advanced_tab)

        summary = ttk.Label(self.advanced_tab, textvariable=self.summary_var, style="Summary.TLabel", padding=(0, 0, 0, 6))
        summary.pack(side=TOP, fill=X)
        guide = ttk.Label(self.advanced_tab, textvariable=self.guide_var, style="Guide.TLabel", padding=(0, 0, 0, 8))
        guide.pack(side=TOP, fill=X)

        body = ttk.Panedwindow(self.advanced_tab, orient=tk.HORIZONTAL)
        body.pack(fill=BOTH, expand=True)

        left = ttk.Frame(body)
        right = ttk.Frame(body, width=360)
        body.add(left, weight=4)
        body.add(right, weight=1)

        self._build_table_panel(left)
        self._build_detail_panel(right)

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 9))
        style.configure("Summary.TLabel", font=("Segoe UI", 10))
        style.configure("Guide.TLabel", font=("Segoe UI", 9))
        style.configure("AssistantTitle.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("AssistantStatus.TLabel", font=("Segoe UI", 11))
        style.configure("AssistantCount.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("ViewMode.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        # Larger, more readable text for monospace report/health panels.
        self.mono_font = ("Consolas", 10)

    def _build_advanced_scan_controls(self, parent: ttk.Frame) -> None:
        controls = ttk.LabelFrame(parent, text="Advanced scan controls", padding=8)
        controls.pack(side=TOP, fill=X, pady=(0, 8))

        ttk.Label(controls, text="Scan folder").grid(row=0, column=0, sticky="w")
        path_entry = ttk.Entry(controls, textvariable=self.scan_path_var)
        path_entry.grid(row=0, column=1, columnspan=5, sticky="ew", padx=(8, 8))
        ttk.Button(controls, text="Browse", command=self.browse_scan_folder).grid(row=0, column=6, padx=(0, 8))
        ttk.Button(controls, text="Demo sandbox", command=self.create_demo).grid(row=0, column=7, padx=(0, 8))
        ttk.Button(controls, text="Open reports", command=lambda: self.open_path(REPORTS_DIR)).grid(row=0, column=8)

        ttk.Label(controls, text="Mode").grid(row=1, column=0, sticky="w", pady=(8, 0))
        mode = ttk.Combobox(
            controls,
            textvariable=self.mode_var,
            values=["light", "python", "wiztree"],
            state="readonly",
            width=12,
        )
        mode.grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(8, 0))

        ttk.Label(controls, text="Large MB").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.large_file_mb_var, width=8).grid(row=1, column=3, sticky="w", padx=(8, 18), pady=(8, 0))

        ttk.Label(controls, text="Limit").grid(row=1, column=4, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.limit_var, width=8).grid(row=1, column=5, sticky="w", padx=(8, 18), pady=(8, 0))

        ttk.Button(controls, text="Auto scan + classify", command=self.run_scan_and_classify).grid(row=1, column=6, sticky="ew", padx=(0, 8), pady=(8, 0))
        ttk.Button(controls, text="Refresh latest", command=self.refresh_from_latest).grid(row=1, column=7, sticky="ew", padx=(0, 8), pady=(8, 0))
        ttk.Button(controls, text="Clear choices", command=self.clear_all_decisions).grid(row=1, column=8, sticky="ew", pady=(8, 0))

        controls.columnconfigure(1, weight=1)

    def _build_assistant_panel(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(side=TOP, fill=X)

        headline = ttk.Frame(top)
        headline.pack(side=LEFT, fill=X, expand=True)
        ttk.Label(headline, text="Trợ lý AI kiểm tra máy", style="AssistantTitle.TLabel").pack(anchor="w")
        ttk.Label(
            headline,
            textvariable=self.assistant_status_var,
            style="AssistantStatus.TLabel",
            wraplength=860,
        ).pack(anchor="w", pady=(6, 0))
        ttk.Label(
            headline,
            textvariable=self.assistant_next_step_var,
            style="Guide.TLabel",
            wraplength=860,
        ).pack(anchor="w", pady=(4, 0))

        quick = ttk.Frame(top)
        quick.pack(side=RIGHT, anchor="ne")
        ttk.Button(quick, text="Kiểm tra máy thật", command=self.run_scan_and_classify, bootstyle=PRIMARY, width=22).pack(fill=X, pady=(0, 6))
        ttk.Button(quick, text="Xem thử (file giả)", command=self.create_demo_and_scan, bootstyle="success-outline").pack(fill=X, pady=(0, 6))
        ttk.Button(quick, text="Chạy demo toàn bộ", command=self.run_full_demo_flow, bootstyle="info-outline").pack(fill=X, pady=(0, 6))
        ttk.Button(quick, text="Xem chi tiết kỹ thuật", command=self.open_advanced_tab, bootstyle="secondary-outline").pack(fill=X)

        steps = ttk.LabelFrame(parent, text="Luồng sử dụng", padding=8)
        steps.pack(side=TOP, fill=X, pady=(14, 10))
        ttk.Label(
            steps,
            text="1. Quét thư mục  ->  2. AI lập đề xuất  ->  3. Bạn xem preview rồi xác nhận",
            style="AssistantCount.TLabel",
        ).pack(anchor="w")

        path_panel = ttk.LabelFrame(parent, text="Thư mục cần kiểm tra", padding=8)
        path_panel.pack(side=TOP, fill=X, pady=(14, 10))
        ttk.Entry(path_panel, textvariable=self.scan_path_var).pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        ttk.Button(path_panel, text="Chọn thư mục", command=self.browse_scan_folder).pack(side=LEFT, padx=(0, 8))
        ttk.Button(path_panel, text="Mở báo cáo", command=lambda: self.open_path(REPORTS_DIR)).pack(side=LEFT)

        counts = ttk.LabelFrame(parent, text="Tóm tắt AI tìm thấy", padding=8)
        counts.pack(side=TOP, fill=X, pady=(0, 10))
        ttk.Label(counts, textvariable=self.assistant_counts_var, style="AssistantCount.TLabel").pack(anchor="w")

        health = ttk.LabelFrame(parent, text="Sức khỏe ổ cứng & tư vấn của AI", padding=8)
        health.pack(side=TOP, fill=X, pady=(0, 10))
        self.view_mode_label = ttk.Label(
            health,
            textvariable=self.view_mode_var,
            style="ViewMode.TLabel",
            bootstyle="secondary",
        )
        self.view_mode_label.pack(side=TOP, anchor="w", pady=(0, 6))
        health_body = ttk.Frame(health)
        health_body.pack(side=TOP, fill=BOTH, expand=True)
        health_scroll = ttk.Scrollbar(health_body, orient=tk.VERTICAL)
        health_scroll.pack(side=RIGHT, fill=Y)
        self.health_text = tk.Text(
            health_body,
            height=14,
            wrap="word",
            font=self.mono_font,
            relief="flat",
            background="#f7f9fc",
            yscrollcommand=health_scroll.set,
        )
        self.health_text.pack(side=LEFT, fill=BOTH, expand=True)
        health_scroll.configure(command=self.health_text.yview)
        self.health_text.configure(state="disabled")
        self.write_text(self.health_text, "Đang chờ lần quét đầu tiên... AI sẽ tự kiểm tra ổ cứng khi mở app.")

        quick = ttk.LabelFrame(parent, text="Dọn nhanh — chọn mục rồi bấm Xóa hoặc Giữ", padding=8)
        quick.pack(side=TOP, fill=X, pady=(0, 10))
        ttk.Label(
            quick,
            text="Đây là các file rác AI thấy an toàn để dọn. Chọn 1 hoặc nhiều dòng, rồi bấm Xóa (đưa vào Recycle Bin) hoặc Giữ.",
            style="Guide.TLabel",
            wraplength=900,
        ).pack(anchor="w", pady=(0, 6))

        quick_body = ttk.Frame(quick)
        quick_body.pack(side=TOP, fill=X)
        quick_scroll = ttk.Scrollbar(quick_body, orient=tk.VERTICAL)
        quick_scroll.pack(side=RIGHT, fill=Y)
        quick_columns = ("size", "name", "path")
        self.quick_tree = ttk.Treeview(
            quick_body,
            columns=quick_columns,
            show="headings",
            selectmode="extended",
            height=7,
            yscrollcommand=quick_scroll.set,
        )
        for col, head, width, stretch in (
            ("size", "Dung lượng", 100, False),
            ("name", "Tên file", 220, False),
            ("path", "Đường dẫn", 640, True),
        ):
            self.quick_tree.heading(col, text=head)
            self.quick_tree.column(col, width=width, stretch=stretch)
        self.quick_tree.pack(side=LEFT, fill=X, expand=True)
        quick_scroll.configure(command=self.quick_tree.yview)

        quick_buttons = ttk.Frame(quick)
        quick_buttons.pack(side=TOP, fill=X, pady=(8, 0))
        ttk.Button(quick_buttons, text="Chọn tất cả", command=self.quick_select_all, bootstyle="secondary-outline").pack(side=LEFT, padx=(0, 6))
        ttk.Button(quick_buttons, text="Mở thư mục", command=self.quick_open_selected, bootstyle="secondary-outline").pack(side=LEFT, padx=(0, 6))
        ttk.Button(quick_buttons, text="Giữ mục đã chọn", command=self.quick_keep_selected, bootstyle=SUCCESS).pack(side=RIGHT)
        ttk.Button(quick_buttons, text="Xóa mục đã chọn", command=self.quick_delete_selected, bootstyle=DANGER).pack(side=RIGHT, padx=(0, 6))
        self.write_quick_placeholder()

        bottom_frame = ttk.Frame(parent)
        bottom_frame.configure(height=ASSISTANT_RESULT_PANEL_MIN_HEIGHT_PX)
        bottom_frame.pack(side=tk.BOTTOM, fill=X, pady=(10, 0))
        bottom_frame.grid_columnconfigure(0, weight=3, minsize=900)
        bottom_frame.grid_columnconfigure(1, weight=1, minsize=420)
        bottom_frame.grid_rowconfigure(0, weight=1)
        bottom_frame.grid_propagate(False)

        log_frame = ttk.LabelFrame(bottom_frame, text="Kết quả gần nhất", padding=8)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL)
        log_scroll.pack(side=RIGHT, fill=Y)
        self.assistant_log_text = tk.Text(log_frame, height=32, width=110, wrap="word", yscrollcommand=log_scroll.set)
        self.assistant_log_text.pack(side=LEFT, fill=BOTH, expand=True)
        log_scroll.configure(command=self.assistant_log_text.yview)
        self.assistant_log_text.configure(state="disabled")
        self.write_text(
            self.assistant_log_text,
            "Chưa có kế hoạch.\n\n"
            "Bấm Chạy full demo để xem mẫu, hoặc quét folder rồi bấm Xem kế hoạch AI.",
        )

        history_frame = ttk.LabelFrame(bottom_frame, text="Lịch sử gần đây", padding=6)
        history_frame.grid(row=0, column=1, sticky="nsew")
        history_text_frame = ttk.Frame(history_frame)
        history_text_frame.pack(fill=BOTH, expand=True)
        history_scroll = ttk.Scrollbar(history_text_frame, orient=tk.VERTICAL)
        history_scroll.pack(side=RIGHT, fill=Y)
        self.history_text = tk.Text(
            history_text_frame,
            height=ASSISTANT_HISTORY_PANEL_ROWS,
            width=58,
            wrap="word",
            yscrollcommand=history_scroll.set,
        )
        self.history_text.pack(side=LEFT, fill=BOTH, expand=True)
        history_scroll.configure(command=self.history_text.yview)
        self.history_text.configure(state="disabled")

        history_buttons = ttk.Frame(history_frame)
        history_buttons.pack(fill=X, pady=(6, 0))
        ttk.Button(history_buttons, text="Làm mới", command=self.refresh_report_history).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        ttk.Button(history_buttons, text="Mở report mới", command=self.open_latest_report).pack(side=LEFT, fill=X, expand=True)
        self.refresh_report_history()

        issue_frame = ttk.Frame(parent)
        issue_frame.pack(side=TOP, fill=BOTH, expand=True)
        issue_frame.columnconfigure(0, weight=3, minsize=680)
        issue_frame.columnconfigure(1, weight=2, minsize=440)
        issue_frame.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(issue_frame, text="Đề xuất của AI", padding=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.assistant_cards_frame = ttk.Frame(left)
        self.assistant_cards_frame.pack(fill=BOTH, expand=True)

        right = ttk.LabelFrame(issue_frame, text="Bước tiếp theo", padding=8)
        right.grid(row=0, column=1, sticky="nsew")

        ttk.Button(
            right,
            text="1. Dùng đề xuất AI",
            command=self.use_recommended_for_all,
            bootstyle=SUCCESS,
        ).pack(fill=X, pady=(0, 8))
        ttk.Button(
            right,
            text="2. Xem kế hoạch AI",
            command=self.preview_ai_plan,
            bootstyle=PRIMARY,
        ).pack(fill=X, pady=(0, 6))
        ttk.Checkbutton(
            right,
            text="Tôi đã xem kế hoạch",
            variable=self.confirm_plan_var,
            bootstyle="round-toggle",
        ).pack(anchor="w", pady=(0, 6))
        ttk.Button(
            right,
            text="3. Áp dụng kế hoạch",
            command=self.apply_ai_plan,
            bootstyle=DANGER,
        ).pack(fill=X, pady=(0, 12))
        ttk.Button(right, text="Chạy demo toàn bộ", command=self.run_full_demo_flow, bootstyle="info-outline").pack(fill=X, pady=(0, 8))
        ttk.Button(right, text="Hủy lựa chọn", command=self.clear_all_decisions, bootstyle="secondary-outline").pack(fill=X, pady=(0, 8))
        ttk.Button(right, text="Chi tiết kỹ thuật", command=self.open_advanced_tab, bootstyle="secondary-outline").pack(fill=X)

    def _build_table_panel(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent)
        toolbar.pack(side=TOP, fill=X, pady=(0, 8))

        ttk.Label(toolbar, text="Group").pack(side=LEFT)
        group_filter = ttk.Combobox(
            toolbar,
            textvariable=self.group_filter_var,
            values=["all", "safe_to_execute", "needs_selection", "do_not_touch", "review_only"],
            state="readonly",
            width=18,
        )
        group_filter.pack(side=LEFT, padx=(6, 14))
        group_filter.bind("<<ComboboxSelected>>", lambda _event: self.populate_table())

        ttk.Label(toolbar, text="Decision/Recommend").pack(side=LEFT)
        decision_filter = ttk.Combobox(
            toolbar,
            textvariable=self.decision_filter_var,
            values=["all", "empty", *SELECTION_DECISIONS],
            state="readonly",
            width=18,
        )
        decision_filter.pack(side=LEFT, padx=(6, 14))
        decision_filter.bind("<<ComboboxSelected>>", lambda _event: self.populate_table())

        ttk.Button(toolbar, text="Use recommended", command=self.use_recommended_for_selected).pack(side=LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="Use visible recommended", command=self.use_recommended_for_visible).pack(side=LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="Show needs_backup", command=self.show_needs_backup).pack(side=LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="Show move_later", command=self.show_move_later).pack(side=LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="Show delete candidates", command=self.show_delete_candidates).pack(side=LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="Show all", command=self.show_all_items).pack(side=LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="Open location", command=self.open_selected_location).pack(side=LEFT)

        columns = ("id", "decision", "recommended", "group", "action", "risk", "size", "name", "path")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="extended")
        headings = {
            "id": "ID",
            "decision": "Decision",
            "recommended": "Recommend",
            "group": "Group",
            "action": "Action",
            "risk": "Risk",
            "size": "Size",
            "name": "Name",
            "path": "Path",
        }
        widths = {
            "id": 58,
            "decision": 116,
            "recommended": 116,
            "group": 118,
            "action": 120,
            "risk": 110,
            "size": 86,
            "name": 190,
            "path": 520,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], stretch=column in {"name", "path"})

        self.tree.tag_configure("do_not_touch", background="#f9e1e1")
        self.tree.tag_configure("needs_selection", background="#fff4d6")
        self.tree.tag_configure("safe_to_execute", background="#e0f2e9")
        self.tree.tag_configure("review_only", background="#e8edf7")
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self.show_selected_detail())

        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=RIGHT, fill=Y)
        self.tree.configure(yscrollcommand=scroll.set)

        actions = ttk.LabelFrame(parent, text="Apply decision to selected rows", padding=8)
        actions.pack(side=TOP, fill=X, pady=(8, 0))
        for decision in SELECTION_DECISIONS:
            ttk.Button(
                actions,
                text=decision,
                command=lambda value=decision: self.apply_decision_to_selected(value),
            ).pack(side=LEFT, padx=(0, 6))
        ttk.Button(actions, text="clear", command=self.clear_selected_decisions).pack(side=LEFT, padx=(10, 0))

    def _build_detail_panel(self, parent: ttk.Frame) -> None:
        detail_frame = ttk.LabelFrame(parent, text="Selected item", padding=8)
        detail_frame.pack(side=TOP, fill=BOTH, expand=True)
        self.detail_text = tk.Text(detail_frame, height=18, wrap="word")
        self.detail_text.pack(fill=BOTH, expand=True)
        self.detail_text.configure(state="disabled")

        note_frame = ttk.LabelFrame(parent, text="Decision note", padding=8)
        note_frame.pack(side=TOP, fill=X, pady=(8, 0))
        ttk.Entry(note_frame, textvariable=self.note_var).pack(fill=X)

        backup_frame = ttk.LabelFrame(parent, text="Backup first", padding=8)
        backup_frame.pack(side=TOP, fill=X, pady=(8, 0))
        ttk.Button(backup_frame, text="Backup dry-run", command=self.backup_dry_run).pack(fill=X, pady=(0, 6))
        ttk.Checkbutton(
            backup_frame,
            text="I reviewed backup dry-run; copy eligible files",
            variable=self.confirm_backup_var,
        ).pack(anchor="w", pady=(0, 6))
        ttk.Button(backup_frame, text="Apply backup", command=self.backup_apply).pack(fill=X)
        ttk.Button(backup_frame, text="Open backup", command=self.open_last_backup).pack(fill=X, pady=(6, 0))

        move_frame = ttk.LabelFrame(parent, text="Move later", padding=8)
        move_frame.pack(side=TOP, fill=X, pady=(8, 0))
        ttk.Label(move_frame, text="Destination folder").pack(anchor="w")
        move_path = ttk.Entry(move_frame, textvariable=self.move_destination_var)
        move_path.pack(fill=X, pady=(2, 6))
        move_buttons = ttk.Frame(move_frame)
        move_buttons.pack(fill=X)
        ttk.Button(move_buttons, text="Browse", command=self.browse_move_destination).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        ttk.Button(move_buttons, text="Open dest", command=self.open_move_destination).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        ttk.Button(move_buttons, text="Move dry-run", command=self.move_later_dry_run).pack(side=LEFT, fill=X, expand=True)
        ttk.Checkbutton(
            move_frame,
            text="I reviewed move dry-run; move eligible files",
            variable=self.confirm_move_var,
        ).pack(anchor="w", pady=(6, 6))
        ttk.Button(move_frame, text="Apply move", command=self.move_later_apply).pack(fill=X)
        ttk.Button(move_frame, text="Undo last move", command=self.undo_last_move).pack(fill=X, pady=(6, 0))

        flow_frame = ttk.LabelFrame(parent, text="Safe delete", padding=8)
        flow_frame.pack(side=TOP, fill=X, pady=(8, 0))
        ttk.Button(flow_frame, text="Save decision report", command=self.save_decision_report).pack(fill=X, pady=(0, 6))
        ttk.Button(flow_frame, text="Safe delete dry-run", command=self.safe_delete_dry_run).pack(fill=X, pady=(0, 6))
        ttk.Checkbutton(
            flow_frame,
            text="I reviewed dry-run; send eligible files to Recycle Bin",
            variable=self.confirm_delete_var,
        ).pack(anchor="w", pady=(0, 6))
        ttk.Button(flow_frame, text="Apply safe delete", style="Danger.TButton", command=self.safe_delete_apply).pack(fill=X)

        reports_frame = ttk.LabelFrame(parent, text="Latest reports", padding=8)
        reports_frame.pack(side=TOP, fill=X, pady=(8, 0))
        self.reports_text = tk.Text(reports_frame, height=9, wrap="word")
        self.reports_text.pack(fill=X)
        self.reports_text.configure(state="disabled")
        self.write_detail(self.default_guide_text(long=True))

    def default_guide_text(self, *, long: bool = False) -> str:
        short = (
            "Flow: 1) Demo/Browse -> 2) Scan + classify -> 3) Use visible recommended "
            "-> 4) Backup/Move/Delete dry-run -> 5) Tick confirm + Apply."
        )
        if not long:
            return short
        return (
            f"{short}\n\n"
            "Safety notes:\n"
            "- Dry-run never deletes files.\n"
            "- Backup copies eligible needs_backup files and preserves the source.\n"
            "- Move uses File Operation Adapter and writes a restore manifest after apply.\n"
            "- Apply sends eligible safe_delete files to Recycle Bin only.\n"
            "- review_required/protected items stay blocked even if selected.\n"
            "- If choices change after dry-run, run dry-run again before apply."
        )

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def set_busy(self, busy: bool, text: str | None = None) -> None:
        self.busy = busy
        if text:
            self.set_status(text)

    def run_background(
        self,
        label: str,
        worker: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
    ) -> None:
        if self.busy:
            messagebox.showinfo("Busy", "A task is already running.")
            return

        self.set_busy(True, f"{label}...")

        def task() -> None:
            try:
                result = worker()
            except Exception as error:  # pragma: no cover - UI error path
                trace = traceback.format_exc()
                self.root.after(0, lambda: self.show_error(label, error, trace))
                return
            self.root.after(0, lambda: self.finish_task(label, result, on_success))

        threading.Thread(target=task, daemon=True).start()

    def finish_task(
        self,
        label: str,
        result: Any,
        on_success: Callable[[Any], None] | None,
    ) -> None:
        self.set_busy(False, f"{label} done.")
        if on_success:
            on_success(result)

    def show_error(self, label: str, error: Exception, trace: str) -> None:
        self.set_busy(False, f"{label} failed.")
        self.write_detail(f"{label} failed:\n{error}\n\n{trace}")
        messagebox.showerror(label, str(error))

    def browse_scan_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.scan_path_var.get() or DEFAULT_SCAN_FOLDER)
        if folder:
            self.scan_path_var.set(folder)
            self.show_all_items()
            self.reset_apply_guard()

    def browse_move_destination(self) -> None:
        initial = self.move_destination_var.get().strip() or self.scan_path_var.get() or DEFAULT_SCAN_FOLDER
        folder = filedialog.askdirectory(initialdir=initial)
        if folder:
            self.move_destination_var.set(folder)
            self.reset_apply_guard()

    def create_demo(self) -> None:
        root = create_demo_sandbox()
        self.scan_path_var.set(str(root))
        self.mode_var.set("python")
        self.large_file_mb_var.set("1")
        self.limit_var.set("50")
        self.group_filter_var.set("all")
        self.decision_filter_var.set("all")
        self.move_destination_var.set(str(root / "_move_destination"))
        self.reset_apply_guard()
        self.set_status(f"Demo sandbox created: {root}")
        messagebox.showinfo("Demo sandbox", f"Created fake test files:\n{root}")

    def create_demo_and_scan(self) -> None:
        root = create_demo_sandbox()
        self.scan_path_var.set(str(root))
        self.mode_var.set("python")
        self.large_file_mb_var.set("1")
        self.limit_var.set("50")
        self.group_filter_var.set("all")
        self.decision_filter_var.set("all")
        self.move_destination_var.set(str(root / "_move_destination"))
        self.reset_apply_guard()
        self.run_scan_and_classify()

    def run_full_demo_flow(self) -> None:
        root = create_demo_sandbox()
        destination = root / "_move_destination"
        self.scan_path_var.set(str(root))
        self.mode_var.set("python")
        self.large_file_mb_var.set("1")
        self.limit_var.set("50")
        self.group_filter_var.set("all")
        self.decision_filter_var.set("all")
        self.move_destination_var.set(str(destination))
        self.reset_apply_guard()

        def worker() -> dict[str, Any]:
            events = [
                "Click 1: Chay thu an toan - tao sandbox file gia.",
                "Click 2: Quet thu muc - auto scan + classify.",
            ]
            scan_export = export_auto_scan_session_report(
                root_drive=str(root),
                storage_mode="python",
                large_file_mb=1,
                result_limit=50,
                extra_tags=["bot_panel_ui", "full_demo"],
            )
            classifier_export = export_issue_classifier_report(
                source_report_path=scan_export["report"],
                include_items=True,
                extra_tags=["bot_panel_ui", "full_demo"],
            )
            bot = build_bot_controller_result(include_items=True)
            session = build_selection_session(bot_result=bot, include_items=True)

            decisions: dict[str, str] = {}
            for group_items in session.get("groups", {}).values():
                for item in group_items:
                    if item.get("locked"):
                        continue
                    selection_id = item.get("selection_id")
                    recommended = item.get("recommended_decision")
                    if selection_id and recommended in item.get("allowed_decisions", []):
                        decisions[str(selection_id)] = str(recommended)

            events.append(f"Click 3: Dung de xuat AI - chon {len(decisions)} item.")

            backup_dry = export_backup_selection_flow_report(
                decisions,
                mode="dry_run",
                final_token=None,
                session=session,
                note="Bot Panel full demo backup dry-run",
                extra_tags=["bot_panel_ui", "full_demo"],
            )
            backup_run_dir = backup_dry.get("flow", {}).get("summary", {}).get("backup_run_dir")
            events.append("Click 4: Xem truoc backup - dry-run, chua copy.")
            backup_apply = export_backup_selection_flow_report(
                decisions,
                mode="apply",
                final_token=FINAL_BACKUP_TOKEN,
                backup_run_dir=backup_run_dir,
                session=session,
                note="Bot Panel full demo backup apply",
                extra_tags=["bot_panel_ui", "full_demo"],
            )
            events.append("Click 5: Copy backup - copy file can backup, giu nguyen source.")

            move_dry = export_move_later_selection_flow_report(
                decisions,
                destination_root=str(destination),
                mode="dry_run",
                final_token=None,
                session=session,
                note="Bot Panel full demo move dry-run",
                extra_tags=["bot_panel_ui", "full_demo"],
            )
            events.append("Click 6: Xem truoc move - dry-run, chua move.")
            move_apply = export_move_later_selection_flow_report(
                decisions,
                destination_root=str(destination),
                mode="apply",
                final_token=FINAL_MOVE_TOKEN,
                session=session,
                note="Bot Panel full demo move apply",
                extra_tags=["bot_panel_ui", "full_demo"],
            )
            events.append("Click 7: Move file - move file vao _move_destination va tao manifest.")

            delete_dry = export_safe_delete_selection_flow_report(
                decisions,
                mode="dry_run",
                final_token=None,
                session=session,
                note="Bot Panel full demo safe-delete dry-run",
                extra_tags=["bot_panel_ui", "full_demo"],
            )
            events.append("Click 8: Xem truoc don an toan - dry-run, chua xoa.")
            delete_apply = export_safe_delete_selection_flow_report(
                decisions,
                mode="apply",
                final_token=FINAL_DELETE_TOKEN,
                session=session,
                note="Bot Panel full demo safe-delete apply",
                extra_tags=["bot_panel_ui", "full_demo"],
            )
            events.append("Click 9: Dua vao Recycle Bin - chi file fake risk=safe_delete.")

            return {
                "sandbox": str(root),
                "destination": str(destination),
                "events": events,
                "scan": scan_export,
                "classifier": classifier_export,
                "bot": bot,
                "session": session,
                "decisions": decisions,
                "backup_dry": backup_dry,
                "backup_apply": backup_apply,
                "move_dry": move_dry,
                "move_apply": move_apply,
                "delete_dry": delete_dry,
                "delete_apply": delete_apply,
            }

        self.run_background("Full demo flow", worker, self.load_full_demo_flow)

    def load_full_demo_flow(self, result: dict[str, Any]) -> None:
        self.last_scan_report = result.get("scan", {}).get("report")
        self.last_scan_data = result.get("scan", {}).get("scan")
        self.last_classifier_report = result.get("classifier", {}).get("report")
        self.bot_result = result.get("bot")
        self.selection_session = result.get("session")
        self.decisions = dict(result.get("decisions", {}))

        backup_summary = result.get("backup_apply", {}).get("flow", {}).get("summary", {})
        move_summary = result.get("move_apply", {}).get("flow", {}).get("summary", {})
        delete_summary = result.get("delete_apply", {}).get("flow", {}).get("summary", {})

        if backup_summary.get("manifest"):
            self.last_backup_manifest = str(backup_summary["manifest"])
        if backup_summary.get("backup_run_dir"):
            self.last_backup_dir = str(backup_summary["backup_run_dir"])
        if move_summary.get("manifest"):
            self.last_move_manifest = str(move_summary["manifest"])

        self.last_flow_report = result.get("delete_apply", {}).get("report")
        self.last_decision_report = (
            result.get("delete_apply", {})
            .get("flow", {})
            .get("decision_report", {})
            .get("report")
            or self.last_decision_report
        )
        self.reset_apply_guard()
        self.populate_table()
        self.update_summary()
        self.update_reports_text()
        self.update_health_panel()
        self.populate_quick_actions()
        self.write_assistant_log(
            "Đã quét xong.\n\n"
            f"Scan report:\n{self.last_scan_report or '-'}\n\n"
            f"Classifier report:\n{self.last_classifier_report or '-'}\n\n"
            "Bước tiếp theo: bấm Dùng đề xuất AI, rồi Xem kế hoạch AI."
        )

        lines = [
            "Full demo flow finished.",
            "",
            f"Sandbox: {result.get('sandbox')}",
            f"Move destination: {result.get('destination')}",
            "",
            "Visible click sequence:",
            *[f"- {event}" for event in result.get("events", [])],
            "",
            "Results:",
            self.format_demo_summary("Backup dry-run", result.get("backup_dry")),
            self.format_demo_summary("Backup apply", result.get("backup_apply")),
            self.format_demo_summary("Move dry-run", result.get("move_dry")),
            self.format_demo_summary("Move apply", result.get("move_apply")),
            self.format_demo_summary("Safe cleanup dry-run", result.get("delete_dry")),
            self.format_demo_summary("Safe cleanup apply", result.get("delete_apply")),
            "",
            "Reports:",
            f"- Scan: {self.last_scan_report}",
            f"- Classifier: {self.last_classifier_report}",
            f"- Final flow: {self.last_flow_report}",
            f"- Backup dir: {self.last_backup_dir or '-'}",
            f"- Move manifest: {self.last_move_manifest or '-'}",
            "",
            "Demo only touched generated fake files under the sandbox path above.",
        ]
        self.write_detail("\n".join(lines))
        self.write_assistant_log("\n".join(lines))
        self.set_status("Full demo done. Review the step log in Assistant.")

    def format_demo_summary(self, title: str, result: dict[str, Any] | None) -> str:
        flow = (result or {}).get("flow", {})
        summary = flow.get("summary", {}) if isinstance(flow, dict) else {}
        keys = [
            "backup_requested_count",
            "backupable_count",
            "backed_up_count",
            "move_requested_count",
            "movable_count",
            "moved_count",
            "delete_requested_count",
            "deletable_count",
            "deleted_count",
            "backup_blocked_count",
            "operation_blocked_count",
            "delete_blocked_count",
            "backup_error_count",
            "operation_error_count",
            "delete_error_count",
        ]
        parts = [f"status={flow.get('status')}", f"mode={flow.get('mode')}"]
        for key in keys:
            if key in summary:
                parts.append(f"{key}={summary.get(key)}")
        return f"- {title}: " + ", ".join(parts)

    def parse_positive_int(self, value: str, fallback: int) -> int:
        try:
            number = int(str(value).strip())
            return number if number > 0 else fallback
        except ValueError:
            return fallback

    def run_scan_and_classify(self) -> None:
        root_path = self.scan_path_var.get().strip() or DEFAULT_SCAN_FOLDER
        mode = self.mode_var.get()
        large_mb = self.parse_positive_int(self.large_file_mb_var.get(), DEFAULT_LARGE_FILE_MB)
        limit = self.parse_positive_int(self.limit_var.get(), DEFAULT_RESULT_LIMIT)

        def worker() -> dict[str, Any]:
            scan_export = export_auto_scan_session_report(
                root_drive=root_path,
                storage_mode=mode,
                large_file_mb=large_mb,
                result_limit=limit,
                extra_tags=["bot_panel_ui"],
            )
            classifier_export = export_issue_classifier_report(
                source_report_path=scan_export["report"],
                include_items=True,
                extra_tags=["bot_panel_ui"],
            )
            bot = build_bot_controller_result(include_items=True)
            session = build_selection_session(bot_result=bot, include_items=True)
            return {
                "scan": scan_export,
                "classifier": classifier_export,
                "bot": bot,
                "session": session,
            }

        self.run_background("Auto scan + classify", worker, self.load_scan_result)

    def auto_start_scan(self) -> None:
        """Run a full read-only scan automatically when the app opens."""
        if self.busy:
            self.root.after(700, self.auto_start_scan)
            return
        scan_path = Path(self.scan_path_var.get().strip() or DEFAULT_SCAN_FOLDER)
        if scan_path.exists():
            self.set_status("AI đang tự động kiểm tra máy...")
            self.run_scan_and_classify()

    def update_health_panel(self) -> None:
        if not hasattr(self, "health_text"):
            return
        data = self.last_scan_data
        if not data:
            return
        if self.is_demo_scan_path():
            self.view_mode_var.set("Đang xem: DỮ LIỆU THỬ (file giả, không phải máy thật)")
            self.view_mode_label.configure(bootstyle="warning")
        else:
            self.view_mode_var.set("Đang xem: MÁY THẬT")
            self.view_mode_label.configure(bootstyle="success")
        snapshot = data.get("snapshot", {})
        advisor = data.get("advisor", {})
        disk = snapshot.get("disk", {})
        storage = snapshot.get("storage", {})

        lines: list[str] = ["== Ổ ĐĨA =="]
        status_label = {"ok": "Tốt", "warning": "Cần theo dõi", "critical": "Sắp đầy"}
        for item in disk.get("disks", []):
            status_text = status_label.get(item.get("status"), str(item.get("status")))
            lines.append(
                f"{item.get('mountpoint')}  {item.get('percent')}% đã dùng  | "
                f"còn trống {format_size(item.get('free', 0))} / {format_size(item.get('total', 0))}  -> {status_text}"
            )

        smart = disk.get("smart_health", {})
        devices = smart.get("devices", [])
        if devices:
            lines.append("")
            lines.append("== SMART (sức khỏe phần cứng) ==")
            for dev in devices:
                passed = dev.get("smart_passed")
                health_text = "PASS" if passed is True else "CẢNH BÁO" if passed is False else "Không rõ"
                temp = dev.get("temperature")
                temp_text = f" | {temp}°C" if temp is not None else ""
                lines.append(
                    f"[{health_text}] {dev.get('device')} "
                    f"{dev.get('model') or dev.get('comment') or ''}{temp_text}"
                )

        large_files = storage.get("large_files", [])
        if large_files:
            total = sum(item.get("size", 0) for item in large_files)
            lines.append("")
            lines.append(f"== FILE NẶNG ({len(large_files)} file, ~{format_size(total)}) ==")
            for item in large_files[:8]:
                lines.append(f"{format_size(item.get('size', 0)):>10}  {item.get('path')}")

        top_folders = storage.get("top_folders", [])
        if top_folders:
            lines.append("")
            lines.append("== THƯ MỤC LỚN NHẤT ==")
            for item in top_folders[:6]:
                lines.append(f"{format_size(item.get('size', 0)):>10}  {item.get('path')}")

        recommendations = advisor.get("recommendations", [])
        if recommendations:
            lines.append("")
            lines.append("== AI TƯ VẤN ==")
            sev_label = {"critical": "NGHIÊM TRỌNG", "warning": "CẢNH BÁO", "info": "Thông tin"}
            for rec in recommendations:
                sev = sev_label.get(rec.get("severity"), str(rec.get("severity")))
                lines.append(f"[{sev}] {rec.get('title')}: {rec.get('detail')}")

        if storage.get("provider") in {"skipped", None} and not large_files and not top_folders:
            lines.append("")
            lines.append("(Chế độ quét nhanh không đọc chi tiết file. Chọn mode python/wiztree ở tab Chi tiết để xem file nặng.)")

        self.write_text(self.health_text, "\n".join(lines))

    # ----- Dọn nhanh: chọn Xóa hoặc Giữ cho từng file rác -----

    def write_quick_placeholder(self, message: str | None = None) -> None:
        if not hasattr(self, "quick_tree"):
            return
        self.quick_tree.delete(*self.quick_tree.get_children())
        self.quick_item_by_id = {}
        text = message or "Chưa có dữ liệu. Bấm 'Kiểm tra máy thật' để AI tìm file rác."
        self.quick_tree.insert("", END, iid="__placeholder__", values=("", "", text))

    def populate_quick_actions(self) -> None:
        if not hasattr(self, "quick_tree"):
            return
        self.quick_tree.delete(*self.quick_tree.get_children())
        self.quick_item_by_id = {}
        if not self.selection_session:
            self.write_quick_placeholder()
            return

        rows = 0
        for item in self.iter_selection_items():
            if item.get("locked"):
                continue
            selection_id = item.get("selection_id")
            if not selection_id or selection_id in self.quick_kept_ids:
                continue
            # Chỉ liệt kê file AI THỰC SỰ khuyến nghị xóa (file rác, risk safe_delete),
            # không phải mọi item tình cờ cho phép xóa như một lựa chọn.
            if item.get("recommended_decision") != "delete_candidate":
                continue
            if "delete_candidate" not in item.get("allowed_decisions", []):
                continue
            if not item.get("path"):
                continue
            self.quick_item_by_id[selection_id] = item
            self.quick_tree.insert(
                "",
                END,
                iid=selection_id,
                values=(
                    item.get("size_text") or "-",
                    item.get("name") or "-",
                    item.get("path") or "-",
                ),
            )
            rows += 1

        if rows == 0:
            self.write_quick_placeholder("Không tìm thấy file rác nào đủ an toàn để dọn tự động. Mọi thứ ổn!")

    def quick_selected_ids(self) -> list[str]:
        return [
            iid for iid in self.quick_tree.selection()
            if iid in self.quick_item_by_id
        ]

    def quick_select_all(self) -> None:
        ids = list(self.quick_item_by_id.keys())
        if ids:
            self.quick_tree.selection_set(ids)

    def quick_open_selected(self) -> None:
        ids = self.quick_selected_ids()
        if not ids:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một dòng trước.")
            return
        item = self.quick_item_by_id.get(ids[0])
        path = item.get("path") if item else None
        if not path:
            return
        target = Path(path)
        if target.exists() and target.is_file():
            subprocess.Popen(["explorer", "/select,", str(target)])
        elif target.parent.exists():
            self.open_path(target.parent)
        else:
            messagebox.showwarning("Không tìm thấy", f"Đường dẫn không còn tồn tại:\n{target}")

    def quick_keep_selected(self) -> None:
        ids = self.quick_selected_ids()
        if not ids:
            messagebox.showinfo("Chưa chọn", "Hãy chọn mục muốn giữ.")
            return
        for selection_id in ids:
            self.quick_kept_ids.add(selection_id)
            self.decisions[selection_id] = "keep"
        self.populate_quick_actions()
        self.update_summary()
        self.set_status(f"Đã giữ {len(ids)} mục; AI sẽ không đụng tới.")

    def quick_delete_selected(self) -> None:
        if not self.selection_session:
            messagebox.showinfo("Chưa quét", "Hãy bấm 'Kiểm tra máy thật' trước.")
            return
        ids = self.quick_selected_ids()
        if not ids:
            messagebox.showinfo("Chưa chọn", "Hãy chọn ít nhất một file để xóa.")
            return

        total_size = sum(int(self.quick_item_by_id[i].get("size") or 0) for i in ids)
        confirmed = messagebox.askyesno(
            "Xác nhận xóa",
            f"Đưa {len(ids)} file vào Recycle Bin (có thể khôi phục), tổng ~{format_size(total_size)}.\n\n"
            "AI chỉ xóa file đủ an toàn; file cần xem tay sẽ bị bỏ qua.\nTiếp tục?",
        )
        if not confirmed:
            return

        decisions = {selection_id: "delete_candidate" for selection_id in ids}
        session = self.selection_session

        def worker() -> dict[str, Any]:
            dry = export_safe_delete_selection_flow_report(
                decisions,
                mode="dry_run",
                final_token=None,
                session=session,
                note="Bot Panel quick-delete dry-run",
                extra_tags=["bot_panel_ui", "quick_delete"],
            )
            deletable = dry["flow"]["summary"].get("deletable_count", 0)
            errors = dry["flow"]["summary"].get("delete_error_count", 0)
            applied = None
            if deletable > 0 and errors == 0:
                applied = export_safe_delete_selection_flow_report(
                    decisions,
                    mode="apply",
                    final_token=FINAL_DELETE_TOKEN,
                    session=session,
                    note="Bot Panel quick-delete apply",
                    extra_tags=["bot_panel_ui", "quick_delete"],
                )
            return {"requested": len(ids), "dry": dry, "applied": applied}

        self.run_background("Dọn nhanh", worker, self.load_quick_delete_result)

    def load_quick_delete_result(self, result: dict[str, Any]) -> None:
        applied = result.get("applied")
        dry = result.get("dry", {})
        requested = result.get("requested", 0)
        if applied is None:
            blocked = dry.get("flow", {}).get("summary", {}).get("delete_blocked_count", 0)
            self.set_status("Dọn nhanh: không có file đủ điều kiện xóa.")
            messagebox.showinfo(
                "Không xóa được",
                f"Trong {requested} mục, không có mục nào đủ an toàn để xóa "
                f"(bị chặn: {blocked}). AI giữ nguyên tất cả.",
            )
            return
        summary = applied.get("flow", {}).get("summary", {})
        deleted = summary.get("deleted_count", 0)
        blocked = summary.get("delete_blocked_count", 0)
        self.last_flow_report = applied.get("report") or self.last_flow_report
        self.update_reports_text()
        self.set_status(f"Đã xóa {deleted} file vào Recycle Bin.")
        messagebox.showinfo(
            "Đã dọn xong",
            f"Đã đưa {deleted} file vào Recycle Bin (có thể khôi phục).\n"
            f"Bị chặn an toàn: {blocked}.\n\nĐang quét lại để cập nhật danh sách...",
        )
        self.root.after(300, self.run_scan_and_classify)

    def refresh_from_latest(self) -> None:
        def worker() -> dict[str, Any]:
            bot = build_bot_controller_result(include_items=True)
            session = build_selection_session(bot_result=bot, include_items=True)
            return {"bot": bot, "session": session}

        self.run_background("Refresh latest reports", worker, self.load_scan_result)

    def load_scan_result(self, result: dict[str, Any]) -> None:
        self.bot_result = result.get("bot")
        self.selection_session = result.get("session")
        if result.get("scan"):
            self.last_scan_report = result["scan"].get("report")
            self.last_scan_data = result["scan"].get("scan")
        if result.get("classifier"):
            self.last_classifier_report = result["classifier"].get("report")
        self.decisions = {}
        self.reset_apply_guard()
        if self.is_demo_scan_path():
            self.group_filter_var.set("all")
            self.decision_filter_var.set("all")
        self.quick_kept_ids = set()
        self.populate_table()
        self.update_summary()
        self.update_reports_text()
        self.update_health_panel()
        self.populate_quick_actions()

    def populate_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.item_by_id = {}
        if not self.selection_session:
            return

        group_filter = self.group_filter_var.get()
        decision_filter = self.decision_filter_var.get()
        inserted_count = 0
        for group_name, items in self.selection_session.get("groups", {}).items():
            if group_filter != "all" and group_name != group_filter:
                continue
            for item in items:
                selection_id = item["selection_id"]
                decision = self.decisions.get(selection_id, "")
                recommended = str(item.get("recommended_decision") or "")
                if decision_filter == "empty" and decision:
                    continue
                if (
                    decision_filter not in {"all", "empty"}
                    and decision != decision_filter
                    and recommended != decision_filter
                ):
                    continue
                self.item_by_id[selection_id] = item
                self.tree.insert(
                    "",
                    END,
                    iid=selection_id,
                    values=(
                        selection_id,
                        decision or "-",
                        item.get("recommended_decision") or "-",
                        item.get("selection_group") or group_name,
                        item.get("plan_action") or "-",
                        item.get("risk") or item.get("policy_decision") or "-",
                        item.get("size_text") or "-",
                        item.get("name") or "-",
                        item.get("path") or "-",
                    ),
                    tags=(group_name,),
                )
                inserted_count += 1
        if inserted_count == 0:
            self.write_detail(
                "No visible rows for the current filter.\n\n"
                "Try Decision/Recommend = all, or click Show all.\n"
                "If this is demo mode, click Demo sandbox again, then Auto scan + classify."
            )

    def update_summary(self) -> None:
        summary = self.bot_result.get("summary", {}) if self.bot_result else {}
        session_summary = self.selection_session.get("summary", {}) if self.selection_session else {}
        delete_selected = sum(1 for decision in self.decisions.values() if decision == "delete_candidate")
        move_selected = sum(1 for decision in self.decisions.values() if decision == "move_later")
        backup_selected = sum(1 for decision in self.decisions.values() if decision == "needs_backup")
        text = (
            f"Readiness: {summary.get('readiness_status', '-')} | "
            f"Issues: {summary.get('classified_issue_count', 0)} | "
            f"Need selection: {summary.get('needs_selection_count', 0)} | "
            f"Do not touch: {summary.get('do_not_touch_count', 0)} | "
            f"Selectable: {session_summary.get('selectable_count', 0)} | "
            f"Choices: {len(self.decisions)} | Backup: {backup_selected} | Move: {move_selected} | Delete: {delete_selected}"
        )
        self.summary_var.set(text)
        self.update_assistant_dashboard()

    def iter_selection_items(self) -> list[dict[str, Any]]:
        if not self.selection_session:
            return []
        items: list[dict[str, Any]] = []
        for group_items in self.selection_session.get("groups", {}).values():
            items.extend(group_items)
        return items

    def count_recommended(self) -> dict[str, int]:
        counts = {
            "needs_backup": 0,
            "move_later": 0,
            "delete_candidate": 0,
            "manual_review": 0,
            "keep": 0,
            "skip": 0,
            "do_not_touch": 0,
        }
        for item in self.iter_selection_items():
            decision = str(item.get("recommended_decision") or "")
            if decision in counts:
                counts[decision] += 1
            if item.get("locked") or item.get("selection_group") == "do_not_touch":
                counts["do_not_touch"] += 1
        return counts

    def update_assistant_dashboard(self) -> None:
        if not hasattr(self, "assistant_cards_frame"):
            return
        summary = self.bot_result.get("summary", {}) if self.bot_result else {}
        counts = self.count_recommended()
        choices = {
            "needs_backup": sum(1 for decision in self.decisions.values() if decision == "needs_backup"),
            "move_later": sum(1 for decision in self.decisions.values() if decision == "move_later"),
            "delete_candidate": sum(1 for decision in self.decisions.values() if decision == "delete_candidate"),
        }

        issue_count = int(summary.get("classified_issue_count", 0) or 0)
        selectable = int((self.selection_session or {}).get("summary", {}).get("selectable_count", 0) or 0)
        if not self.selection_session:
            self.assistant_status_var.set("Chưa có kết quả quét. AI đang chờ bạn chọn thư mục.")
            self.assistant_next_step_var.set("Bấm Chạy thử an toàn để test bằng file giả, hoặc chọn thư mục thật rồi quét.")
        else:
            self.assistant_status_var.set(
                f"AI phát hiện {issue_count} vấn đề. {selectable} item có thể xem xét an toàn; "
                f"{counts['do_not_touch']} item được khóa và sẽ không bị đụng tới."
            )
            if counts["delete_candidate"] or counts["needs_backup"] or counts["move_later"]:
                self.assistant_next_step_var.set(
                    "Thứ tự nên làm: backup trước, xem move nếu cần, sau đó mới xem dọn an toàn."
                )
            elif counts["manual_review"]:
                self.assistant_next_step_var.set("Chưa nên tự xử lý gì; các item này cần bạn xem thủ công.")
            else:
                self.assistant_next_step_var.set("Không có hành động rủi ro trong lần quét mới nhất.")

        self.assistant_counts_var.set(
            f"Cần backup {counts['needs_backup']} | Cần move {counts['move_later']} | "
            f"Dọn an toàn {counts['delete_candidate']} | Cần xem {counts['manual_review']} | "
            f"Được bảo vệ {counts['do_not_touch']} | Đã chọn {len(self.decisions)}"
        )

        rows = [
            ("needs_backup", "Backup trước", counts["needs_backup"], choices["needs_backup"], "Copy trước khi làm gì khác; file gốc giữ nguyên.", "Xem backup"),
            ("move_later", "Move sau", counts["move_later"], choices["move_later"], "Chuyển sang thư mục bạn chọn; có manifest để restore.", "Xem move"),
            ("delete_candidate", "Dọn an toàn", counts["delete_candidate"], choices["delete_candidate"], "Chỉ file đủ an toàn mới được đưa vào Recycle Bin.", "Xem dọn"),
            ("manual_review", "Cần xem tay", counts["manual_review"], 0, "Không tự động xử lý; cần bạn quyết định.", "Xem review"),
            ("do_not_touch", "Không đụng tới", counts["do_not_touch"], 0, "File/folder được khóa; AI không thay đổi.", "Xem khóa"),
        ]
        for child in self.assistant_cards_frame.winfo_children():
            child.destroy()
        for decision, area, count, selected_count, meaning, button_text in rows:
            self.create_assistant_card(
                parent=self.assistant_cards_frame,
                decision=decision,
                title=area,
                count=count,
                selected_count=selected_count,
                meaning=meaning,
                button_text=button_text,
            )

    def create_assistant_card(
        self,
        *,
        parent: ttk.Frame,
        decision: str,
        title: str,
        count: int,
        selected_count: int,
        meaning: str,
        button_text: str,
    ) -> None:
        card_style = {
            "needs_backup": "warning",
            "move_later": "info",
            "delete_candidate": "danger",
            "manual_review": "secondary",
            "do_not_touch": "secondary",
        }.get(decision, "secondary")

        card = ttk.LabelFrame(parent, text=title, padding=8, bootstyle=card_style)
        card.pack(side=TOP, fill=X, pady=(0, 8))

        top = ttk.Frame(card)
        top.pack(fill=X)
        ttk.Label(
            top,
            text=f"{count} item | {selected_count} đã chọn",
            style="AssistantCount.TLabel",
            bootstyle=card_style,
        ).pack(side=LEFT)
        ttk.Button(
            top,
            text=button_text,
            command=lambda value=decision: self.show_assistant_group(value),
            bootstyle=f"{card_style}-outline",
        ).pack(side=RIGHT)

        ttk.Label(
            card,
            text=meaning,
            style="Guide.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(6, 0))

        if decision in {"needs_backup", "move_later", "delete_candidate"}:
            ttk.Button(
                card,
                text="Chọn theo đề xuất này",
                command=lambda value=decision: self.prepare_and_focus_recommended(value),
                bootstyle=card_style,
            ).pack(anchor="e", pady=(6, 0))

    def update_reports_text(self) -> None:
        lines = [
            f"Scan: {self.last_scan_report or '-'}",
            f"Classifier: {self.last_classifier_report or '-'}",
            f"Decision: {self.last_decision_report or '-'}",
            f"Flow: {self.last_flow_report or '-'}",
            f"Backup manifest: {self.last_backup_manifest or '-'}",
            f"Backup dir: {self.last_backup_dir or '-'}",
            f"Move manifest: {self.last_move_manifest or '-'}",
        ]
        self.write_text(self.reports_text, "\n".join(lines))
        self.refresh_report_history()

    def refresh_report_history(self) -> None:
        if not hasattr(self, "history_text"):
            return
        records = read_recent_report_index(limit=8)
        if not records:
            self.latest_report_path = None
            self.write_text(self.history_text, "Chưa có report nào.")
            return

        latest = records[-1]
        self.latest_report_path = latest.get("report_path")
        lines = []
        for index, record in enumerate(reversed(records), start=1):
            created = str(record.get("created_at") or "-").replace("T", " ")
            tool = record.get("tool") or "-"
            action = record.get("action") or "-"
            status = record.get("status") or "-"
            risk = record.get("risk_level") or "-"
            report_path = Path(str(record.get("report_path") or ""))
            label = report_path.name if str(report_path) else "-"
            lines.append(f"{index}. {created}")
            lines.append(f"   {tool} | {action} | {status} | {risk}")
            lines.append(f"   {label}")
        self.write_text(self.history_text, "\n".join(lines))

    def open_latest_report(self) -> None:
        self.refresh_report_history()
        if not self.latest_report_path:
            messagebox.showinfo("No report", "Chưa có report mới để mở.")
            return
        target = Path(self.latest_report_path)
        if target.exists() and target.is_file():
            subprocess.Popen(["explorer", "/select,", str(target)])
        elif target.parent.exists():
            self.open_path(target.parent)
        else:
            messagebox.showwarning("Missing report", f"Report không còn tồn tại:\n{target}")

    def show_selected_detail(self) -> None:
        selected = self.tree.selection()
        if not selected:
            self.write_detail("No item selected.")
            return
        item = self.item_by_id.get(selected[0])
        if not item:
            self.write_detail("Selected item is not available.")
            return
        lines = [
            f"ID: {item.get('selection_id')}",
            f"Decision: {self.decisions.get(item.get('selection_id'), '-')}",
            f"Recommended: {item.get('recommended_decision')}",
            f"Allowed: {', '.join(item.get('allowed_decisions', []))}",
            f"Locked: {item.get('locked')}",
            f"Group: {item.get('selection_group')}",
            f"Action: {item.get('plan_action')}",
            f"Risk: {item.get('risk') or item.get('policy_decision')}",
            f"Size: {item.get('size_text')}",
            f"Name: {item.get('name')}",
            f"Path: {item.get('path')}",
            "",
            f"Context: {item.get('context')}",
            f"Reason: {item.get('reason')}",
        ]
        self.write_detail("\n".join(lines))

    def write_detail(self, text: str) -> None:
        self.write_text(self.detail_text, text)

    def write_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def write_assistant_log(self, text: str) -> None:
        if hasattr(self, "assistant_log_text"):
            self.write_text(self.assistant_log_text, text)

    def apply_decision_to_selected(self, decision: str) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Select one or more rows first.")
            return
        applied = 0
        blocked = 0
        for selection_id in selected:
            item = self.item_by_id.get(selection_id)
            if not item:
                continue
            if item.get("locked") and decision != "keep":
                blocked += 1
                continue
            if decision not in item.get("allowed_decisions", []):
                blocked += 1
                continue
            self.decisions[selection_id] = decision
            applied += 1
        if applied:
            self.reset_apply_guard()
        self.populate_table()
        self.show_selected_detail()
        self.update_summary()
        self.set_status(f"Decision applied: {applied}; blocked: {blocked}.")
        if blocked:
            messagebox.showwarning("Some rows blocked", f"Applied: {applied}\nBlocked: {blocked}")

    def use_recommended_for_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Select one or more rows first.")
            return
        applied = 0
        for selection_id in selected:
            item = self.item_by_id.get(selection_id)
            if not item or item.get("locked"):
                continue
            decision = item.get("recommended_decision")
            if decision in item.get("allowed_decisions", []):
                self.decisions[selection_id] = decision
                applied += 1
        if applied:
            self.reset_apply_guard()
        self.populate_table()
        self.show_selected_detail()
        self.update_summary()
        self.set_status(f"Recommended decisions applied: {applied}.")

    def use_recommended_for_visible(self) -> None:
        if not self.item_by_id:
            messagebox.showinfo("No rows", "No visible rows to update.")
            return
        applied = 0
        for selection_id, item in list(self.item_by_id.items()):
            if item.get("locked"):
                continue
            decision = item.get("recommended_decision")
            if decision in item.get("allowed_decisions", []):
                self.decisions[selection_id] = decision
                applied += 1
        if applied:
            self.reset_apply_guard()
        self.populate_table()
        self.show_selected_detail()
        self.update_summary()
        self.set_status(f"Visible recommended decisions applied: {applied}.")

    def use_recommended_for_all(self) -> None:
        if not self.selection_session:
            messagebox.showinfo("No scan", "Run a scan first.")
            return
        applied = 0
        recommended = self.build_recommended_decisions()
        for selection_id, decision in recommended.items():
            self.decisions[selection_id] = decision
            applied += 1
        if applied:
            self.reset_apply_guard()
        self.populate_table()
        self.show_selected_detail()
        self.update_summary()
        self.set_status(f"Assistant choices prepared: {applied}.")

    def build_recommended_decisions(self) -> dict[str, str]:
        decisions: dict[str, str] = {}
        for item in self.iter_selection_items():
            if item.get("locked"):
                continue
            selection_id = item.get("selection_id")
            decision = item.get("recommended_decision")
            if selection_id and decision in item.get("allowed_decisions", []):
                decisions[str(selection_id)] = str(decision)
        return decisions

    def count_decisions(self, decisions: dict[str, str] | None = None) -> dict[str, int]:
        source = decisions if decisions is not None else self.decisions
        return {
            "needs_backup": sum(1 for decision in source.values() if decision == "needs_backup"),
            "move_later": sum(1 for decision in source.values() if decision == "move_later"),
            "delete_candidate": sum(1 for decision in source.values() if decision == "delete_candidate"),
            "manual_review": sum(1 for decision in source.values() if decision == "manual_review"),
        }

    def ensure_move_destination(self, move_count: int) -> bool:
        if move_count <= 0:
            return True
        destination = self.move_destination_var.get().strip()
        if destination:
            return True
        scan_path = Path(self.scan_path_var.get().strip() or DEFAULT_SCAN_FOLDER)
        if self.is_demo_scan_path():
            demo_destination = scan_path / "_move_destination"
            demo_destination.mkdir(parents=True, exist_ok=True)
            self.move_destination_var.set(str(demo_destination))
            return True
        self.browse_move_destination()
        return bool(self.move_destination_var.get().strip())

    def preview_ai_plan(self) -> None:
        if not self.selection_session:
            messagebox.showinfo("No scan", "Chạy quét trước, hoặc bấm Chạy full demo để xem luồng mẫu.")
            return
        decisions = self.build_recommended_decisions()
        counts = self.count_decisions(decisions)
        action_count = counts["needs_backup"] + counts["move_later"] + counts["delete_candidate"]
        if action_count <= 0:
            messagebox.showinfo("No safe plan", "AI chưa có hành động an toàn nào để preview. Các item còn lại cần review thủ công.")
            return
        if not self.ensure_move_destination(counts["move_later"]):
            return

        destination = self.move_destination_var.get().strip()
        session = self.selection_session

        def worker() -> dict[str, Any]:
            result: dict[str, Any] = {
                "mode": "dry_run",
                "decisions": decisions,
                "counts": counts,
                "destination": destination,
                "backup": None,
                "move": None,
                "delete": None,
            }
            if counts["needs_backup"] > 0:
                result["backup"] = export_backup_selection_flow_report(
                    decisions,
                    mode="dry_run",
                    final_token=None,
                    session=session,
                    note="Bot Panel AI plan backup dry-run",
                    extra_tags=["bot_panel_ui", "ai_plan"],
                )
            if counts["move_later"] > 0:
                result["move"] = export_move_later_selection_flow_report(
                    decisions,
                    destination_root=destination,
                    mode="dry_run",
                    final_token=None,
                    session=session,
                    note="Bot Panel AI plan move dry-run",
                    extra_tags=["bot_panel_ui", "ai_plan"],
                )
            if counts["delete_candidate"] > 0:
                result["delete"] = export_safe_delete_selection_flow_report(
                    decisions,
                    mode="dry_run",
                    final_token=None,
                    session=session,
                    note="Bot Panel AI plan safe-delete dry-run",
                    extra_tags=["bot_panel_ui", "ai_plan"],
                )
            return result

        self.run_background("AI plan preview", worker, self.load_ai_plan_preview)

    def load_ai_plan_preview(self, result: dict[str, Any]) -> None:
        decisions = dict(result.get("decisions", {}))
        counts = result.get("counts", {})
        self.decisions = decisions
        self.confirm_plan_var.set(False)
        self.confirm_backup_var.set(False)
        self.confirm_move_var.set(False)
        self.confirm_delete_var.set(False)

        backup_result = result.get("backup")
        move_result = result.get("move")
        delete_result = result.get("delete")
        signature = self.decision_signature()
        self.last_plan_preview_signature = signature

        if backup_result:
            backup_flow = backup_result.get("flow", {})
            backup_summary = backup_flow.get("summary", {})
            backup_run_dir = backup_summary.get("backup_run_dir")
            self.pending_backup_run_dir = str(backup_run_dir) if backup_run_dir else None
            if backup_summary.get("backupable_count", 0) > 0 and backup_summary.get("backup_error_count", 0) == 0:
                self.last_backup_dry_run_signature = signature
            else:
                self.last_backup_dry_run_signature = None
            self.last_flow_report = backup_result.get("report") or self.last_flow_report
            self.last_decision_report = (
                backup_flow.get("decision_report", {}).get("report")
                or self.last_decision_report
            )
        if move_result:
            move_summary = move_result.get("flow", {}).get("summary", {})
            if move_summary.get("movable_count", 0) > 0 and move_summary.get("operation_error_count", 0) == 0:
                self.last_move_dry_run_signature = self.move_signature()
            else:
                self.last_move_dry_run_signature = None
            self.last_flow_report = move_result.get("report") or self.last_flow_report
            self.last_decision_report = (
                move_result.get("flow", {}).get("decision_report", {}).get("report")
                or self.last_decision_report
            )
        if delete_result:
            delete_summary = delete_result.get("flow", {}).get("summary", {})
            if delete_summary.get("deletable_count", 0) > 0 and delete_summary.get("delete_error_count", 0) == 0:
                self.last_dry_run_signature = signature
            else:
                self.last_dry_run_signature = None
            self.last_flow_report = delete_result.get("report") or self.last_flow_report
            self.last_decision_report = (
                delete_result.get("flow", {}).get("decision_report", {}).get("report")
                or self.last_decision_report
            )

        self.populate_table()
        self.update_summary()
        self.update_reports_text()
        lines = [
            "AI plan preview ready.",
            "",
            "No files were changed in this preview.",
            f"Backup items: {counts.get('needs_backup', 0)}",
            f"Move items: {counts.get('move_later', 0)}",
            f"Safe cleanup items: {counts.get('delete_candidate', 0)}",
            f"Manual review items: {counts.get('manual_review', 0)}",
            f"Move destination: {result.get('destination') or '-'}",
            "",
            "Preview summaries:",
        ]
        if backup_result:
            lines.append(self.format_demo_summary("Backup preview", backup_result))
        if move_result:
            lines.append(self.format_demo_summary("Move preview", move_result))
        if delete_result:
            lines.append(self.format_demo_summary("Safe cleanup preview", delete_result))
        lines.extend([
            "",
            "Next step:",
            "If the plan looks right, tick 'Toi da xem ke hoach' on the Assistant tab, then click 'Ap dung ke hoach'.",
            "If anything looks wrong, click 'Huy lua chon'.",
        ])
        self.write_detail("\n".join(lines))
        self.write_assistant_log("\n".join(lines))
        self.set_status("AI plan preview ready. Tick confirm if you want to apply.")

    def apply_ai_plan(self) -> None:
        if not self.decisions:
            messagebox.showinfo("No plan", "Bấm Dùng đề xuất AI hoặc Xem kế hoạch AI trước.")
            return
        counts = self.count_decisions()
        action_count = counts["needs_backup"] + counts["move_later"] + counts["delete_candidate"]
        if action_count <= 0:
            messagebox.showinfo("No action", "Kế hoạch hiện tại không có backup/move/dọn an toàn để áp dụng.")
            return
        if not self.confirm_plan_var.get():
            messagebox.showwarning("Confirmation required", "Tick 'Tôi đã xem kế hoạch' sau khi đọc preview.")
            return
        signature = self.decision_signature()
        missing_preview = []
        if counts["needs_backup"] > 0 and self.last_backup_dry_run_signature != signature:
            missing_preview.append("backup")
        if counts["move_later"] > 0 and self.last_move_dry_run_signature != self.move_signature():
            missing_preview.append("move")
        if counts["delete_candidate"] > 0 and self.last_dry_run_signature != signature:
            missing_preview.append("safe cleanup")
        if missing_preview:
            messagebox.showwarning(
                "Preview required",
                "Run Xem kế hoạch AI again before applying: " + ", ".join(missing_preview),
            )
            return
        confirmed = messagebox.askyesno(
            "Apply AI plan",
            "This will apply the reviewed plan.\n\n"
            f"Backup: {counts['needs_backup']}\n"
            f"Move: {counts['move_later']}\n"
            f"Send to Recycle Bin: {counts['delete_candidate']}\n\n"
            "Continue?",
        )
        if not confirmed:
            return

        decisions = dict(self.decisions)
        destination = self.move_destination_var.get().strip()
        backup_run_dir = self.pending_backup_run_dir
        session = self.selection_session

        def worker() -> dict[str, Any]:
            result: dict[str, Any] = {
                "mode": "apply",
                "decisions": decisions,
                "counts": counts,
                "destination": destination,
                "backup": None,
                "move": None,
                "delete": None,
            }
            if counts["needs_backup"] > 0:
                result["backup"] = export_backup_selection_flow_report(
                    decisions,
                    mode="apply",
                    final_token=FINAL_BACKUP_TOKEN,
                    backup_run_dir=backup_run_dir,
                    session=session,
                    note="Bot Panel AI plan backup apply",
                    extra_tags=["bot_panel_ui", "ai_plan"],
                )
            if counts["move_later"] > 0:
                result["move"] = export_move_later_selection_flow_report(
                    decisions,
                    destination_root=destination,
                    mode="apply",
                    final_token=FINAL_MOVE_TOKEN,
                    session=session,
                    note="Bot Panel AI plan move apply",
                    extra_tags=["bot_panel_ui", "ai_plan"],
                )
            if counts["delete_candidate"] > 0:
                result["delete"] = export_safe_delete_selection_flow_report(
                    decisions,
                    mode="apply",
                    final_token=FINAL_DELETE_TOKEN,
                    session=session,
                    note="Bot Panel AI plan safe-delete apply",
                    extra_tags=["bot_panel_ui", "ai_plan"],
                )
            return result

        self.run_background("AI plan apply", worker, self.load_ai_plan_apply)

    def load_ai_plan_apply(self, result: dict[str, Any]) -> None:
        backup_result = result.get("backup")
        move_result = result.get("move")
        delete_result = result.get("delete")
        if backup_result:
            backup_summary = backup_result.get("flow", {}).get("summary", {})
            if backup_summary.get("manifest"):
                self.last_backup_manifest = str(backup_summary["manifest"])
            if backup_summary.get("backup_run_dir"):
                self.last_backup_dir = str(backup_summary["backup_run_dir"])
            self.last_flow_report = backup_result.get("report") or self.last_flow_report
        if move_result:
            move_summary = move_result.get("flow", {}).get("summary", {})
            if move_summary.get("manifest"):
                self.last_move_manifest = str(move_summary["manifest"])
            self.last_flow_report = move_result.get("report") or self.last_flow_report
        if delete_result:
            self.last_flow_report = delete_result.get("report") or self.last_flow_report

        lines = [
            "AI plan applied.",
            "",
            "Apply summaries:",
        ]
        if backup_result:
            lines.append(self.format_demo_summary("Backup apply", backup_result))
        if move_result:
            lines.append(self.format_demo_summary("Move apply", move_result))
        if delete_result:
            lines.append(self.format_demo_summary("Safe cleanup apply", delete_result))
        lines.extend([
            "",
            f"Backup dir: {self.last_backup_dir or '-'}",
            f"Move manifest: {self.last_move_manifest or '-'}",
            f"Final report: {self.last_flow_report or '-'}",
            "",
            "Refresh scan if you want the table to reflect files after move/delete.",
        ])
        self.update_reports_text()
        self.write_detail("\n".join(lines))
        self.write_assistant_log("\n".join(lines))
        self.refresh_after_apply()

    def prepare_recommended_action(self, decision: str) -> int:
        if not self.selection_session:
            messagebox.showinfo("No scan", "Run a scan first.")
            return 0
        applied = 0
        for item in self.iter_selection_items():
            if item.get("locked"):
                continue
            selection_id = item.get("selection_id")
            recommended = item.get("recommended_decision")
            if selection_id and recommended == decision and decision in item.get("allowed_decisions", []):
                self.decisions[str(selection_id)] = decision
                applied += 1
        if applied:
            self.reset_apply_guard()
            self.decision_filter_var.set(decision)
            self.populate_table()
            self.update_summary()
        return applied

    def preview_recommended_backup(self) -> None:
        applied = self.prepare_recommended_action("needs_backup")
        if applied <= 0:
            messagebox.showinfo("No backups", "The latest scan has no recommended backup item.")
            return
        self.backup_dry_run()

    def preview_recommended_delete(self) -> None:
        applied = self.prepare_recommended_action("delete_candidate")
        if applied <= 0:
            messagebox.showinfo("No cleanup", "The latest scan has no recommended safe cleanup item.")
            return
        self.safe_delete_dry_run()

    def preview_recommended_move(self) -> None:
        applied = self.prepare_recommended_action("move_later")
        if applied <= 0:
            messagebox.showinfo("No moves", "The latest scan has no recommended move item.")
            return
        if not self.move_destination_var.get().strip():
            self.browse_move_destination()
        if not self.move_destination_var.get().strip():
            return
        self.move_later_dry_run()

    def prepare_and_focus_recommended(self, decision: str) -> None:
        applied = self.prepare_recommended_action(decision)
        if applied <= 0:
            messagebox.showinfo("No matching items", "Không có item phù hợp với nhóm đề xuất này.")
            return
        self.show_assistant_group(decision)
        self.set_status(f"Đã chọn {applied} item cho nhóm {decision}.")

    def show_assistant_group(self, decision: str) -> None:
        if decision == "do_not_touch":
            self.group_filter_var.set("do_not_touch")
            self.decision_filter_var.set("all")
        else:
            self.group_filter_var.set("all")
            self.decision_filter_var.set(decision)
        self.populate_table()
        self.open_advanced_tab()

    def open_assistant_group(self) -> None:
        self.open_advanced_tab()

    def open_advanced_tab(self) -> None:
        self.notebook.select(self.advanced_tab)

    def show_move_later(self) -> None:
        self.group_filter_var.set("all")
        self.decision_filter_var.set("move_later")
        self.populate_table()

    def show_needs_backup(self) -> None:
        self.group_filter_var.set("all")
        self.decision_filter_var.set("needs_backup")
        self.populate_table()

    def show_delete_candidates(self) -> None:
        self.group_filter_var.set("all")
        self.decision_filter_var.set("delete_candidate")
        self.populate_table()

    def show_all_items(self) -> None:
        self.group_filter_var.set("all")
        self.decision_filter_var.set("all")
        self.populate_table()

    def clear_selected_decisions(self) -> None:
        cleared = False
        for selection_id in self.tree.selection():
            if selection_id in self.decisions:
                cleared = True
                self.decisions.pop(selection_id, None)
        if cleared:
            self.reset_apply_guard()
        self.populate_table()
        self.update_summary()

    def clear_all_decisions(self) -> None:
        self.decisions = {}
        self.reset_apply_guard()
        self.populate_table()
        self.update_summary()
        self.set_status("Choices cleared.")

    def save_decision_report(self) -> None:
        if not self.selection_session:
            messagebox.showinfo("No session", "Run scan/classify or refresh first.")
            return
        if not self.decisions:
            messagebox.showinfo("No choices", "Select at least one decision first.")
            return

        decisions = dict(self.decisions)
        note = self.note_var.get().strip() or "Bot Panel UI decision"

        def worker() -> dict[str, Any]:
            return export_selection_decision_report(
                decisions,
                session=self.selection_session,
                note=note,
                extra_tags=["bot_panel_ui"],
            )

        self.run_background("Save decision report", worker, self.load_decision_export)

    def load_decision_export(self, result: dict[str, Any]) -> None:
        self.last_decision_report = result.get("report")
        decision = result.get("decision", {})
        self.update_reports_text()
        self.write_detail(
            "Decision report saved.\n\n"
            f"Status: {decision.get('status')}\n"
            f"Report: {self.last_decision_report}\n"
            f"Summary: {decision.get('summary')}"
        )

    def safe_delete_dry_run(self) -> None:
        self.run_safe_delete_flow(mode="dry_run", final_token=None)

    def backup_dry_run(self) -> None:
        self.run_backup_flow(mode="dry_run", final_token=None)

    def backup_apply(self) -> None:
        if self.last_backup_dry_run_signature != self.decision_signature():
            messagebox.showwarning(
                "Backup dry-run required",
                "Run Backup dry-run after your latest choices before applying.",
            )
            return
        if not self.confirm_backup_var.get():
            messagebox.showwarning(
                "Confirmation required",
                "Tick the backup confirmation checkbox after reviewing dry-run.",
            )
            return
        backup_count = sum(1 for decision in self.decisions.values() if decision == "needs_backup")
        if backup_count <= 0:
            messagebox.showinfo("No backup choices", "No row is selected as needs_backup.")
            return
        confirmed = messagebox.askyesno(
            "Confirm backup",
            "This will copy eligible needs_backup files to managed backups.\n"
            "Source files are preserved.\n\n"
            f"Backup choices: {backup_count}\nContinue?",
        )
        if not confirmed:
            return
        self.run_backup_flow(mode="apply", final_token=FINAL_BACKUP_TOKEN)

    def run_backup_flow(self, *, mode: str, final_token: str | None) -> None:
        if not self.selection_session:
            messagebox.showinfo("No session", "Run scan/classify or refresh first.")
            return
        if not self.decisions:
            messagebox.showinfo("No choices", "Select at least one decision first.")
            return
        decisions = dict(self.decisions)
        note = self.note_var.get().strip() or "Bot Panel UI backup flow"

        def worker() -> dict[str, Any]:
            return export_backup_selection_flow_report(
                decisions,
                mode=mode,
                final_token=final_token,
                backup_run_dir=self.pending_backup_run_dir if mode == "apply" else None,
                session=self.selection_session,
                note=note,
                extra_tags=["bot_panel_ui"],
            )

        self.run_background(f"Backup {mode}", worker, self.load_backup_flow)

    def load_backup_flow(self, result: dict[str, Any]) -> None:
        self.last_flow_report = result.get("report")
        flow = result.get("flow", {})
        decision_report = flow.get("decision_report", {})
        self.last_decision_report = decision_report.get("report") or self.last_decision_report
        summary = flow.get("summary", {})
        backup_report = flow.get("backup_report", {})
        backup_payload = backup_report.get("backup", {}) if isinstance(backup_report, dict) else {}
        steps = backup_payload.get("steps", []) if isinstance(backup_payload, dict) else []
        lines = [
            "Backup flow finished.",
            "",
            f"Flow status: {flow.get('status')}",
            f"Mode: {flow.get('mode')}",
            f"Decision report: {self.last_decision_report}",
            f"Flow report: {self.last_flow_report}",
            f"Backup dir: {summary.get('backup_run_dir') or '-'}",
            f"Manifest: {summary.get('manifest') or '-'}",
            "",
            f"Backup requested: {summary.get('backup_requested_count')}",
            f"Backupable: {summary.get('backupable_count')}",
            f"Backed up: {summary.get('backed_up_count')}",
            f"Blocked: {summary.get('backup_blocked_count')}",
            f"Errors: {summary.get('backup_error_count')}",
            "",
            "Steps:",
        ]
        for step in steps[:40]:
            lines.append(
                f"- {step.get('selection_id')} | {step.get('step_status')} | "
                f"{step.get('path')} | {step.get('reason')}"
            )
            if step.get("planned_backup_path"):
                lines.append(f"  Backup: {step.get('planned_backup_path')}")
            if step.get("actual_backup_path"):
                lines.append(f"  Copied: {step.get('actual_backup_path')}")
        self.update_reports_text()
        self.write_detail("\n".join(lines))
        if flow.get("mode") == "apply":
            if summary.get("manifest"):
                self.last_backup_manifest = str(summary["manifest"])
            if summary.get("backup_run_dir"):
                self.last_backup_dir = str(summary["backup_run_dir"])
            self.refresh_after_apply()
        elif flow.get("mode") == "dry_run":
            if summary.get("backupable_count", 0) > 0 and summary.get("backup_error_count", 0) == 0:
                self.last_backup_dry_run_signature = self.decision_signature()
                backup_run_dir = summary.get("backup_run_dir")
                self.pending_backup_run_dir = str(backup_run_dir) if backup_run_dir else None
                self.confirm_backup_var.set(False)
                self.set_status("Backup dry-run ready. Tick confirm if you want to apply.")
            else:
                self.last_backup_dry_run_signature = None
                self.pending_backup_run_dir = None
                self.confirm_backup_var.set(False)
                self.set_status("Backup dry-run finished, but no eligible backup is ready.")

    def safe_delete_apply(self) -> None:
        if self.last_dry_run_signature != self.decision_signature():
            messagebox.showwarning(
                "Dry-run required",
                "Run Safe delete dry-run after your latest choices before applying.",
            )
            return
        if not self.confirm_delete_var.get():
            messagebox.showwarning(
                "Confirmation required",
                "Tick the confirmation checkbox after reviewing dry-run.",
            )
            return
        delete_count = sum(1 for decision in self.decisions.values() if decision == "delete_candidate")
        if delete_count <= 0:
            messagebox.showinfo("No delete choices", "No row is selected as delete_candidate.")
            return
        confirmed = messagebox.askyesno(
            "Confirm safe delete",
            "This will send eligible safe_delete files to Recycle Bin only.\n"
            "Review_required/protected files remain blocked.\n\n"
            f"Delete choices: {delete_count}\nContinue?",
        )
        if not confirmed:
            return
        self.run_safe_delete_flow(mode="apply", final_token=FINAL_DELETE_TOKEN)

    def move_later_dry_run(self) -> None:
        self.run_move_later_flow(mode="dry_run", final_token=None)

    def move_later_apply(self) -> None:
        if self.last_move_dry_run_signature != self.move_signature():
            messagebox.showwarning(
                "Move dry-run required",
                "Run Move dry-run after your latest choices and destination before applying.",
            )
            return
        if not self.confirm_move_var.get():
            messagebox.showwarning(
                "Confirmation required",
                "Tick the move confirmation checkbox after reviewing dry-run.",
            )
            return
        move_count = sum(1 for decision in self.decisions.values() if decision == "move_later")
        if move_count <= 0:
            messagebox.showinfo("No move choices", "No row is selected as move_later.")
            return
        destination = self.move_destination_var.get().strip()
        confirmed = messagebox.askyesno(
            "Confirm move",
            "This will move eligible move_later files using the File Operation Adapter.\n"
            "A restore manifest is created after successful moves.\n\n"
            f"Move choices: {move_count}\nDestination: {destination}\nContinue?",
        )
        if not confirmed:
            return
        self.run_move_later_flow(mode="apply", final_token=FINAL_MOVE_TOKEN)

    def run_move_later_flow(self, *, mode: str, final_token: str | None) -> None:
        if not self.selection_session:
            messagebox.showinfo("No session", "Run scan/classify or refresh first.")
            return
        if not self.decisions:
            messagebox.showinfo("No choices", "Select at least one decision first.")
            return
        destination = self.move_destination_var.get().strip()
        if not destination:
            messagebox.showinfo("No destination", "Choose a destination folder for move_later first.")
            return
        decisions = dict(self.decisions)
        note = self.note_var.get().strip() or "Bot Panel UI move later flow"

        def worker() -> dict[str, Any]:
            return export_move_later_selection_flow_report(
                decisions,
                destination_root=destination,
                mode=mode,
                final_token=final_token,
                session=self.selection_session,
                note=note,
                extra_tags=["bot_panel_ui"],
            )

        self.run_background(f"Move later {mode}", worker, self.load_move_later_flow)

    def load_move_later_flow(self, result: dict[str, Any]) -> None:
        self.last_flow_report = result.get("report")
        flow = result.get("flow", {})
        decision_report = flow.get("decision_report", {})
        self.last_decision_report = decision_report.get("report") or self.last_decision_report
        summary = flow.get("summary", {})
        operation_report = flow.get("operation_report", {})
        operation_payload = operation_report.get("operation", {}) if isinstance(operation_report, dict) else {}
        steps = operation_payload.get("steps", []) if isinstance(operation_payload, dict) else []
        lines = [
            "Move later flow finished.",
            "",
            f"Flow status: {flow.get('status')}",
            f"Mode: {flow.get('mode')}",
            f"Destination: {flow.get('destination_root')}",
            f"Decision report: {self.last_decision_report}",
            f"Flow report: {self.last_flow_report}",
            f"Manifest: {summary.get('manifest') or '-'}",
            "",
            f"Move requested: {summary.get('move_requested_count')}",
            f"Movable: {summary.get('movable_count')}",
            f"Moved: {summary.get('moved_count')}",
            f"Blocked: {summary.get('operation_blocked_count')}",
            f"Errors: {summary.get('operation_error_count')}",
            "",
            "Steps:",
        ]
        for step in steps[:40]:
            lines.append(
                f"- {step.get('selection_id')} | {step.get('step_status')} | "
                f"{step.get('path')} | {step.get('reason')}"
            )
            if step.get("planned_target"):
                lines.append(f"  Target: {step.get('planned_target')}")
            if step.get("actual_target"):
                lines.append(f"  Moved to: {step.get('actual_target')}")
        self.update_reports_text()
        self.write_detail("\n".join(lines))
        if flow.get("mode") == "apply":
            if summary.get("manifest"):
                self.last_move_manifest = str(summary["manifest"])
            self.refresh_after_apply()
        elif flow.get("mode") == "dry_run":
            if summary.get("movable_count", 0) > 0 and summary.get("operation_error_count", 0) == 0:
                self.last_move_dry_run_signature = self.move_signature()
                self.confirm_move_var.set(False)
                self.set_status("Move dry-run ready. Tick confirm if you want to apply.")
            else:
                self.last_move_dry_run_signature = None
                self.confirm_move_var.set(False)
                self.set_status("Move dry-run finished, but no eligible move is ready.")

    def run_safe_delete_flow(self, *, mode: str, final_token: str | None) -> None:
        if not self.selection_session:
            messagebox.showinfo("No session", "Run scan/classify or refresh first.")
            return
        if not self.decisions:
            messagebox.showinfo("No choices", "Select at least one decision first.")
            return
        decisions = dict(self.decisions)
        note = self.note_var.get().strip() or "Bot Panel UI safe delete flow"

        def worker() -> dict[str, Any]:
            return export_safe_delete_selection_flow_report(
                decisions,
                mode=mode,
                final_token=final_token,
                session=self.selection_session,
                note=note,
                extra_tags=["bot_panel_ui"],
            )

        self.run_background(f"Safe delete {mode}", worker, self.load_safe_delete_flow)

    def load_safe_delete_flow(self, result: dict[str, Any]) -> None:
        self.last_flow_report = result.get("report")
        flow = result.get("flow", {})
        decision_report = flow.get("decision_report", {})
        self.last_decision_report = decision_report.get("report") or self.last_decision_report
        summary = flow.get("summary", {})
        delete_report = flow.get("delete_report", {})
        delete_payload = delete_report.get("delete", {}) if isinstance(delete_report, dict) else {}
        steps = delete_payload.get("steps", []) if isinstance(delete_payload, dict) else []
        lines = [
            "Safe delete flow finished.",
            "",
            f"Flow status: {flow.get('status')}",
            f"Mode: {flow.get('mode')}",
            f"Decision report: {self.last_decision_report}",
            f"Flow report: {self.last_flow_report}",
            "",
            f"Delete requested: {summary.get('delete_requested_count')}",
            f"Deletable: {summary.get('deletable_count')}",
            f"Deleted: {summary.get('deleted_count')}",
            f"Blocked: {summary.get('delete_blocked_count')}",
            f"Errors: {summary.get('delete_error_count')}",
            "",
            "Steps:",
        ]
        for step in steps[:40]:
            lines.append(
                f"- {step.get('selection_id')} | {step.get('step_status')} | "
                f"{step.get('path')} | {step.get('reason')}"
            )
        self.update_reports_text()
        self.write_detail("\n".join(lines))
        if flow.get("mode") == "apply":
            self.refresh_after_apply()
        elif flow.get("mode") == "dry_run":
            if summary.get("deletable_count", 0) > 0 and summary.get("delete_error_count", 0) == 0:
                self.last_dry_run_signature = self.decision_signature()
                self.confirm_delete_var.set(False)
                self.set_status("Dry-run ready. Tick confirm if you want to apply.")
            else:
                self.last_dry_run_signature = None
                self.confirm_delete_var.set(False)
                self.set_status("Dry-run finished, but no eligible delete is ready.")

    def refresh_after_apply(self) -> None:
        self.confirm_plan_var.set(False)
        self.confirm_backup_var.set(False)
        self.confirm_delete_var.set(False)
        self.confirm_move_var.set(False)
        self.last_plan_preview_signature = None
        self.last_backup_dry_run_signature = None
        self.pending_backup_run_dir = None
        self.last_dry_run_signature = None
        self.last_move_dry_run_signature = None
        self.set_status("Apply finished. Refresh when you want to rescan.")

    def reset_apply_guard(self) -> None:
        self.confirm_plan_var.set(False)
        self.confirm_backup_var.set(False)
        self.confirm_delete_var.set(False)
        self.confirm_move_var.set(False)
        self.last_plan_preview_signature = None
        self.last_backup_dry_run_signature = None
        self.pending_backup_run_dir = None
        self.last_dry_run_signature = None
        self.last_move_dry_run_signature = None

    def decision_signature(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(
            (str(selection_id), str(decision))
            for selection_id, decision in self.decisions.items()
        ))

    def move_signature(self) -> tuple[tuple[str, str], ...]:
        return (
            ("destination", self.move_destination_var.get().strip()),
            *self.decision_signature(),
        )

    def undo_last_move(self) -> None:
        if not self.last_move_manifest:
            messagebox.showinfo("No move manifest", "No move manifest is available in this UI session.")
            return
        manifest = Path(self.last_move_manifest)
        if not manifest.exists():
            messagebox.showwarning("Missing manifest", f"Manifest does not exist:\n{manifest}")
            return
        confirmed = messagebox.askyesno(
            "Undo last move",
            "This will restore files from the latest move manifest.\n\n"
            f"Manifest: {manifest}\nContinue?",
        )
        if not confirmed:
            return

        def worker() -> dict[str, Any]:
            return restore_manifest(manifest)

        self.run_background("Undo last move", worker, self.load_undo_result)

    def load_undo_result(self, result: dict[str, Any]) -> None:
        self.write_detail(
            "Undo last move finished.\n\n"
            f"Status: {result.get('status')}\n"
            f"Restored: {result.get('restored_count')}\n"
            f"Failed: {result.get('failed_count')}\n"
            f"Report: {result.get('report')}"
        )
        self.last_move_manifest = None
        self.update_reports_text()
        self.set_status("Undo last move done. Refresh when you want to rescan.")

    def is_demo_scan_path(self) -> bool:
        try:
            scan_path = Path(self.scan_path_var.get()).resolve()
            demo_root = DEMO_SANDBOX_ROOT.resolve()
        except OSError:
            return False
        return scan_path == demo_root or demo_root in scan_path.parents

    def open_selected_location(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Select one row first.")
            return
        item = self.item_by_id.get(selected[0])
        if not item:
            return
        path = item.get("path")
        if not path:
            messagebox.showinfo("No path", "This item does not have a file path.")
            return
        target = Path(path)
        if target.exists() and target.is_file():
            subprocess.Popen(["explorer", "/select,", str(target)])
        elif target.exists() and target.is_dir():
            self.open_path(target)
        elif target.parent.exists():
            self.open_path(target.parent)
        else:
            messagebox.showwarning("Missing path", f"Path does not exist:\n{target}")

    def open_move_destination(self) -> None:
        destination = self.move_destination_var.get().strip()
        if not destination:
            messagebox.showinfo("No destination", "Choose a destination folder first.")
            return
        target = Path(destination)
        if not target.exists():
            messagebox.showwarning("Missing destination", f"Destination does not exist:\n{target}")
            return
        self.open_path(target)

    def open_last_backup(self) -> None:
        target_text = self.last_backup_dir or self.last_backup_manifest
        if not target_text:
            messagebox.showinfo("No backup", "No backup folder or manifest is available in this UI session.")
            return
        target = Path(target_text)
        if target.is_file():
            target = target.parent
        if not target.exists():
            messagebox.showwarning("Missing backup", f"Backup path does not exist:\n{target}")
            return
        self.open_path(target)

    def open_path(self, path: str | Path) -> None:
        target = Path(path)
        try:
            os.startfile(str(target))
        except OSError as error:
            messagebox.showerror("Open failed", str(error))


if __name__ == "__main__":
    run_bot_panel()
