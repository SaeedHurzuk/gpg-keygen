#!/usr/bin/env python3
"""
GPG-Keygen — First-run / repair installer.

Uses ONLY Python stdlib (tkinter, subprocess, threading) so it runs before
the venv exists. Creates the venv, installs packages, then launches the
main app — no reopen required.
"""

import os, sys, subprocess, threading, time, shutil
import tkinter as tk
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
RESOURCES   = Path(__file__).parent
MAIN_APP    = RESOURCES / "gpg_keygen_app.py"
VENV_DIR    = Path.home() / "Library" / "Application Support" / "GPG-Keygen" / "venv"
VENV_PYTHON = VENV_DIR / "bin" / "python3"
VENV_PIP    = VENV_DIR / "bin" / "pip"
PACKAGES    = ["customtkinter", "colorama"]

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#0a0c0f"
SURFACE  = "#0f1318"
SURFACE2 = "#161b22"
BORDER   = "#1e2530"
GREEN    = "#00ff88"
GREEN_DK = "#003d1f"
RED      = "#ff4455"
AMBER    = "#ffb700"
TEXT     = "#e2e8f0"
DIM      = "#64748b"
MONO     = "Menlo"
SANS     = "Helvetica Neue"


class InstallerApp(tk.Tk):

    def __init__(self, sys_python: str):
        super().__init__()
        self._sys_python = sys_python
        self._bar_pos    = 0.0
        self._bar_target = 0.0
        self._bar_w      = 480

        # Detect repair mode (venv exists but something is missing)
        self._repair = VENV_DIR.exists() and VENV_PYTHON.exists()

        self._setup_window()
        self._build_ui()
        self.after(16,  self._tick_bar)
        self.after(300, self._start_worker)

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        W, H = 540, 360
        self.title("GPG Keygen — Setup")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - W) // 2
        y = (self.winfo_screenheight() - H) // 2
        self.geometry(f"{W}x{H}+{x}+{y}")
        self.lift(); self.focus_force()
        self.protocol("WM_DELETE_WINDOW", lambda: None)   # block accidental close

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # 1-px green top border
        tk.Frame(self, bg=GREEN, height=2).pack(fill="x", side="top")

        wrap = tk.Frame(self, bg=BORDER, padx=1, pady=1)
        wrap.pack(fill="both", expand=True)
        card = tk.Frame(wrap, bg=BG)
        card.pack(fill="both", expand=True)

        body = tk.Frame(card, bg=BG)
        body.pack(fill="both", expand=True, padx=40, pady=30)

        # ── Header ───────────────────────────────────────────────────────────
        hrow = tk.Frame(body, bg=BG)
        hrow.pack(fill="x")

        tk.Label(hrow, text="⬡", font=(MONO, 30), fg=GREEN, bg=BG).pack(side="left", padx=(0,14))

        htxt = tk.Frame(hrow, bg=BG)
        htxt.pack(side="left")
        tk.Label(htxt, text="GPG KEYGEN", font=(MONO, 18, "bold"), fg=GREEN, bg=BG, anchor="w").pack(fill="x")
        subtitle = "Repairing environment…" if self._repair else "Setting up for the first time…"
        tk.Label(htxt, text=subtitle, font=(SANS, 12), fg=DIM, bg=BG, anchor="w").pack(fill="x")

        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(20, 18))

        # ── Status labels ─────────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Starting…")
        self._detail_var = tk.StringVar(value="")

        tk.Label(body, textvariable=self._status_var,
                 font=(MONO, 12), fg=TEXT, bg=BG, anchor="w").pack(fill="x")
        tk.Label(body, textvariable=self._detail_var,
                 font=(MONO, 10), fg=DIM,  bg=BG, anchor="w").pack(fill="x", pady=(3, 14))

        # ── Progress bar ──────────────────────────────────────────────────────
        bar_bg = tk.Frame(body, bg=SURFACE2, height=8)
        bar_bg.pack(fill="x")
        bar_bg.pack_propagate(False)

        self._canvas = tk.Canvas(bar_bg, bg=SURFACE2, height=8, highlightthickness=0, bd=0)
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Configure>", lambda e: setattr(self, "_bar_w", e.width))
        self._bar_rect = self._canvas.create_rectangle(0, 0, 0, 8, fill=GREEN, outline="", tags="bar")

        # ── Step checklist ────────────────────────────────────────────────────
        steps_frame = tk.Frame(body, bg=BG)
        steps_frame.pack(fill="x", pady=(20, 0))

        self._dots = {}
        step_defs = [
            ("venv",   "Create isolated Python environment"),
            ("pkgs",   f"Install {', '.join(PACKAGES)}"),
            ("launch", "Launch GPG Keygen"),
        ]
        if self._repair:
            step_defs[0] = ("venv", "Verify Python environment")

        for key, label in step_defs:
            row = tk.Frame(steps_frame, bg=BG)
            row.pack(fill="x", pady=2)
            dot = tk.Label(row, text="○", font=(MONO, 11), fg=DIM, bg=BG, width=3, anchor="w")
            dot.pack(side="left")
            tk.Label(row, text=label, font=(SANS, 11), fg=DIM, bg=BG, anchor="w").pack(side="left")
            self._dots[key] = dot

        # ── Footer note ───────────────────────────────────────────────────────
        self._note_var = tk.StringVar(value="This only happens once.")
        tk.Label(body, textvariable=self._note_var,
                 font=(SANS, 10), fg=DIM, bg=BG, anchor="w").pack(side="bottom", fill="x")

    # ── Bar animation ~60 fps eased ───────────────────────────────────────────

    def _tick_bar(self):
        diff = self._bar_target - self._bar_pos
        self._bar_pos += diff * 0.14 if abs(diff) > 0.001 else diff
        px = max(0, int(self._bar_pos * self._bar_w))
        self._canvas.coords(self._bar_rect, 0, 0, px, 8)
        self.after(16, self._tick_bar)

    def _progress(self, f: float):
        self._bar_target = max(0.0, min(1.0, f))

    # ── Step helpers ──────────────────────────────────────────────────────────

    def _active(self, key):
        d = self._dots.get(key)
        if d: d.config(text="◌", fg=AMBER)

    def _done(self, key):
        d = self._dots.get(key)
        if d: d.config(text="✔", fg=GREEN)

    def _fail(self, key):
        d = self._dots.get(key)
        if d: d.config(text="✖", fg=RED)

    def _status(self, msg, detail=""):
        self._status_var.set(msg)
        self._detail_var.set(detail)

    # ── Worker (background thread) ────────────────────────────────────────────

    def _start_worker(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        def ui(fn): self.after(0, fn)

        try:
            # ── Step 1: venv ─────────────────────────────────────────────────
            ui(lambda: self._active("venv"))
            ui(lambda: self._progress(0.05))

            if self._repair:
                ui(lambda: self._status("Verifying environment…", str(VENV_DIR)))
                # Check if venv python works at all; rebuild if not
                r = subprocess.run([str(VENV_PYTHON), "-c", "import sys"], capture_output=True)
                if r.returncode != 0:
                    ui(lambda: self._status("Rebuilding broken environment…", ""))
                    shutil.rmtree(str(VENV_DIR), ignore_errors=True)
                    self._create_venv()
            else:
                ui(lambda: self._status("Creating Python environment…", str(VENV_DIR)))
                self._create_venv()

            ui(lambda: self._done("venv"))
            ui(lambda: self._progress(0.30))

            # ── Step 2: upgrade pip ───────────────────────────────────────────
            ui(lambda: self._status("Upgrading pip…", ""))
            subprocess.run(
                [str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "-q"],
                capture_output=True,
            )
            ui(lambda: self._progress(0.40))

            # ── Step 3: packages ──────────────────────────────────────────────
            ui(lambda: self._active("pkgs"))
            n = len(PACKAGES)
            for i, pkg in enumerate(PACKAGES):
                already = subprocess.run(
                    [str(VENV_PYTHON), "-c", f"import {pkg}"], capture_output=True
                ).returncode == 0

                msg = f"Verifying {pkg}…" if already else f"Installing {pkg}…"
                detail = f"Package {i+1} of {n}"
                ui(lambda m=msg, d=detail: self._status(m, d))
                ui(lambda p=0.40 + 0.50*(i/n): self._progress(p))

                if not already:
                    r = subprocess.run(
                        [str(VENV_PIP), "install", pkg, "-q"],
                        capture_output=True, text=True,
                    )
                    if r.returncode != 0:
                        raise RuntimeError(f"Failed to install {pkg}:\n{r.stderr.strip()}")

                # Verify
                v = subprocess.run(
                    [str(VENV_PYTHON), "-c", f"import {pkg}"], capture_output=True
                )
                if v.returncode != 0:
                    raise RuntimeError(f"{pkg} installed but cannot be imported.")

            ui(lambda: self._done("pkgs"))
            ui(lambda: self._progress(0.95))

            # ── Step 4: launch ────────────────────────────────────────────────
            ui(lambda: self._active("launch"))
            ui(lambda: self._status("Launching GPG Keygen…", ""))
            ui(lambda: self._note_var.set("All done — starting the app now."))
            time.sleep(0.7)
            ui(lambda: self._done("launch"))
            ui(lambda: self._progress(1.0))
            time.sleep(0.35)
            ui(self._launch)

        except Exception as exc:
            ui(lambda e=str(exc): self._show_error(e))

    def _create_venv(self):
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [self._sys_python, "-m", "venv", str(VENV_DIR)],
            capture_output=True, text=True,
        )
        if r.returncode != 0 or not VENV_PYTHON.exists():
            raise RuntimeError(f"venv creation failed:\n{r.stderr.strip()}")

    # ── Launch + close ────────────────────────────────────────────────────────

    def _launch(self):
        subprocess.Popen(
            [str(VENV_PYTHON), str(MAIN_APP)],
            close_fds=True,
            start_new_session=True,
        )
        self.after(500, self.destroy)

    # ── Error screen ──────────────────────────────────────────────────────────

    def _show_error(self, msg: str):
        self._canvas.itemconfig(self._bar_rect, fill=RED)
        self._progress(1.0)
        self._status("Setup failed", "")
        self._note_var.set("You can retry or install manually.")

        # Clear steps, show error box + retry button
        for w in list(self.winfo_children()):
            pass  # keep window intact

        # Find body frame and append error widgets
        body = None
        for w in self.winfo_children():
            if isinstance(w, tk.Frame) and w.cget("bg") == BORDER:
                for c in w.winfo_children():
                    if isinstance(c, tk.Frame) and c.cget("bg") == BG:
                        for b in c.winfo_children():
                            if isinstance(b, tk.Frame) and b.cget("bg") == BG:
                                body = b
                                break

        if body:
            err_card = tk.Frame(body, bg=SURFACE2, padx=12, pady=10)
            err_card.pack(fill="x", pady=(6, 0))
            tk.Label(err_card, text=msg[:400], font=(MONO, 10), fg=RED,
                     bg=SURFACE2, justify="left", wraplength=420, anchor="w").pack(fill="x")

            tk.Button(
                body, text="✕  Delete environment & retry",
                font=(MONO, 11), fg=GREEN, bg=GREEN_DK,
                activebackground="#005533", activeforeground=GREEN,
                relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                command=self._retry,
            ).pack(pady=(12, 0), anchor="w")

    def _retry(self):
        shutil.rmtree(str(VENV_DIR), ignore_errors=True)
        # Restart the whole installer window
        self.destroy()
        app = InstallerApp(self._sys_python)
        app.mainloop()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: installer.py <system_python>"); sys.exit(1)
    InstallerApp(sys.argv[1]).mainloop()
