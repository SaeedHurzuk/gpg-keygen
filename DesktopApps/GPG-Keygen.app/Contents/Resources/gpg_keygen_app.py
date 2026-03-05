#!/usr/bin/env python3
"""
gpg-keygen — macOS GUI Application
A fully interactive GPG key generation tool with a dark terminal-luxury aesthetic.

Requirements:
    Python 3.9+  (ships with macOS)
    customtkinter  (auto-installed on first run)
    colorama       (auto-installed on first run)
    gpg / gpg2     (install via: brew install gnupg  or  https://gpgtools.org)
"""

# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTS
#  Dependencies (customtkinter, colorama) are guaranteed by the app launcher,
#  which creates a private venv at:
#    ~/Library/Application Support/GPG-Keygen/venv
# ══════════════════════════════════════════════════════════════════════════════
import subprocess
import sys
import os
import customtkinter as ctk
import threading
import re
import shutil
import platform
import tempfile
import atexit
import getpass
import queue
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS — obsidian terminal luxury
# ══════════════════════════════════════════════════════════════════════════════
COL = {
    "bg":           "#0a0c0f",   # near-black obsidian
    "surface":      "#0f1318",   # card background
    "surface2":     "#161b22",   # elevated surface
    "border":       "#1e2530",   # subtle border
    "border_bright":"#2d3748",   # hover border
    "green":        "#00ff88",   # phosphor green accent
    "green_dim":    "#00cc6a",   # dimmer green
    "green_dark":   "#003d1f",   # green tint bg
    "amber":        "#ffb700",   # warning amber
    "red":          "#ff4455",   # error red
    "red_dark":     "#2d0008",   # red tint bg
    "blue":         "#4d9fff",   # info blue
    "text":         "#e2e8f0",   # primary text
    "text_dim":     "#64748b",   # muted text
    "text_bright":  "#f8fafc",   # bright text
    "mono":         "#a8ff78",   # monospace value colour
}

FONT_MONO  = ("JetBrains Mono", "Menlo", "Monaco", "Courier New")
FONT_SANS  = ("SF Pro Display", "Helvetica Neue", "Segoe UI", "Arial")

def font(family_list, size, weight="normal"):
    for f in family_list:
        return (f, size, weight)  # tkinter tries the first it finds

# ══════════════════════════════════════════════════════════════════════════════
#  GPG UTILITIES  (same logic as gpg-keygen.py)
# ══════════════════════════════════════════════════════════════════════════════
def find_gpg() -> str | None:
    for c in ["gpg2", "gpg"]:
        p = shutil.which(c)
        if p:
            return p
    if platform.system() == "Windows":
        base = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        for cand in [base / "GnuPG/bin/gpg.exe", base / "Gpg4win/bin/gpg.exe"]:
            if cand.is_file():
                return str(cand)
    return None

def gpg_version(gpg: str) -> tuple:
    try:
        out = subprocess.run([gpg, "--version"], capture_output=True, text=True).stdout
        ver = out.splitlines()[0].split()[-1]
        parts = ver.split(".")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return 2, 0

def configure_agent(gpg: str, major: int, minor: int, homedir: str):
    if not (major >= 2 and minor >= 1):
        return

    import time

    home = Path(homedir) if homedir else Path.home() / ".gnupg"
    home.mkdir(parents=True, exist_ok=True)
    try:
        home.chmod(0o700)
    except Exception:
        pass

    # Ensure allow-loopback-pinentry is in gpg-agent.conf.
    conf = home / "gpg-agent.conf"
    try:
        text = conf.read_text() if conf.exists() else ""
        if "allow-loopback-pinentry" not in text:
            conf.write_text(text + "\nallow-loopback-pinentry\n")
            try:
                conf.chmod(0o600)
            except Exception:
                pass
    except OSError:
        pass

    homedir_args = ["--homedir", str(home)]

    # Kill any existing agent (safe even if none running) so it restarts
    # and picks up the updated conf with allow-loopback-pinentry.
    for tool, args in [
        ("gpgconf", homedir_args + ["--kill", "gpg-agent"]),
        ("gpgconf", homedir_args + ["--launch", "gpg-agent"]),
    ]:
        try:
            subprocess.run([tool] + args, capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # Wait up to 3 s for the agent socket to appear.
    socket_candidates = [
        home / "S.gpg-agent",
        Path(f"/var/folders") ,  # macOS puts sockets in var/folders — just wait
    ]
    for _ in range(30):
        if (home / "S.gpg-agent").exists():
            break
        time.sleep(0.1)

    # Reload so the running agent reads the updated conf.
    try:
        subprocess.run(
            ["gpgconf"] + homedir_args + ["--reload", "gpg-agent"],
            capture_output=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def build_batch(cfg: dict, major: int) -> str:
    is_ecc = cfg["key_type"] in ("ECDSA", "EdDSA")
    lines = [f"Key-Type: {cfg['key_type']}"]
    if not is_ecc:
        lines.append(f"Key-Length: {cfg['key_length']}")
    lines.append("Key-Usage: sign,cert")
    lines.append(f"Subkey-Type: {cfg['subkey_type']}")
    lines.append("Subkey-Usage: encrypt")
    if cfg["subkey_type"] != "ECDH" and cfg.get("subkey_length", "0") not in ("", "0"):
        lines.append(f"Subkey-Length: {cfg['subkey_length']}")
    lines.append(f"Name-Real: {cfg['name_real']}")
    if cfg.get("name_comment"):
        lines.append(f"Name-Comment: {cfg['name_comment']}")
    lines.append(f"Name-Email: {cfg['name_email']}")
    lines.append(f"Expire-Date: {cfg['expire_date']}")
    if cfg.get("no_protection"):
        if major >= 2:
            lines.append("%no-protection")
    elif cfg.get("passphrase"):
        lines.append(f"Passphrase: {cfg['passphrase']}")
    lines.append("%commit")
    return "\n".join(lines) + "\n"

SUBKEY_MAP = {"RSA": "RSA", "DSA": "ELG-E", "ECDSA": "ECDH", "EdDSA": "ECDH"}

# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM WIDGETS
# ══════════════════════════════════════════════════════════════════════════════

class GlowButton(ctk.CTkButton):
    """Button with phosphor-green glow on hover."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            fg_color=COL["green_dark"],
            hover_color="#005533",
            text_color=COL["green"],
            border_color=COL["green"],
            border_width=1,
            corner_radius=4,
            font=font(FONT_MONO, 13, "bold"),
            height=40,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class DangerButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        defaults = dict(
            fg_color=COL["red_dark"],
            hover_color="#4a0010",
            text_color=COL["red"],
            border_color=COL["red"],
            border_width=1,
            corner_radius=4,
            font=font(FONT_MONO, 13, "bold"),
            height=40,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class FieldLabel(ctk.CTkLabel):
    def __init__(self, master, text, **kwargs):
        super().__init__(
            master, text=text,
            text_color=COL["text_dim"],
            font=font(FONT_MONO, 11),
            anchor="w",
            **kwargs,
        )


class StyledEntry(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        defaults = dict(
            fg_color=COL["surface2"],
            border_color=COL["border"],
            text_color=COL["text"],
            placeholder_text_color=COL["text_dim"],
            font=font(FONT_MONO, 13),
            corner_radius=4,
            border_width=1,
            height=36,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class StyledSegmented(ctk.CTkSegmentedButton):
    def __init__(self, master, **kwargs):
        defaults = dict(
            fg_color=COL["surface2"],
            selected_color=COL["green_dark"],
            selected_hover_color="#005533",
            unselected_color=COL["surface2"],
            unselected_hover_color=COL["border"],
            text_color=COL["text_dim"],
            text_color_disabled=COL["text_dim"],
            font=font(FONT_MONO, 12),
            corner_radius=4,
            border_width=1,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class SectionFrame(ctk.CTkFrame):
    def __init__(self, master, title="", **kwargs):
        defaults = dict(
            fg_color=COL["surface"],
            border_color=COL["border"],
            border_width=1,
            corner_radius=6,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)
        if title:
            title_bar = ctk.CTkFrame(self, fg_color=COL["border"], height=1, corner_radius=0)
            lbl = ctk.CTkLabel(
                self, text=f"  {title}  ",
                text_color=COL["green"],
                font=font(FONT_MONO, 11, "bold"),
                fg_color=COL["surface"],
            )
            lbl.place(x=16, y=-8)


class TerminalBox(ctk.CTkTextbox):
    """Scrolling terminal output pane."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            fg_color=COL["bg"],
            text_color=COL["mono"],
            font=font(FONT_MONO, 12),
            border_color=COL["border"],
            border_width=1,
            corner_radius=4,
            wrap="word",
            state="disabled",
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)
        # Tag colours
        self._textbox.tag_config("green",  foreground=COL["green"])
        self._textbox.tag_config("red",    foreground=COL["red"])
        self._textbox.tag_config("amber",  foreground=COL["amber"])
        self._textbox.tag_config("dim",    foreground=COL["text_dim"])
        self._textbox.tag_config("bright", foreground=COL["text_bright"])
        self._textbox.tag_config("blue",   foreground=COL["blue"])

    def append(self, text: str, tag: str = ""):
        self.configure(state="normal")
        if tag:
            self._textbox.insert("end", text + "\n", tag)
        else:
            self.insert("end", text + "\n")
        self.configure(state="disabled")
        self._textbox.see("end")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class GPGKeygenApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("GPG Keygen")
        self.geometry("1280x720")
        self.minsize(960, 640)
        self.configure(fg_color=COL["bg"])

        # State
        self.gpg_path  = find_gpg()
        self.gpg_major = 2
        self.gpg_minor = 0
        if self.gpg_path:
            self.gpg_major, self.gpg_minor = gpg_version(self.gpg_path)

        self._gen_thread: threading.Thread | None = None
        self._log_queue: queue.Queue = queue.Queue()
        self._tmpfile: str | None = None

        self._build_ui()
        self._check_gpg_status()
        self._poll_log_queue()

        atexit.register(self._cleanup)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Title bar ──────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COL["surface"], corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="⬡  GPG KEYGEN",
            text_color=COL["green"],
            font=font(FONT_MONO, 20, "bold"),
        ).pack(side="left", padx=24, pady=0)

        self.status_dot = ctk.CTkLabel(
            header, text="●  checking...",
            text_color=COL["amber"],
            font=font(FONT_MONO, 12),
        )
        self.status_dot.pack(side="right", padx=24)

        # ── Thin accent line ───────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color=COL["green"], height=1, corner_radius=0).pack(fill="x")

        # ── Main body ─────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=COL["bg"], corner_radius=0)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        # Left panel — form
        self.left_scroll = ctk.CTkScrollableFrame(
            body, fg_color=COL["bg"],
            scrollbar_button_color=COL["border"],
            scrollbar_button_hover_color=COL["border_bright"],
            corner_radius=0, width=480,
        )
        self.left_scroll.pack(side="left", fill="both", expand=False, padx=(20, 10), pady=16)

        # Right panel — terminal output
        right = ctk.CTkFrame(body, fg_color=COL["bg"], corner_radius=0)
        right.pack(side="right", fill="both", expand=True, padx=(10, 20), pady=16)

        self._build_form(self.left_scroll)
        self._build_terminal(right)
        self._bind_smooth_scroll(self.left_scroll)

    def _build_form(self, parent):

        # ── IDENTITY ──────────────────────────────────────────────────────
        self._section_header(parent, "IDENTITY")

        id_frame = SectionFrame(parent)
        id_frame.pack(fill="x", pady=(0, 12))
        id_inner = ctk.CTkFrame(id_frame, fg_color="transparent")
        id_inner.pack(fill="x", padx=16, pady=14)

        FieldLabel(id_inner, "NAME-REAL *").pack(anchor="w")
        self.e_name = StyledEntry(id_inner, placeholder_text="Alice Example")
        self.e_name.pack(fill="x", pady=(4, 10))

        FieldLabel(id_inner, "EMAIL *").pack(anchor="w")
        self.e_email = StyledEntry(id_inner, placeholder_text="alice@example.com")
        self.e_email.pack(fill="x", pady=(4, 10))

        FieldLabel(id_inner, "COMMENT (optional)").pack(anchor="w")
        self.e_comment = StyledEntry(id_inner, placeholder_text="Work key")
        self.e_comment.pack(fill="x", pady=(4, 0))

        # ── KEY TYPE ──────────────────────────────────────────────────────
        self._section_header(parent, "KEY TYPE")

        kt_frame = SectionFrame(parent)
        kt_frame.pack(fill="x", pady=(0, 12))
        kt_inner = ctk.CTkFrame(kt_frame, fg_color="transparent")
        kt_inner.pack(fill="x", padx=16, pady=14)

        self.key_type_var = ctk.StringVar(value="RSA")
        seg = StyledSegmented(
            kt_inner,
            values=["RSA", "DSA", "ECDSA", "EdDSA"],
            variable=self.key_type_var,
            command=self._on_key_type_change,
        )
        seg.pack(fill="x", pady=(0, 12))

        # Key type description
        self.type_desc = ctk.CTkLabel(
            kt_inner,
            text="Universal compatibility · widely supported",
            text_color=COL["text_dim"],
            font=font(FONT_SANS, 12),
            anchor="w",
        )
        self.type_desc.pack(anchor="w", pady=(0, 12))

        # Key length (hidden for ECC)
        self.len_container = ctk.CTkFrame(kt_inner, fg_color="transparent")
        self.len_container.pack(fill="x")

        FieldLabel(self.len_container, "KEY LENGTH").pack(anchor="w")
        self.key_len_var = ctk.StringVar(value="4096")
        len_seg = StyledSegmented(
            self.len_container,
            values=["2048", "3072", "4096"],
            variable=self.key_len_var,
        )
        len_seg.pack(fill="x", pady=(4, 8))
        self.e_custom_len = StyledEntry(
            self.len_container,
            placeholder_text="Custom bits (e.g. 8192)",
            width=200,
        )
        self.e_custom_len.pack(anchor="w", pady=(0, 0))

        # ── EXPIRY ────────────────────────────────────────────────────────
        self._section_header(parent, "EXPIRY")

        exp_frame = SectionFrame(parent)
        exp_frame.pack(fill="x", pady=(0, 12))
        exp_inner = ctk.CTkFrame(exp_frame, fg_color="transparent")
        exp_inner.pack(fill="x", padx=16, pady=14)

        self.expire_var = ctk.StringVar(value="1y")
        exp_seg = StyledSegmented(
            exp_inner,
            values=["6m", "1y", "2y", "5y", "Never"],
            variable=self.expire_var,
            command=self._on_expire_change,
        )
        exp_seg.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(exp_inner, fg_color="transparent")
        row.pack(fill="x")
        FieldLabel(row, "CUSTOM (e.g. 3y, 18m, 90d)").pack(side="left")
        self.e_custom_expire = StyledEntry(row, width=160, placeholder_text="0 = never")
        self.e_custom_expire.pack(side="right")

        # ── GPG HOMEDIR ───────────────────────────────────────────────────
        self._section_header(parent, "GPG HOMEDIR")

        hd_frame = SectionFrame(parent)
        hd_frame.pack(fill="x", pady=(0, 12))
        hd_inner = ctk.CTkFrame(hd_frame, fg_color="transparent")
        hd_inner.pack(fill="x", padx=16, pady=14)

        hd_row = ctk.CTkFrame(hd_inner, fg_color="transparent")
        hd_row.pack(fill="x")
        self.e_homedir = StyledEntry(hd_row, placeholder_text="~/.gnupg  (default)")
        self.e_homedir.pack(side="left", fill="x", expand=True, padx=(0, 8))
        GlowButton(hd_row, text="Browse", width=80, command=self._pick_homedir).pack(side="right")

        # ── SECURITY ──────────────────────────────────────────────────────
        self._section_header(parent, "SECURITY")

        sec_frame = SectionFrame(parent)
        sec_frame.pack(fill="x", pady=(0, 12))
        sec_inner = ctk.CTkFrame(sec_frame, fg_color="transparent")
        sec_inner.pack(fill="x", padx=16, pady=14)

        self.no_passphrase_var = ctk.BooleanVar(value=False)
        self.cb_no_pass = ctk.CTkCheckBox(
            sec_inner,
            text="No passphrase  (automation / CI mode)",
            variable=self.no_passphrase_var,
            text_color=COL["text_dim"],
            font=font(FONT_MONO, 12),
            fg_color=COL["green_dark"],
            hover_color="#005533",
            border_color=COL["border"],
            checkmark_color=COL["green"],
            command=self._on_passphrase_toggle,
        )
        self.cb_no_pass.pack(anchor="w", pady=(0, 10))

        self.pass_fields = ctk.CTkFrame(sec_inner, fg_color="transparent")
        self.pass_fields.pack(fill="x")

        FieldLabel(self.pass_fields, "PASSPHRASE").pack(anchor="w")
        self.e_pass = StyledEntry(self.pass_fields, placeholder_text="Enter passphrase", show="●")
        self.e_pass.pack(fill="x", pady=(4, 8))

        FieldLabel(self.pass_fields, "CONFIRM PASSPHRASE").pack(anchor="w")
        self.e_pass2 = StyledEntry(self.pass_fields, placeholder_text="Confirm passphrase", show="●")
        self.e_pass2.pack(fill="x", pady=(4, 0))

        # ── EXPORT ────────────────────────────────────────────────────────
        self._section_header(parent, "EXPORT")

        ex_frame = SectionFrame(parent)
        ex_frame.pack(fill="x", pady=(0, 12))
        ex_inner = ctk.CTkFrame(ex_frame, fg_color="transparent")
        ex_inner.pack(fill="x", padx=16, pady=14)

        self.export_pub_var = ctk.BooleanVar(value=True)
        self.export_sec_var = ctk.BooleanVar(value=False)
        self.armor_var      = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            ex_inner, text="Export public key  (.asc)",
            variable=self.export_pub_var,
            text_color=COL["text"], font=font(FONT_MONO, 12),
            fg_color=COL["green_dark"], hover_color="#005533",
            border_color=COL["border"], checkmark_color=COL["green"],
        ).pack(anchor="w", pady=(0, 6))

        ctk.CTkCheckBox(
            ex_inner, text="Export secret key  (.asc) ⚠",
            variable=self.export_sec_var,
            text_color=COL["amber"], font=font(FONT_MONO, 12),
            fg_color=COL["green_dark"], hover_color="#005533",
            border_color=COL["border"], checkmark_color=COL["amber"],
        ).pack(anchor="w", pady=(0, 6))

        ctk.CTkCheckBox(
            ex_inner, text="ASCII armored (.asc)  — uncheck for binary (.gpg)",
            variable=self.armor_var,
            text_color=COL["text_dim"], font=font(FONT_MONO, 12),
            fg_color=COL["green_dark"], hover_color="#005533",
            border_color=COL["border"], checkmark_color=COL["green"],
        ).pack(anchor="w", pady=(0, 12))

        outdir_row = ctk.CTkFrame(ex_inner, fg_color="transparent")
        outdir_row.pack(fill="x")
        FieldLabel(outdir_row, "OUTPUT DIRECTORY").pack(anchor="w")
        dir_row = ctk.CTkFrame(ex_inner, fg_color="transparent")
        dir_row.pack(fill="x", pady=(4, 0))
        self.e_outdir = StyledEntry(dir_row, placeholder_text="./  (current directory)")
        self.e_outdir.pack(side="left", fill="x", expand=True, padx=(0, 8))
        GlowButton(dir_row, text="Browse", width=80, command=self._pick_outdir).pack(side="right")

        # ── ACTIONS ───────────────────────────────────────────────────────
        self._section_header(parent, "ACTIONS")

        act_frame = ctk.CTkFrame(parent, fg_color="transparent")
        act_frame.pack(fill="x", pady=(0, 16))

        self.btn_dryrun = GlowButton(
            act_frame, text="⊞  DRY RUN",
            fg_color=COL["surface2"],
            text_color=COL["text_dim"],
            border_color=COL["border"],
            hover_color=COL["border"],
            command=self._do_dry_run,
        )
        self.btn_dryrun.pack(fill="x", pady=(0, 8))

        self.btn_generate = GlowButton(
            act_frame, text="⬡  GENERATE KEY",
            fg_color=COL["green_dark"],
            text_color=COL["green"],
            border_color=COL["green"],
            font=font(FONT_MONO, 14, "bold"),
            height=48,
            command=self._do_generate,
        )
        self.btn_generate.pack(fill="x", pady=(0, 8))

        self.btn_clear = DangerButton(
            act_frame, text="✕  CLEAR",
            height=36,
            command=self._do_clear,
        )
        self.btn_clear.pack(fill="x")

    def _build_terminal(self, parent):
        ctk.CTkLabel(
            parent,
            text="OUTPUT",
            text_color=COL["text_dim"],
            font=font(FONT_MONO, 11, "bold"),
            anchor="w",
        ).pack(anchor="w", padx=4, pady=(0, 6))

        self.terminal = TerminalBox(parent)
        self.terminal.pack(fill="both", expand=True)

        # Key info panel (hidden until key is generated)
        self.keyinfo_frame = SectionFrame(parent, title="")
        # Don't pack yet — shown after generation

        # Copy buttons row
        copy_row = ctk.CTkFrame(parent, fg_color="transparent")
        copy_row.pack(fill="x", pady=(8, 0))

        GlowButton(
            copy_row, text="Copy Fingerprint",
            fg_color=COL["surface2"], text_color=COL["text_dim"],
            border_color=COL["border"], height=32,
            font=font(FONT_MONO, 11),
            command=lambda: self._copy_to_clipboard(self.fp_var),
        ).pack(side="left", padx=(0, 6))

        GlowButton(
            copy_row, text="Copy Key ID",
            fg_color=COL["surface2"], text_color=COL["text_dim"],
            border_color=COL["border"], height=32,
            font=font(FONT_MONO, 11),
            command=lambda: self._copy_to_clipboard(self.kid_var),
        ).pack(side="left")

        self.fp_var  = ctk.StringVar(value="")
        self.kid_var = ctk.StringVar(value="")
        self.uid_var = ctk.StringVar(value="")

        # Key info display
        ki = ctk.CTkFrame(parent, fg_color=COL["surface"], border_color=COL["border"],
                          border_width=1, corner_radius=6)
        ki.pack(fill="x", pady=(8, 0))
        ki_inner = ctk.CTkFrame(ki, fg_color="transparent")
        ki_inner.pack(fill="x", padx=14, pady=10)

        self._ki_row(ki_inner, "FINGERPRINT", self.fp_var)
        self._ki_row(ki_inner, "UID",         self.uid_var)
        self._ki_row(ki_inner, "KEY ID",       self.kid_var)

    def _ki_row(self, parent, label, var):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=f"{label:<14}", text_color=COL["text_dim"],
                     font=font(FONT_MONO, 11), width=110, anchor="w").pack(side="left")
        ctk.CTkLabel(row, textvariable=var, text_color=COL["mono"],
                     font=font(FONT_MONO, 11), anchor="w").pack(side="left", fill="x", expand=True)

    def _section_header(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            text_color=COL["green"],
            font=font(FONT_MONO, 10, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(14, 4))

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _on_key_type_change(self, value):
        desc_map = {
            "RSA":   "Universal compatibility · widely supported",
            "DSA":   "Legacy signing key · no encryption subkey",
            "ECDSA": "Elliptic curve · compact & fast",
            "EdDSA": "Modern Ed25519 curve · recommended",
        }
        self.type_desc.configure(text=desc_map.get(value, ""))
        is_ecc = value in ("ECDSA", "EdDSA")
        if is_ecc:
            self.len_container.pack_forget()
        else:
            self.len_container.pack(fill="x")

    def _on_expire_change(self, value):
        if value == "Never":
            self.e_custom_expire.delete(0, "end")
            self.e_custom_expire.insert(0, "0")
        elif value in ("6m", "1y", "2y", "5y"):
            self.e_custom_expire.delete(0, "end")

    def _on_passphrase_toggle(self):
        if self.no_passphrase_var.get():
            self.pass_fields.pack_forget()
        else:
            self.pass_fields.pack(fill="x")

    def _pick_homedir(self):
        d = filedialog.askdirectory(title="Select GPG Homedir")
        if d:
            self.e_homedir.delete(0, "end")
            self.e_homedir.insert(0, d)

    def _pick_outdir(self):
        d = filedialog.askdirectory(title="Select Output Directory")
        if d:
            self.e_outdir.delete(0, "end")
            self.e_outdir.insert(0, d)

    def _copy_to_clipboard(self, var: ctk.StringVar):
        val = var.get()
        if val:
            self.clipboard_clear()
            self.clipboard_append(val)
            self._log("  ✔  Copied to clipboard.", "green")

    # ── Validation ────────────────────────────────────────────────────────────

    def _collect_config(self) -> dict | None:
        cfg = {}

        cfg["name_real"]  = self.e_name.get().strip()
        cfg["name_email"] = self.e_email.get().strip()
        cfg["name_comment"] = self.e_comment.get().strip()

        if not cfg["name_real"]:
            self._log("  ✖  Name-Real is required.", "red"); return None
        if not cfg["name_email"] or "@" not in cfg["name_email"]:
            self._log("  ✖  A valid email address is required.", "red"); return None

        cfg["key_type"]   = self.key_type_var.get()
        cfg["subkey_type"] = SUBKEY_MAP.get(cfg["key_type"], "RSA")

        is_ecc = cfg["key_type"] in ("ECDSA", "EdDSA")
        if is_ecc:
            cfg["key_length"] = "0"
            cfg["subkey_length"] = "0"
        else:
            custom = self.e_custom_len.get().strip()
            if custom:
                if not custom.isdigit():
                    self._log("  ✖  Custom key length must be a number.", "red"); return None
                cfg["key_length"] = custom
            else:
                cfg["key_length"] = self.key_len_var.get()
            cfg["subkey_length"] = cfg["key_length"]

        custom_exp = self.e_custom_expire.get().strip()
        expire_map = {"6m": "6m", "1y": "1y", "2y": "2y", "5y": "5y", "Never": "0"}
        if custom_exp:
            cfg["expire_date"] = custom_exp
        else:
            cfg["expire_date"] = expire_map.get(self.expire_var.get(), "1y")

        cfg["gpg_homedir"] = self.e_homedir.get().strip()
        cfg["output_dir"]  = self.e_outdir.get().strip()

        cfg["no_protection"] = self.no_passphrase_var.get()
        if not cfg["no_protection"]:
            p1 = self.e_pass.get()
            p2 = self.e_pass2.get()
            if not p1:
                self._log("  ✖  Passphrase is required. Check 'No passphrase' to skip.", "red")
                return None
            if p1 != p2:
                self._log("  ✖  Passphrases do not match.", "red")
                return None
            cfg["passphrase"] = p1
        else:
            cfg["passphrase"] = ""

        cfg["export_pub"] = self.export_pub_var.get()
        cfg["export_sec"] = self.export_sec_var.get()
        cfg["armor"]      = self.armor_var.get()

        return cfg

    # ── Actions ───────────────────────────────────────────────────────────────

    def _do_dry_run(self):
        cfg = self._collect_config()
        if not cfg:
            return
        self.terminal.clear()
        self._log("  ┌─ Dry run — batch file ──────────────────────", "dim")
        batch = build_batch(cfg, self.gpg_major)
        for line in batch.splitlines():
            display = "  Passphrase: [REDACTED]" if line.startswith("Passphrase:") else f"  {line}"
            self._log(display)
        self._log("  └─────────────────────────────────────────────", "dim")

    def _do_generate(self):
        if not self.gpg_path:
            self._log("  ✖  GPG not found. Install GnuPG and restart.", "red")
            return
        if self._gen_thread and self._gen_thread.is_alive():
            self._log("  ⚠  Generation already in progress...", "amber")
            return

        cfg = self._collect_config()
        if not cfg:
            return

        self.terminal.clear()
        self.fp_var.set("")
        self.kid_var.set("")
        self.uid_var.set("")

        self.btn_generate.configure(state="disabled", text="⬡  GENERATING...")
        self._gen_thread = threading.Thread(target=self._generate_worker, args=(cfg,), daemon=True)
        self._gen_thread.start()

    def _do_clear(self):
        self.terminal.clear()
        self.fp_var.set("")
        self.kid_var.set("")
        self.uid_var.set("")

    # ── Generation Worker (runs in thread) ────────────────────────────────────

    def _generate_worker(self, cfg: dict):
        try:
            self._log(f"\n  ➜  Generating key for {cfg['name_real']} <{cfg['name_email']}> ...")

            # Directories
            homedir = ""
            if cfg["gpg_homedir"]:
                homedir = str(Path(cfg["gpg_homedir"]).expanduser())
                Path(homedir).mkdir(parents=True, exist_ok=True)
                try: Path(homedir).chmod(0o700)
                except: pass

            if cfg["output_dir"]:
                outdir = str(Path(cfg["output_dir"]).expanduser())
                Path(outdir).mkdir(parents=True, exist_ok=True)
            else:
                outdir = "."

            # GPG agent config
            configure_agent(self.gpg_path, self.gpg_major, self.gpg_minor, homedir)

            # Build batch content
            batch_content = build_batch(cfg, self.gpg_major)

            # Write batch file inside the homedir so GPG's agent can read it
            # regardless of sandbox restrictions (relevant on macOS GPG Suite).
            home_path = Path(homedir) if homedir else Path.home() / ".gnupg"
            tmp = tempfile.NamedTemporaryFile(
                mode="wb", prefix="gpg-keygen-", suffix=".tmp",
                dir=str(home_path), delete=False,
            )
            tmp.write(batch_content.encode())
            tmp.flush(); tmp.close()
            self._tmpfile = tmp.name
            try: Path(tmp.name).chmod(0o600)
            except: pass

            # Build GPG args
            base = [self.gpg_path]
            if homedir:
                base += ["--homedir", homedir]

            gen_flags = ["--batch", "--no-tty"]
            if self.gpg_major >= 2 and self.gpg_minor >= 1:
                gen_flags += ["--pinentry-mode", "loopback"]

            # Pre-flight: log what we're about to do
            self._log(f"  ·  GPG binary  : {self.gpg_path}", "dim")
            self._log(f"  ·  Homedir     : {homedir or '~/.gnupg (default)'}", "dim")
            self._log(f"  ·  Batch file  : {tmp.name}", "dim")
            self._log(f"  ·  Flags       : {' '.join(gen_flags)}", "dim")

            # Three-attempt generation
            success = False
            attempts = [
                ("filename", base + gen_flags + ["--gen-key", tmp.name], None),
                ("stdin",    base + gen_flags + ["--gen-key"],           batch_content.encode()),
                ("full-gen", base + gen_flags + ["--full-generate-key", tmp.name], None),
            ]

            for label, cmd, stdin_data in attempts:
                result = subprocess.run(cmd, input=stdin_data, capture_output=True)
                output = (result.stdout + result.stderr).decode(errors="replace")
                for line in output.splitlines():
                    if line.strip():
                        self._log(f"  │  {line}", "dim")
                if result.returncode == 0:
                    success = True
                    break
                self._log(f"  ⚠  Attempt '{label}' failed, trying next...", "amber")

            if not success:
                self._log("\n  ✖  All generation methods failed.", "red")
                return

            # Retrieve key info
            self._log("\n  ➜  Retrieving key info...", "dim")
            info_out = ""
            for search in [f"<{cfg['name_email']}>", cfg["name_email"]]:
                r = subprocess.run(
                    base + ["--with-colons", "--list-keys", search],
                    capture_output=True, text=True,
                )
                if r.returncode == 0 and r.stdout.strip():
                    info_out = r.stdout
                    break

            fingerprint = uid = keyid = ""
            if info_out:
                for line in info_out.splitlines():
                    parts = line.split(":")
                    if parts[0] == "pub" and not keyid:
                        keyid = parts[4] if len(parts) > 4 else ""
                    elif parts[0] == "fpr" and not fingerprint:
                        fingerprint = parts[9] if len(parts) > 9 else ""
                    elif parts[0] == "uid" and not uid:
                        uid = parts[9] if len(parts) > 9 else ""

            self._log("\n  ┌─ Key info ──────────────────────────────────", "green")
            self._log(f"  │  {'Fingerprint :':<14} {fingerprint}", "green")
            self._log(f"  │  {'UID :':<14} {uid}", "green")
            self._log(f"  │  {'Key ID :':<14} {keyid}", "green")
            self._log("  └─────────────────────────────────────────────", "green")

            # Update key info vars (must be done from main thread)
            self.after(0, lambda: self.fp_var.set(fingerprint))
            self.after(0, lambda: self.kid_var.set(keyid))
            self.after(0, lambda: self.uid_var.set(uid))

            # Export
            def safe_name(email):
                return re.sub(r"[^A-Za-z0-9._@-]", "_", email)

            if cfg["export_pub"]:
                ext  = ".asc" if cfg["armor"] else ".gpg"
                dest = Path(outdir) / f"pubkey-{safe_name(cfg['name_email'])}{ext}"
                exp_cmd = base + (["--armor"] if cfg["armor"] else []) + ["--export", cfg["name_email"]]
                r = subprocess.run(exp_cmd, capture_output=True)
                if r.returncode == 0:
                    dest.write_bytes(r.stdout)
                    try: dest.chmod(0o644)
                    except: pass
                    self._log(f"\n  ✔  Public key  → {dest}", "green")
                else:
                    self._log("  ✖  Failed to export public key.", "red")

            if cfg["export_sec"]:
                ext  = ".asc" if cfg["armor"] else ".gpg"
                dest = Path(outdir) / f"seckey-{safe_name(cfg['name_email'])}{ext}"

                sec_flags = ["--batch", "--no-tty"]
                if self.gpg_major >= 2 and self.gpg_minor >= 1:
                    sec_flags += ["--pinentry-mode", "loopback"]

                # Pass the passphrase via stdin with --passphrase-fd 0.
                # This is necessary because the gpg-agent does not cache the
                # passphrase from batch key generation, so --pinentry-mode
                # loopback alone still results in "can't get input" in batch mode.
                passphrase = cfg.get("passphrase", "")
                if passphrase:
                    sec_flags += ["--passphrase-fd", "0"]
                    stdin_data = (passphrase + "\n").encode()
                else:
                    stdin_data = None

                exp_cmd = (
                    base
                    + sec_flags
                    + (["--armor"] if cfg["armor"] else [])
                    + ["--export-secret-keys", cfg["name_email"]]
                )
                r = subprocess.run(exp_cmd, input=stdin_data, capture_output=True)
                if r.returncode == 0 and r.stdout:
                    dest.write_bytes(r.stdout)
                    try: dest.chmod(0o600)
                    except: pass
                    self._log(f"  ✔  Secret key  → {dest}", "amber")
                else:
                    detail = r.stderr.decode(errors="replace").strip()
                    self._log(f"  ✖  Failed to export secret key.", "red")
                    if detail:
                        self._log(f"     {detail}", "dim")

            self._log("\n  ✔  Done.\n", "green")

        except Exception as exc:
            self._log(f"\n  ✖  Error: {exc}", "red")
        finally:
            self.after(0, lambda: self.btn_generate.configure(
                state="normal", text="⬡  GENERATE KEY"
            ))
            self._cleanup()

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, text: str, tag: str = ""):
        self._log_queue.put((text, tag))

    def _poll_log_queue(self):
        try:
            while True:
                text, tag = self._log_queue.get_nowait()
                self.terminal.append(text, tag)
        except queue.Empty:
            pass
        self.after(50, self._poll_log_queue)

    # ── Smooth Scroll ─────────────────────────────────────────────────────────

    def _bind_smooth_scroll(self, frame: ctk.CTkScrollableFrame):
        """
        Smooth scroll — fires exactly ONCE per wheel event.

        Uses bind_all on the window so events are caught regardless of which
        child widget has focus, but the handler immediately returns if the mouse
        is not inside the scrollable panel.  This avoids the previous approach
        of binding to every child widget which caused the handler to fire N times
        per event (once per widget in the bubble chain) making scroll laggy.
        """
        canvas = frame._parent_canvas
        system = platform.system()

        self._scroll_velocity  = 0.0
        self._scroll_momentum_id = None

        def _move(delta_px: float):
            try:
                bbox = canvas.bbox("all")
                total = int(bbox[3]) if bbox else 0
                if total <= 0:
                    return
                current = canvas.yview()[0]
                new_pos = max(0.0, min(1.0, current + delta_px / total))
                canvas.yview_moveto(new_pos)
            except Exception:
                pass

        def _momentum():
            self._scroll_velocity *= 0.80
            if abs(self._scroll_velocity) < 0.4:
                self._scroll_velocity = 0.0
                self._scroll_momentum_id = None
                return
            _move(self._scroll_velocity)
            self._scroll_momentum_id = self.after(16, _momentum)

        def _mouse_over_panel() -> bool:
            """Return True only when the pointer is inside the scrollable frame."""
            try:
                px = self.winfo_pointerx() - self.winfo_rootx()
                py = self.winfo_pointery() - self.winfo_rooty()
                fx = frame.winfo_x()
                fy = frame.winfo_y()
                fw = frame.winfo_width()
                fh = frame.winfo_height()
                return fx <= px <= fx + fw and fy <= py <= fy + fh
            except Exception:
                return False

        def _on_scroll(event):
            if not _mouse_over_panel():
                return

            # Cancel running momentum so new input takes over cleanly
            if self._scroll_momentum_id:
                self.after_cancel(self._scroll_momentum_id)
                self._scroll_momentum_id = None

            if system == "Darwin":
                raw = event.delta
                if abs(raw) >= 60:
                    # Mouse wheel: each notch is ±120 on macOS
                    delta_px = (raw / 120.0) * 45
                    use_momentum = True
                else:
                    # Trackpad: OS already provides inertia, just pass through
                    delta_px = raw * 1.8
                    use_momentum = False
            elif system == "Windows":
                delta_px = (event.delta / 120.0) * 45
                use_momentum = True
            else:
                delta_px = -45 if event.num == 4 else 45
                use_momentum = False

            _move(-delta_px)

            if use_momentum:
                self._scroll_velocity = -delta_px * 0.5
                self._scroll_momentum_id = self.after(16, _momentum)

        # Single binding at the window level — fires exactly once per event
        self.bind_all("<MouseWheel>", _on_scroll)
        self.bind_all("<Button-4>",   _on_scroll)
        self.bind_all("<Button-5>",   _on_scroll)

    # ── GPG Status ────────────────────────────────────────────────────────────

    def _check_gpg_status(self):
        if self.gpg_path:
            ver = f"{self.gpg_major}.{self.gpg_minor}"
            self.status_dot.configure(
                text=f"●  gpg {ver}  ({self.gpg_path})",
                text_color=COL["green"],
            )
            self._log(f"  ✔  Found {self.gpg_path}  (v{self.gpg_major}.{self.gpg_minor})", "green")
            self._log(f"  ✔  customtkinter ready", "green")
            self._log(f"  ·  Ready — fill in the form and click GENERATE KEY\n", "dim")
        else:
            self.status_dot.configure(text="●  GPG NOT FOUND", text_color=COL["red"])
            self.btn_generate.configure(state="disabled")
            self._log("  ✖  GPG not found. Install GnuPG to continue.", "red")
            self._log("     macOS:  brew install gnupg", "dim")
            self._log("     macOS:  https://gpgtools.org", "dim")
            self._log("     Linux:  sudo apt install gnupg", "dim")

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _cleanup(self):
        if self._tmpfile and Path(self._tmpfile).exists():
            try:
                Path(self._tmpfile).unlink()
            except Exception:
                pass
            self._tmpfile = None


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = GPGKeygenApp()
    app.mainloop()
