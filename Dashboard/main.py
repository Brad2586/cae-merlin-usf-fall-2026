"""Modern companion dashboard for Merlin and sponsor-provided host programs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = PROJECT_ROOT / "Logs" / "runtime_status.json"
CONFIG_PATH = PROJECT_ROOT / "config" / "dashboard.json"

BACKGROUND = "#0f172a"
SURFACE = "#172033"
SURFACE_ALT = "#1e293b"
BORDER = "#334155"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
DANGER = "#ef4444"


class MerlinDashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Merlin Control Center")
        self.root.geometry("1180x760")
        self.root.minsize(940, 620)
        self.root.configure(bg=BACKGROUND)
        self.config = self._load_config()
        self.processes: dict[str, subprocess.Popen] = {}
        self._last_changes = None

        self.merlin_state = tk.StringVar(value="Offline")
        self.server_state = tk.StringVar(value="Disconnected")
        self.model_state = tk.StringVar(value="—")
        self.last_command = tk.StringVar(value="No command received")
        self.last_transcription = tk.StringVar(value="—")
        self.message = tk.StringVar(value="Start Merlin to begin.")
        self.path_summary = tk.StringVar()

        self._configure_styles()
        self._build_ui()
        self._refresh_path_summary()
        self._poll_status()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dark.TFrame",
            background=BACKGROUND,
        )
        style.configure(
            "Surface.TFrame",
            background=SURFACE,
            relief="flat",
        )
        style.configure(
            "Title.TLabel",
            background=BACKGROUND,
            foreground=TEXT,
            font=("Segoe UI Semibold", 24),
        )
        style.configure(
            "Subtitle.TLabel",
            background=BACKGROUND,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=SURFACE,
            foreground=MUTED,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "CardValue.TLabel",
            background=SURFACE,
            foreground=TEXT,
            font=("Segoe UI Semibold", 16),
        )
        style.configure(
            "SurfaceText.TLabel",
            background=SURFACE,
            foreground=TEXT,
            font=("Segoe UI", 10),
        )
        style.configure(
            "MutedSurface.TLabel",
            background=SURFACE,
            foreground=MUTED,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Primary.TButton",
            background=ACCENT,
            foreground="#082f49",
            borderwidth=0,
            padding=(18, 10),
            font=("Segoe UI Semibold", 10),
        )
        style.map("Primary.TButton", background=[("active", "#7dd3fc")])
        style.configure(
            "Secondary.TButton",
            background=SURFACE_ALT,
            foreground=TEXT,
            bordercolor=BORDER,
            padding=(16, 10),
            font=("Segoe UI Semibold", 10),
        )
        style.map("Secondary.TButton", background=[("active", BORDER)])
        style.configure(
            "Changes.Treeview",
            background=SURFACE,
            fieldbackground=SURFACE,
            foreground=TEXT,
            rowheight=32,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Changes.Treeview.Heading",
            background=SURFACE_ALT,
            foreground=MUTED,
            borderwidth=0,
            padding=(8, 8),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Changes.Treeview",
            background=[("selected", "#075985")],
            foreground=[("selected", TEXT)],
        )

    def _build_ui(self):
        outer = ttk.Frame(self.root, style="Dark.TFrame", padding=24)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        header = ttk.Frame(outer, style="Dark.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Merlin Control Center", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Live status and requested simulator changes",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Button(
            header,
            text="Open Logs",
            command=self._open_logs,
            style="Secondary.TButton",
        ).grid(row=0, column=1, rowspan=2, padx=(8, 0))

        cards = ttk.Frame(outer, style="Dark.TFrame")
        cards.grid(row=1, column=0, sticky="ew", pady=(22, 16))
        for column in range(3):
            cards.columnconfigure(column, weight=1, uniform="cards")
        self.merlin_indicator = self._status_card(
            cards, 0, "MERLIN", self.merlin_state
        )
        self.server_indicator = self._status_card(
            cards, 1, "SIMULATOR SERVER", self.server_state
        )
        self.model_indicator = self._status_card(
            cards, 2, "ACTIVE MODEL", self.model_state, indicator=False
        )

        actions = ttk.Frame(outer, style="Dark.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        ttk.Button(
            actions,
            text="Start Merlin",
            command=self._start_merlin,
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Launch DemoHost",
            command=lambda: self._launch_external("demo_host_path", "DemoHost"),
            style="Secondary.TButton",
        ).pack(side="left", padx=(10, 0))
        ttk.Button(
            actions,
            text="Launch IOS",
            command=lambda: self._launch_external("ios_path", "IOS"),
            style="Secondary.TButton",
        ).pack(side="left", padx=(10, 0))
        ttk.Button(
            actions,
            text="Configure Paths",
            command=self._configure_paths,
            style="Secondary.TButton",
        ).pack(side="right")

        command_panel = ttk.Frame(outer, style="Surface.TFrame", padding=18)
        command_panel.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        command_panel.columnconfigure(1, weight=1)
        ttk.Label(
            command_panel, text="LATEST VOICE INPUT", style="CardTitle.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            command_panel, text="Transcription", style="MutedSurface.TLabel"
        ).grid(row=1, column=0, sticky="nw", pady=(12, 0))
        ttk.Label(
            command_panel,
            textvariable=self.last_transcription,
            style="SurfaceText.TLabel",
            wraplength=760,
        ).grid(row=1, column=1, sticky="w", padx=(20, 0), pady=(12, 0))
        ttk.Label(command_panel, text="Processing", style="MutedSurface.TLabel").grid(
            row=2, column=0, sticky="nw", pady=(8, 0)
        )
        ttk.Label(
            command_panel,
            textvariable=self.last_command,
            style="SurfaceText.TLabel",
        ).grid(row=2, column=1, sticky="w", padx=(20, 0), pady=(8, 0))

        changes_panel = ttk.Frame(outer, style="Surface.TFrame", padding=18)
        changes_panel.grid(row=4, column=0, sticky="nsew")
        changes_panel.columnconfigure(0, weight=1)
        changes_panel.rowconfigure(1, weight=1)
        ttk.Label(
            changes_panel,
            text="REQUESTED SIMULATOR CHANGES",
            style="CardTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        columns = ("time", "display_name", "variable", "value", "status")
        self.changes = ttk.Treeview(
            changes_panel,
            columns=columns,
            show="headings",
            style="Changes.Treeview",
            selectmode="browse",
        )
        headings = {
            "time": "Time",
            "display_name": "Change",
            "variable": "Host Variable",
            "value": "Requested Value",
            "status": "Status",
        }
        widths = {
            "time": 100,
            "display_name": 230,
            "variable": 260,
            "value": 150,
            "status": 110,
        }
        for column in columns:
            self.changes.heading(column, text=headings[column])
            self.changes.column(
                column,
                width=widths[column],
                minwidth=80,
                stretch=column in {"display_name", "variable"},
            )
        scrollbar = ttk.Scrollbar(
            changes_panel, orient="vertical", command=self.changes.yview
        )
        self.changes.configure(yscrollcommand=scrollbar.set)
        self.changes.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        footer = ttk.Frame(outer, style="Dark.TFrame")
        footer.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(
            footer, textvariable=self.message, style="Subtitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            footer, textvariable=self.path_summary, style="Subtitle.TLabel"
        ).grid(row=0, column=1, sticky="e")

    def _status_card(self, parent, column, title, variable, indicator=True):
        card = ttk.Frame(parent, style="Surface.TFrame", padding=18)
        card.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=(0 if column == 0 else 6, 0 if column == 2 else 6),
        )
        card.columnconfigure(1, weight=1)
        dot = tk.Label(
            card,
            text="●" if indicator else "◆",
            fg=MUTED,
            bg=SURFACE,
            font=("Segoe UI", 14),
        )
        dot.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ttk.Label(card, text=title, style="CardTitle.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(card, textvariable=variable, style="CardValue.TLabel").grid(
            row=1, column=1, sticky="w", pady=(3, 0)
        )
        return dot

    def _load_config(self):
        defaults = {"demo_host_path": "", "ios_path": ""}
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            defaults.update(
                {key: value for key, value in loaded.items() if key in defaults}
            )
        except (OSError, json.JSONDecodeError):
            pass
        return defaults

    def _save_config(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self.config, indent=2) + "\n",
            encoding="utf-8",
        )
        self._refresh_path_summary()

    def _resolve_path(self, configured_path):
        path = Path(configured_path)
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()

    def _start_merlin(self):
        existing = self.processes.get("merlin")
        if existing and existing.poll() is None:
            messagebox.showinfo("Merlin", "Merlin is already running.")
            return
        try:
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            self.processes["merlin"] = subprocess.Popen(
                [sys.executable, str(PROJECT_ROOT / "Pipeline" / "main.py")],
                cwd=PROJECT_ROOT,
                creationflags=creation_flags,
            )
            self.message.set("Merlin is starting in a separate console.")
        except OSError as exc:
            messagebox.showerror("Unable to start Merlin", str(exc))

    def _launch_external(self, config_key, display_name):
        path = self._resolve_path(self.config.get(config_key, ""))
        if not path.is_file():
            selected = filedialog.askopenfilename(
                title=f"Select {display_name} executable",
                filetypes=[("Windows applications", "*.exe"), ("All files", "*.*")],
            )
            if not selected:
                return
            path = Path(selected)
            self.config[config_key] = str(path)
            self._save_config()

        existing = self.processes.get(config_key)
        if existing and existing.poll() is None:
            messagebox.showinfo(display_name, f"{display_name} is already running.")
            return
        try:
            self.processes[config_key] = subprocess.Popen(
                [str(path)],
                cwd=path.parent,
            )
            self.message.set(f"{display_name} launched.")
        except OSError as exc:
            messagebox.showerror(f"Unable to launch {display_name}", str(exc))

    def _configure_paths(self):
        for config_key, display_name in (
            ("demo_host_path", "DemoHost"),
            ("ios_path", "IOS"),
        ):
            selected = filedialog.askopenfilename(
                title=f"Select {display_name} executable",
                initialdir=str(self._resolve_path(self.config.get(config_key, "")).parent),
                filetypes=[("Windows applications", "*.exe"), ("All files", "*.*")],
            )
            if selected:
                self.config[config_key] = selected
        self._save_config()

    def _open_logs(self):
        log_directory = PROJECT_ROOT / "Logs"
        log_directory.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(log_directory)
        except OSError as exc:
            messagebox.showerror("Unable to open logs", str(exc))

    def _refresh_path_summary(self):
        demo_ready = self._resolve_path(self.config.get("demo_host_path", "")).is_file()
        ios_ready = self._resolve_path(self.config.get("ios_path", "")).is_file()
        self.path_summary.set(
            f"DemoHost {'✓' if demo_ready else 'not set'}   "
            f"IOS {'✓' if ios_ready else 'not set'}"
        )

    def _poll_status(self):
        try:
            with STATUS_PATH.open("r", encoding="utf-8") as file:
                status = json.load(file)
            updated = datetime.fromisoformat(status["updated_at"])
            age = (datetime.now(updated.tzinfo) - updated).total_seconds()
            if age > 8:
                status["merlin_state"] = "offline"
                status["server_state"] = "unknown"
                status["message"] = "Merlin status is stale."
            self._render_status(status)
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            self._render_status(
                {
                    "merlin_state": "offline",
                    "server_state": "disconnected",
                    "active_model": "—",
                    "last_transcription": "",
                    "last_command": "",
                    "message": "Waiting for Merlin status.",
                    "requested_changes": [],
                }
            )
        self.root.after(750, self._poll_status)

    def _render_status(self, status):
        merlin = str(status.get("merlin_state", "offline"))
        server = str(status.get("server_state", "disconnected"))
        self.merlin_state.set(merlin.replace("_", " ").title())
        self.server_state.set(server.replace("_", " ").title())
        self.model_state.set(str(status.get("active_model", "—")).title())
        self.last_transcription.set(status.get("last_transcription") or "—")
        self.last_command.set(status.get("last_command") or "No command received")
        self.message.set(status.get("message") or "")

        self.merlin_indicator.configure(
            fg=SUCCESS if merlin in {"ready", "listening", "processing"} else DANGER
        )
        server_colors = {
            "connected": SUCCESS,
            "reconnecting": WARNING,
            "disconnected": DANGER,
            "unknown": MUTED,
        }
        self.server_indicator.configure(fg=server_colors.get(server, MUTED))
        self.model_indicator.configure(fg=ACCENT)

        changes = status.get("requested_changes", [])
        fingerprint = json.dumps(changes, sort_keys=True, default=str)
        if fingerprint == self._last_changes:
            return
        self._last_changes = fingerprint
        self.changes.delete(*self.changes.get_children())
        for change in changes:
            timestamp = str(change.get("time", ""))
            if "T" in timestamp:
                timestamp = timestamp.split("T", 1)[1][:8]
            self.changes.insert(
                "",
                "end",
                values=(
                    timestamp,
                    change.get("display_name", ""),
                    change.get("variable", ""),
                    change.get("value", ""),
                    str(change.get("status", "")).title(),
                ),
            )


def main():
    root = tk.Tk()
    MerlinDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
