"""Startup Decision Window.

A focused graphical "Decision Inbox" shown on boot (or on demand). It runs a
read-only full-drive scan, then presents the safe-delete candidates with
exactly the three choices the user asked for:

    - Khong xoa gi
    - Xoa file da chon
    - Xoa tat ca file an toan duoc de xuat

It never deletes anything silently. Real deletes go through the existing
guarded Safe Delete flow: dry-run first, an explicit confirm dialog, then the
internal final token, sending files only to the Recycle Bin.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, messagebox, ttk
from typing import Any

from config.settings import (
    DEFAULT_LARGE_FILE_MB,
    DEFAULT_RESULT_LIMIT,
    DEFAULT_SCAN_FOLDER,
)
from tools.core.auto_scan_session import export_auto_scan_session_report
from tools.core.bot_controller import (
    FINAL_DELETE_TOKEN,
    build_bot_controller_result,
    build_selection_session,
    export_safe_delete_selection_flow_report,
    iter_selection_items,
)
from tools.core.safety_utils import format_size
from tools.core.startup_scan import build_advisory, resolve_scan_mode


def run_startup_window(*, scan_mode: str | None = None) -> None:
    root = tk.Tk()
    StartupWindow(root, scan_mode=scan_mode)
    root.mainloop()


class StartupWindow:
    def __init__(self, root: tk.Tk, *, scan_mode: str | None = None) -> None:
        self.root = root
        self.scan_mode = scan_mode
        self.session: dict[str, Any] | None = None
        self.delete_items: list[dict[str, Any]] = []
        self.row_to_id: dict[str, str] = {}
        self.busy = False

        root.title("Tro ly khoi dong - Decision Inbox")
        root.geometry("900x620")

        header = ttk.Frame(root, padding=12)
        header.pack(fill=X)
        ttk.Label(
            header,
            text="Tro ly da quet may. Ban quyet dinh xoa gi.",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        self.status_var = tk.StringVar(value="Dang quet o dia, vui long doi...")
        ttk.Label(header, textvariable=self.status_var, foreground="#555").pack(anchor="w")

        body = ttk.Frame(root, padding=(12, 0, 12, 0))
        body.pack(fill=BOTH, expand=True)
        ttk.Label(
            body,
            text="File co the xoa an toan (chon nhieu dong bang Ctrl/Shift):",
        ).pack(anchor="w", pady=(8, 4))

        table_frame = ttk.Frame(body)
        table_frame.pack(fill=BOTH, expand=True)
        columns = ("size", "path")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="extended"
        )
        self.tree.heading("size", text="Dung luong")
        self.tree.heading("path", text="Duong dan")
        self.tree.column("size", width=110, anchor="e")
        self.tree.column("path", width=720, anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        footer = ttk.Frame(root, padding=12)
        footer.pack(fill=X)
        self.btn_skip = ttk.Button(footer, text="Khong xoa gi", command=self.on_skip)
        self.btn_skip.pack(side=LEFT)
        self.btn_delete_selected = ttk.Button(
            footer, text="Xoa file da chon", command=self.on_delete_selected, state="disabled"
        )
        self.btn_delete_selected.pack(side=LEFT, padx=8)
        self.btn_delete_all = ttk.Button(
            footer,
            text="Xoa tat ca file an toan",
            command=self.on_delete_all,
            state="disabled",
        )
        self.btn_delete_all.pack(side=LEFT)
        ttk.Label(
            footer,
            text="Moi lan xoa deu co xem truoc + xac nhan, file chi vao Recycle Bin.",
            foreground="#888",
        ).pack(side=RIGHT)

        self.root.after(100, self.start_scan)

    # ----- scanning -----

    def start_scan(self) -> None:
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        try:
            mode = resolve_scan_mode(self.scan_mode)
            scan_export = export_auto_scan_session_report(
                root_drive=DEFAULT_SCAN_FOLDER,
                storage_mode=mode,
                large_file_mb=DEFAULT_LARGE_FILE_MB,
                result_limit=DEFAULT_RESULT_LIMIT,
                extra_tags=["startup_scan", "boot", "ui"],
            )
            auto_scan = scan_export["scan"]
            bot_result = build_bot_controller_result(include_items=True)
            session = build_selection_session(bot_result=bot_result, include_items=True)
            advisory = build_advisory(bot_result)
            delete_items = [
                item
                for item in iter_selection_items(session)
                if "delete_candidate" in item.get("allowed_decisions", [])
            ]
            snapshot = auto_scan.get("snapshot", {})
            processes = snapshot.get("processes", {})
            payload = {
                "mode": mode,
                "session": session,
                "advisory": advisory,
                "delete_items": delete_items,
                "ram": processes.get("system_memory_percent"),
                "root": auto_scan.get("root_drive"),
            }
            self.root.after(0, lambda: self._on_scan_done(payload))
        except Exception as exc:  # noqa: BLE001 - surface any scan error in UI
            self.root.after(0, lambda: self._on_scan_error(exc))

    def _on_scan_done(self, payload: dict[str, Any]) -> None:
        self.session = payload["session"]
        self.delete_items = payload["delete_items"]
        advisory = payload["advisory"]

        self.status_var.set(
            f"O {payload['root']} | che do {payload['mode']} | RAM {payload['ram']}% | "
            f"{advisory['issue_count']} van de, {advisory['delete_candidate_count']} file co the xoa an toan, "
            f"{advisory['do_not_touch_count']} khong duoc dung"
        )

        self.tree.delete(*self.tree.get_children())
        self.row_to_id.clear()
        for item in self.delete_items:
            size_text = item.get("size_text") or format_size(int(item.get("size") or 0))
            row = self.tree.insert("", END, values=(size_text, item.get("path")))
            self.row_to_id[row] = item["selection_id"]

        if self.delete_items:
            self.btn_delete_selected.configure(state="normal")
            self.btn_delete_all.configure(state="normal")
        else:
            self.status_var.set(self.status_var.get() + " | Khong co file an toan nao de xoa.")

    def _on_scan_error(self, exc: Exception) -> None:
        self.status_var.set(f"Loi khi quet: {exc}")
        messagebox.showerror("Loi quet", str(exc))

    # ----- decisions -----

    def on_skip(self) -> None:
        self.root.destroy()

    def on_delete_selected(self) -> None:
        if self.busy:
            messagebox.showinfo("Dang chay", "Mot tac vu dang chay, vui long doi.")
            return
        selected_rows = self.tree.selection()
        if not selected_rows:
            messagebox.showinfo("Chua chon", "Hay chon it nhat mot file de xoa.")
            return
        ids = [self.row_to_id[row] for row in selected_rows if row in self.row_to_id]
        self._delete_ids(ids, note="startup_window_select")

    def on_delete_all(self) -> None:
        if self.busy:
            messagebox.showinfo("Dang chay", "Mot tac vu dang chay, vui long doi.")
            return
        ids = list(self.row_to_id.values())
        if not ids:
            messagebox.showinfo("Khong co file", "Khong co file an toan nao de xoa.")
            return
        self._delete_ids(ids, note="startup_window_delete_all_safe")

    def _delete_ids(self, ids: list[str], *, note: str) -> None:
        if not ids or self.session is None:
            return
        decisions = {selection_id: "delete_candidate" for selection_id in ids}
        self._set_busy(True)
        self.status_var.set(f"Dang xem truoc {len(decisions)} file (dry-run)...")
        threading.Thread(
            target=self._delete_worker, args=(decisions, note), daemon=True
        ).start()

    def _delete_worker(self, decisions: dict[str, str], note: str) -> None:
        try:
            dry = export_safe_delete_selection_flow_report(
                decisions,
                mode="dry_run",
                session=self.session,
                note=note,
                extra_tags=["startup_window"],
            )
            deletable = dry["flow"]["summary"].get("deletable_count", 0)
            self.root.after(0, lambda: self._after_dry_run(decisions, note, deletable))
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._delete_failed(exc))

    def _after_dry_run(self, decisions: dict[str, str], note: str, deletable: int) -> None:
        if deletable <= 0:
            self._set_busy(False)
            self.status_var.set("Khong co file nao du dieu kien safe_delete.")
            messagebox.showinfo(
                "Khong xoa", "Khong co file nao du dieu kien an toan sau khi xem truoc."
            )
            return

        confirm = messagebox.askyesno(
            "Xac nhan xoa",
            f"Se dua {deletable} file vao Recycle Bin (co the khoi phuc).\n\nBan chac chan?",
        )
        if not confirm:
            self._set_busy(False)
            self.status_var.set("Da huy. Khong xoa gi.")
            return

        self.status_var.set(f"Dang xoa {deletable} file vao Recycle Bin...")
        threading.Thread(
            target=self._apply_worker, args=(decisions, note), daemon=True
        ).start()

    def _apply_worker(self, decisions: dict[str, str], note: str) -> None:
        try:
            applied = export_safe_delete_selection_flow_report(
                decisions,
                mode="apply",
                final_token=FINAL_DELETE_TOKEN,
                session=self.session,
                note=note,
                extra_tags=["startup_window"],
            )
            summary = applied["flow"]["summary"]
            deleted = summary.get("deleted_count", 0)
            report = applied.get("report")
            self.root.after(0, lambda: self._apply_done(deleted, report))
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._delete_failed(exc))

    def _apply_done(self, deleted: int, report: str | None) -> None:
        self._set_busy(False)
        self.status_var.set(f"Da dua {deleted} file vao Recycle Bin. Report: {report}")
        messagebox.showinfo(
            "Hoan tat",
            f"Da dua {deleted} file vao Recycle Bin.\nCo the khoi phuc tu Recycle Bin neu can.",
        )
        # Refresh so deleted rows disappear.
        self.start_scan()

    def _delete_failed(self, exc: Exception) -> None:
        self._set_busy(False)
        self.status_var.set(f"Loi khi xoa: {exc}")
        messagebox.showerror("Loi xoa", str(exc))

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.btn_delete_selected.configure(state=state)
        self.btn_delete_all.configure(state=state)


if __name__ == "__main__":
    run_startup_window()
