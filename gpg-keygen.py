#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ██████╗ ██████╗  ██████╗       ██╗  ██╗███████╗██╗   ██╗ ██████╗ ███████╗║
║   ██╔════╝ ██╔══██╗██╔════╝       ██║ ██╔╝██╔════╝╚██╗ ██╔╝██╔════╝ ██╔════╝║
║   ██║  ███╗██████╔╝██║  ███╗      █████╔╝ █████╗   ╚████╔╝ ██║  ███╗█████╗  ║
║   ██║   ██║██╔═══╝ ██║   ██║      ██╔═██╗ ██╔══╝    ╚██╔╝  ██║   ██║██╔══╝  ║
║   ╚██████╔╝██║     ╚██████╔╝      ██║  ██╗███████╗   ██║   ╚██████╔╝███████╗║
║    ╚═════╝ ╚═╝      ╚═════╝       ╚═╝  ╚═╝╚══════╝   ╚═╝    ╚═════╝ ╚══════╝║
║                                                                              ║
║   gpg-keygen — Batch GPG key generation utility                             ║
║   Compatible with macOS · Linux · Windows (via Gpg4win)                    ║
║   Requires: Python 3.7+  ·  gpg / gpg2 1.4+  ·  colorama                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

USAGE
  gpg-keygen.py --interactive
  gpg-keygen.py -n "Alice" -e "alice@example.com" --export-public --output-dir ~/keys
  gpg-keygen.py -n "Bob"   -e "bob@example.com"   -x 0 --homedir ./gpg --export-secret

EXIT CODES
  0  Success
  1  Fatal error
  2  Usage error
"""

import argparse
import atexit
import getpass
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
#  DEPENDENCY BOOTSTRAP
#
#  Checks all required dependencies before anything else runs:
#    • colorama  — Python package, installable via pip
#    • gpg / gpg2 — system binary, must be installed by the user
#
#  For pip packages: offers to install automatically.
#  For system binaries: prints platform-specific install instructions and exits.
#  If the user declines any install, writes a one-liner install reminder and
#  exits cleanly so they can come back once everything is ready.
# ══════════════════════════════════════════════════════════════════════════════

def _print_raw(msg: str) -> None:
    """Print without colour (used before colorama is available)."""
    print(msg)

def _bootstrap_check_dependencies() -> None:
    """Run all dependency checks. Must be called before any other imports."""
    missing_pip: list[str]    = []
    missing_system: list[str] = []

    # ── Check Python packages ───────────────────────────────────────────────
    PIP_PACKAGES = ["colorama"]
    for pkg in PIP_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing_pip.append(pkg)

    # ── Check system binaries ───────────────────────────────────────────────
    gpg_found = shutil.which("gpg2") or shutil.which("gpg")
    if not gpg_found:
        # On Windows also check Gpg4win default path
        if platform.system() == "Windows":
            gpg4win = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            for candidate in [
                gpg4win / "GnuPG"   / "bin" / "gpg.exe",
                gpg4win / "Gpg4win" / "bin" / "gpg.exe",
            ]:
                if candidate.is_file():
                    gpg_found = str(candidate)
                    break
        if not gpg_found:
            missing_system.append("gpg")

    # ── All good ─────────────────────────────────────────────────────────────
    if not missing_pip and not missing_system:
        return

    # ── Report what's missing ────────────────────────────────────────────────
    _print_raw("")
    _print_raw("  ┌─ Dependency check ──────────────────────────")
    _print_raw("  │")
    if missing_pip:
        _print_raw(f"  │  Missing Python packages:")
        for p in missing_pip:
            _print_raw(f"  │    ✖  {p}")
    if missing_system:
        _print_raw(f"  │  Missing system tools:")
        for t in missing_system:
            _print_raw(f"  │    ✖  {t}")
    _print_raw("  │")
    _print_raw("  └─────────────────────────────────────────────")
    _print_raw("")

    # ── Offer to install pip packages ────────────────────────────────────────
    if missing_pip:
        declined: list[str] = []
        for pkg in missing_pip:
            while True:
                try:
                    answer = input(f"  ➜  Install '{pkg}' via pip? (y/n) [y]: ").strip().lower() or "y"
                except EOFError:
                    answer = "n"
                if answer in ("y", "yes"):
                    _print_raw(f"  ➜  Installing {pkg} ...")
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", pkg],
                        capture_output=True, text=True,
                    )
                    if result.returncode == 0:
                        _print_raw(f"  ✔  {pkg} installed successfully.")
                    else:
                        _print_raw(f"  ✖  Failed to install {pkg}:")
                        _print_raw(f"     {result.stderr.strip()}")
                        _print_raw(f"     Try manually:  pip install {pkg}")
                        declined.append(pkg)
                    break
                elif answer in ("n", "no"):
                    declined.append(pkg)
                    break
                else:
                    _print_raw("  Please answer y or n.")

        if declined:
            _write_install_reminder(declined, missing_system)
            _print_raw("")
            _print_raw("  ✖  Cannot continue without required packages.")
            _print_raw("     Run the install commands above, then re-run this script.")
            _print_raw("")
            sys.exit(1)

    # ── Handle missing system binaries ───────────────────────────────────────
    if missing_system:
        _print_raw("  ✖  The following system tools must be installed manually:")
        _print_raw("")
        for tool in missing_system:
            if tool == "gpg":
                _print_raw("  ┌─ Install GnuPG ──────────────────────────────")
                _print_raw("  │")
                _print_raw("  │  macOS (Homebrew):   brew install gnupg")
                _print_raw("  │  macOS (GPG Suite):  https://gpgtools.org")
                _print_raw("  │  Ubuntu / Debian:    sudo apt install gnupg")
                _print_raw("  │  Arch Linux:         sudo pacman -S gnupg")
                _print_raw("  │  RHEL / Fedora:      sudo dnf install gnupg2")
                _print_raw("  │  Windows:            https://www.gpg4win.org")
                _print_raw("  │")
                _print_raw("  └─────────────────────────────────────────────")
        _print_raw("")
        _write_install_reminder([], missing_system)
        _print_raw("  ✖  Cannot continue without GnuPG. Install it and re-run.")
        _print_raw("")
        sys.exit(1)


def _write_install_reminder(
    pip_packages: list[str], system_tools: list[str]
) -> None:
    """Write INSTALL_DEPENDENCIES.txt next to the script so the user has a reminder."""
    script_dir = Path(sys.argv[0]).resolve().parent
    reminder   = script_dir / "INSTALL_DEPENDENCIES.txt"
    lines = [
        "gpg-keygen — Missing dependencies",
        "=" * 50,
        "",
    ]
    if pip_packages:
        lines += [
            "Python packages (install with pip):",
            *[f"  pip install {p}" for p in pip_packages],
            "",
        ]
    if system_tools:
        lines += ["System tools:", ""]
        for tool in system_tools:
            if tool == "gpg":
                lines += [
                    "  GnuPG (gpg / gpg2):",
                    "    macOS (Homebrew):   brew install gnupg",
                    "    macOS (GPG Suite):  https://gpgtools.org",
                    "    Ubuntu / Debian:    sudo apt install gnupg",
                    "    Arch Linux:         sudo pacman -S gnupg",
                    "    RHEL / Fedora:      sudo dnf install gnupg2",
                    "    Windows:            https://www.gpg4win.org",
                    "",
                ]
    lines += ["Once installed, delete this file and re-run gpg-keygen.py."]
    try:
        reminder.write_text("\n".join(lines))
        _print_raw(f"  ➜  Install instructions saved → {reminder}")
    except OSError:
        pass  # Non-fatal — just a convenience file


# Run checks immediately, before any other code executes.
_bootstrap_check_dependencies()


# ══════════════════════════════════════════════════════════════════════════════
#  COLORAMA SETUP  (safe to import now — bootstrap ensured it's present)
#  strip=True on non-TTY outputs so ANSI codes never appear in pipes/logs.
# ══════════════════════════════════════════════════════════════════════════════
from colorama import Fore, Style, init as colorama_init  # noqa: E402
colorama_init(autoreset=False, strip=not sys.stdout.isatty())
GRN  = Fore.GREEN
RED  = Fore.RED
CYN  = Fore.CYAN
DIM  = Style.DIM
BLD  = Style.BRIGHT
RST  = Style.RESET_ALL

PROGNAME = Path(sys.argv[0]).name

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def err(msg: str) -> None:
    print(f"  {RED}✖{RST}  {msg}", file=sys.stderr)

def die(msg: str, code: int = 1) -> None:
    err(msg)
    sys.exit(code)

def info(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(f"  ➜  {msg}")

def ok(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(f"  {GRN}✔{RST}  {msg}")

def debug(msg: str, verbose: bool = False) -> None:
    if verbose:
        print(f"  ·  [debug] {msg}", file=sys.stderr)

def prompt(label: str, default: str = "") -> str:
    """Prompt the user, returning default on empty input."""
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  │  {label}{suffix}: ").strip()
        return val if val else default
    except EOFError:
        return default

def prompt_secret(label: str) -> str:
    """Prompt for a secret (no echo)."""
    try:
        return getpass.getpass(f"  │  {label}: ")
    except EOFError:
        return ""

def section(title: str) -> None:
    print(f"  ├─ {title} {'─' * (44 - len(title))}")

def section_top(title: str = "") -> None:
    if title:
        print(f"  ┌─ {title} {'─' * (44 - len(title))}")
    else:
        print(f"  ┌─────────────────────────────────────────────")

def section_end() -> None:
    print(f"  └─────────────────────────────────────────────\n")

def row(label: str) -> None:
    print(f"  │  {label}")

def chmod_safe(path: Path, mode: int) -> None:
    """Apply chmod — silently skipped on Windows where it has no effect."""
    try:
        path.chmod(mode)
    except (OSError, NotImplementedError):
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  ARGUMENT PARSING
# ══════════════════════════════════════════════════════════════════════════════
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=PROGNAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"""
  {BLD}gpg-keygen{RST} — Batch GPG key generation utility

  {BLD}IDENTITY{RST}
    -n / --name      Real name       (required)
    -e / --email     Email address   (required)
    -c / --comment   Optional UID comment

  {BLD}KEY OPTIONS{RST}
    -t / --type      RSA | DSA | ECDSA | EdDSA   (default: RSA)
    -l / --length    Key size in bits             (default: 4096)
    -x / --expire    0=never · Ny · Nm · Nd       (default: 1y)
         --homedir   Custom GPG home directory
         --no-protection  No passphrase

  {BLD}EXPORT{RST}
         --export-public   Export public key after generation
         --export-secret   Export secret key (implies --export-public)
         --no-armor        Binary .gpg instead of ASCII-armored .asc
         --output-dir DIR  Destination directory

  {BLD}MISC{RST}
         --save-batch      Save redacted batch file to --output-dir
         --interactive     Guided wizard
         --dry-run         Print batch file and exit
    -v / --verbose         Debug output
    -q / --quiet           Suppress informational output
        """,
        add_help=True,
    )

    g_id = p.add_argument_group("Identity")
    g_id.add_argument("-n", "--name",    dest="name_real",    default="", metavar="NAME")
    g_id.add_argument("-e", "--email",   dest="name_email",   default="", metavar="EMAIL")
    g_id.add_argument("-c", "--comment", dest="name_comment", default="", metavar="COMMENT")

    g_key = p.add_argument_group("Key options")
    g_key.add_argument("-t", "--type",          dest="key_type",      default="RSA",  metavar="TYPE")
    g_key.add_argument("-s", "--subkey-type",   dest="subkey_type",   default="",     metavar="TYPE")
    g_key.add_argument("-l", "--length",        dest="key_length",    default="4096", metavar="BITS")
    g_key.add_argument("--subkey-length",       dest="subkey_length", default="",     metavar="BITS")
    g_key.add_argument("-x", "--expire",        dest="expire_date",   default="1y",   metavar="DATE")
    g_key.add_argument("--homedir",             dest="gpg_homedir",   default="",     metavar="DIR")
    g_key.add_argument("--no-protection",       dest="no_protection", action="store_true")

    g_exp = p.add_argument_group("Export")
    g_exp.add_argument("--export-public", dest="export_pub", action="store_true")
    g_exp.add_argument("--export-secret", dest="export_sec", action="store_true")
    g_exp.add_argument("--no-armor",      dest="armor",      action="store_false", default=True)
    g_exp.add_argument("--output-dir",    dest="output_dir", default="", metavar="DIR")

    g_misc = p.add_argument_group("Misc")
    g_misc.add_argument("--save-batch",   dest="save_batch",   action="store_true")
    g_misc.add_argument("--interactive",  dest="interactive",  action="store_true")
    g_misc.add_argument("--dry-run",      dest="dry_run",      action="store_true")
    g_misc.add_argument("-v", "--verbose", dest="verbose",     action="store_true")
    g_misc.add_argument("-q", "--quiet",   dest="quiet",       action="store_true")

    return p

# ══════════════════════════════════════════════════════════════════════════════
#  LOCATE GPG BINARY
#  Prefer gpg2 → gpg. On Windows also check common Gpg4win install paths.
# ══════════════════════════════════════════════════════════════════════════════
def find_gpg() -> str:
    candidates = ["gpg2", "gpg"]
    if platform.system() == "Windows":
        gpg4win = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        candidates += [
            str(gpg4win / "GnuPG" / "bin" / "gpg.exe"),
            str(gpg4win / "Gpg4win" / "bin" / "gpg.exe"),
        ]
    for c in candidates:
        path = shutil.which(c) or (c if os.path.isfile(c) else None)
        if path:
            return path
    die("gpg / gpg2 not found. Install GnuPG (https://gnupg.org) and try again.")

def gpg_version(gpg: str) -> tuple[int, int]:
    """Return (major, minor) version tuple."""
    try:
        out = subprocess.run(
            [gpg, "--version"], capture_output=True, text=True
        ).stdout.splitlines()[0]
        ver = out.split()[-1]          # e.g. "2.4.3"
        parts = ver.split(".")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return 2, 0

# ══════════════════════════════════════════════════════════════════════════════
#  INTERACTIVE WIZARD
# ══════════════════════════════════════════════════════════════════════════════
def run_wizard(args: argparse.Namespace) -> str:
    """Fill in missing fields interactively. Returns passphrase (may be empty)."""
    passphrase = ""

    print()
    section_top("Identity")
    if not args.name_real:
        args.name_real = prompt("Name-Real")
    if not args.name_email:
        args.name_email = prompt("Name-Email")
    if not args.name_comment:
        args.name_comment = prompt("Comment (optional, Enter to skip)")

    section("Key settings")

    # ── Key type ──────────────────────────────────────────────────
    row("")
    row("Key type:")
    row("  1) RSA    — universal compatibility, widely supported")
    row("  2) DSA    — legacy signing key, no encryption subkey")
    row("  3) ECDSA  — elliptic curve, compact & fast")
    row("  4) EdDSA  — modern Ed25519 curve, recommended")
    row("")

    KEY_TYPE_MAP = {
        "1": ("RSA",   "RSA"),
        "rsa": ("RSA", "RSA"),
        "2": ("DSA",   "ELG-E"),
        "dsa": ("DSA", "ELG-E"),
        "3": ("ECDSA", "ECDH"),
        "ecdsa": ("ECDSA", "ECDH"),
        "4": ("EdDSA", "ECDH"),
        "eddsa": ("EdDSA", "ECDH"),
    }
    while True:
        choice = prompt("Choice", default="1").lower()
        if choice in KEY_TYPE_MAP:
            args.key_type, args.subkey_type = KEY_TYPE_MAP[choice]
            break
        row(f"  {RED}✖{RST}  Please enter 1–4.")
    row("")

    # ── Key length ────────────────────────────────────────────────
    is_ecc = args.key_type in ("ECDSA", "EdDSA")
    if is_ecc:
        row(f"Key length: (curve-based — not configurable for {args.key_type})")
        args.key_length = "0"
    elif args.key_type == "RSA":
        row("Key length:")
        row("  1) 2048 — minimum acceptable")
        row("  2) 3072 — NIST recommended")
        row("  3) 4096 — strong, slightly slower  (default)")
        row("  4) custom")
        row("")
        RSA_LEN = {"1": "2048", "2": "3072", "3": "4096"}
        while True:
            choice = prompt("Choice", default="3")
            if choice in RSA_LEN:
                args.key_length = RSA_LEN[choice]
                break
            elif choice == "4":
                while True:
                    val = prompt("Enter bits (1024–8192)")
                    if val.isdigit() and 1024 <= int(val) <= 8192:
                        args.key_length = val
                        break
                    row(f"  {RED}✖{RST}  Must be a number between 1024 and 8192.")
                break
            else:
                row(f"  {RED}✖{RST}  Please enter 1–4.")
    else:
        # DSA
        row("Key length:")
        row("  1) 1024 — legacy")
        row("  2) 2048 — standard")
        row("  3) 3072 — maximum for DSA  (default)")
        row("  4) custom")
        row("")
        DSA_LEN = {"1": "1024", "2": "2048", "3": "3072"}
        while True:
            choice = prompt("Choice", default="3")
            if choice in DSA_LEN:
                args.key_length = DSA_LEN[choice]
                break
            elif choice == "4":
                while True:
                    val = prompt("Enter bits (1024–3072)")
                    if val.isdigit() and 1024 <= int(val) <= 3072:
                        args.key_length = val
                        break
                    row(f"  {RED}✖{RST}  Must be a number between 1024 and 3072.")
                break
            else:
                row(f"  {RED}✖{RST}  Please enter 1–4.")

    args.subkey_length = args.key_length
    row("")

    val = prompt(f"Expire date (0=never, Ny/Nm/Nd)", default=args.expire_date)
    if val:
        args.expire_date = val

    val = prompt("GPG homedir", default="~/.gnupg")
    if val and val != "~/.gnupg":
        args.gpg_homedir = val

    # ── Security ──────────────────────────────────────────────────
    section("Security")
    while True:
        yn = prompt("Passphrase protect key? (y/n)", default="y").lower()
        if yn in ("y", "yes"):
            while True:
                p1 = prompt_secret("Enter passphrase")
                p2 = prompt_secret("Confirm passphrase")
                if p1 != p2:
                    row(f"  {RED}✖{RST}  Passphrases do not match. Try again.")
                elif not p1:
                    row(f"  {RED}✖{RST}  Empty passphrase not allowed. Answer n to skip.")
                else:
                    passphrase = p1
                    break
            break
        elif yn in ("n", "no"):
            args.no_protection = True
            info("Key will be generated without a passphrase.", quiet=args.quiet)
            break
        else:
            row("  Please answer y or n.")

    # ── Export ────────────────────────────────────────────────────
    section("Export")
    while True:
        choice = prompt("Export keys? (pub · both · no)", default="pub").lower()
        if choice in ("pub", "public"):
            args.export_pub = True
            break
        elif choice in ("both", "secret"):
            args.export_pub = True
            args.export_sec = True
            break
        elif choice in ("no", "none", "n"):
            break
        else:
            row("  Please answer pub, both, or no.")

    if args.export_pub or args.export_sec:
        val = prompt("Output directory", default="current directory")
        if val and val != "current directory":
            args.output_dir = val

    section_end()
    return passphrase

# ══════════════════════════════════════════════════════════════════════════════
#  VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
EXPIRE_RE = re.compile(r"^(0|[0-9]+[yYmMdD]?|[0-9]{4}-[0-9]{2}-[0-9]{2})$")

def validate(args: argparse.Namespace) -> None:
    if not args.name_real:
        die("Name-Real is required  (-n / --name).", 2)
    if not args.name_email:
        die("Name-Email is required (-e / --email).", 2)
    is_ecc = args.key_type in ("ECDSA", "EdDSA")
    if not is_ecc and not args.key_length.isdigit():
        die("Key length must be a positive integer.", 2)
    if not EXPIRE_RE.match(args.expire_date):
        die(f"Invalid expire date '{args.expire_date}'. Use: 0 · Ny · Nm · Nd · YYYY-MM-DD.", 2)

# ══════════════════════════════════════════════════════════════════════════════
#  GPG AGENT CONFIG  (macOS / GPG Suite compatibility)
# ══════════════════════════════════════════════════════════════════════════════
def configure_agent(gpg: str, gpg_major: int, gpg_minor: int,
                    gpg_homedir: str, verbose: bool) -> None:
    if not (gpg_major >= 2 and gpg_minor >= 1):
        return
    home = Path(gpg_homedir) if gpg_homedir else Path.home() / ".gnupg"
    home.mkdir(parents=True, exist_ok=True)
    conf = home / "gpg-agent.conf"
    try:
        if conf.exists():
            if "allow-loopback-pinentry" not in conf.read_text():
                conf.write_text(conf.read_text() + "\nallow-loopback-pinentry\n")
        else:
            conf.write_text("allow-loopback-pinentry\n")
            chmod_safe(conf, 0o600)
        debug(f"allow-loopback-pinentry ensured in {conf}", verbose)
    except OSError as exc:
        debug(f"Could not write gpg-agent.conf: {exc}", verbose)

    # Reload the agent
    reload_cmd = ["gpgconf", "--reload", "gpg-agent"]
    if gpg_homedir:
        reload_cmd = ["gpgconf", "--homedir", gpg_homedir, "--reload", "gpg-agent"]
    try:
        subprocess.run(reload_cmd, capture_output=True)
    except FileNotFoundError:
        pass  # gpgconf not available on all platforms

# ══════════════════════════════════════════════════════════════════════════════
#  BUILD BATCH FILE CONTENT
# ══════════════════════════════════════════════════════════════════════════════
def build_batch(args: argparse.Namespace, passphrase: str,
                gpg_major: int) -> str:
    is_ecc = args.key_type in ("ECDSA", "EdDSA")
    is_ecdh_subkey = args.subkey_type == "ECDH"

    lines = [f"Key-Type: {args.key_type}"]
    if not is_ecc:
        lines.append(f"Key-Length: {args.key_length}")
    lines.append("Key-Usage: sign,cert")
    lines.append(f"Subkey-Type: {args.subkey_type}")
    lines.append("Subkey-Usage: encrypt")
    if not is_ecdh_subkey and args.subkey_length not in ("", "0"):
        lines.append(f"Subkey-Length: {args.subkey_length}")
    lines.append(f"Name-Real: {args.name_real}")
    if args.name_comment:
        lines.append(f"Name-Comment: {args.name_comment}")
    lines.append(f"Name-Email: {args.name_email}")
    lines.append(f"Expire-Date: {args.expire_date}")
    if args.no_protection:
        if gpg_major >= 2:
            lines.append("%no-protection")
    elif passphrase:
        lines.append(f"Passphrase: {passphrase}")
    lines.append("%commit")
    return "\n".join(lines) + "\n"

# ══════════════════════════════════════════════════════════════════════════════
#  KEY GENERATION
#  Three attempts — same strategy as the bash version.
# ══════════════════════════════════════════════════════════════════════════════
def run_gpg(cmd: list[str], stdin_data: bytes | None = None) -> tuple[bool, str]:
    """Run a GPG command, return (success, combined_output)."""
    try:
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
        )
        output = (result.stdout + result.stderr).decode(errors="replace")
        return result.returncode == 0, output
    except FileNotFoundError as exc:
        return False, str(exc)

def generate_key(gpg: str, gpg_major: int, gpg_minor: int,
                 homedir: str, batch_path: str,
                 batch_bytes: bytes, verbose: bool) -> bool:
    base_args = [gpg] + (["--homedir", homedir] if homedir else [])
    use_loopback = gpg_major >= 2 and gpg_minor >= 1

    gen_flags = ["--batch", "--no-tty"]
    if use_loopback:
        gen_flags += ["--pinentry-mode", "loopback"]

    attempts = [
        ("filename arg", base_args + gen_flags + ["--gen-key", batch_path], None),
        ("stdin",        base_args + gen_flags + ["--gen-key"],             batch_bytes),
        ("--full-gen",   base_args + gen_flags + ["--full-generate-key", batch_path], None),
    ]

    for label, cmd, stdin in attempts:
        debug(f"Attempt → {label}", verbose)
        success, output = run_gpg(cmd, stdin)
        for line in output.splitlines():
            print(f"  │  {line}")
        if success:
            return True
        err(f"Attempt '{label}' failed — trying next method...")

    return False

# ══════════════════════════════════════════════════════════════════════════════
#  KEY INFO DISPLAY
# ══════════════════════════════════════════════════════════════════════════════
def show_key_info(gpg: str, homedir: str, email: str) -> None:
    base = [gpg] + (["--homedir", homedir] if homedir else [])
    output = ""
    for search in [f"<{email}>", email]:
        result = subprocess.run(
            base + ["--with-colons", "--list-keys", search],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout
            break

    if not output:
        err(f"Could not retrieve key info for <{email}> (generation may still have succeeded).")
        return

    fingerprint = uid = keyid = ""
    for line in output.splitlines():
        parts = line.split(":")
        if parts[0] == "pub" and not keyid:
            keyid = parts[4] if len(parts) > 4 else ""
        elif parts[0] == "fpr" and not fingerprint:
            fingerprint = parts[9] if len(parts) > 9 else ""
        elif parts[0] == "uid" and not uid:
            uid = parts[9] if len(parts) > 9 else ""

    print(f"  ┌─ Key info ──────────────────────────────────")
    if fingerprint:
        print(f"  │  {'Fingerprint :':<14} {fingerprint}")
    if uid:
        print(f"  │  {'UID :':<14} {uid}")
    if keyid:
        print(f"  │  {'Key ID :':<14} {keyid}")
    print(f"  └─────────────────────────────────────────────")

# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT KEYS
# ══════════════════════════════════════════════════════════════════════════════
def safe_filename(email: str) -> str:
    return re.sub(r"[^A-Za-z0-9._@-]", "_", email)

def export_key(gpg: str, homedir: str, email: str,
               secret: bool, armor: bool, output_dir: str,
               quiet: bool) -> None:
    base = [gpg] + (["--homedir", homedir] if homedir else [])
    safe = safe_filename(email)
    kind = "seckey" if secret else "pubkey"
    ext  = ".asc" if armor else ".gpg"
    filename = f"{kind}-{safe}{ext}"
    dest = Path(output_dir or ".") / filename

    cmd = base + (["--armor"] if armor else [])
    cmd += ["--export-secret-keys" if secret else "--export", email]

    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        dest.write_bytes(result.stdout)
        chmod_safe(dest, 0o600 if secret else 0o644)
        ok(f"{'Secret' if secret else 'Public'} key  → {dest}", quiet)
    except Exception as exc:
        err(f"Failed to export {'secret' if secret else 'public'} key: {exc}")

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    parser = build_parser()

    # Show help + tip when called with no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        print(f"\n  Tip: run with --interactive to be guided through all options.\n")
        sys.exit(0)

    args = parser.parse_args()

    # ── Locate GPG ──────────────────────────────────────────────────────────
    gpg = find_gpg()
    gpg_major, gpg_minor = gpg_version(gpg)
    debug(f"Binary: {gpg}  version: {gpg_major}.{gpg_minor}", args.verbose)

    # ── Interactive wizard ───────────────────────────────────────────────────
    passphrase = ""
    if args.interactive:
        passphrase = run_wizard(args)

    # ── Validation ───────────────────────────────────────────────────────────
    validate(args)

    # Mirror subkey length if not set
    if not args.subkey_length:
        args.subkey_length = args.key_length
    # Default subkey type based on key type
    if not args.subkey_type:
        args.subkey_type = {
            "RSA":   "RSA",
            "DSA":   "ELG-E",
            "ECDSA": "ECDH",
            "EdDSA": "ECDH",
        }.get(args.key_type, "RSA")
    # Handle export_sec implying export_pub
    if args.export_sec:
        args.export_pub = True

    # ── Directories ──────────────────────────────────────────────────────────
    if args.gpg_homedir:
        homedir = str(Path(args.gpg_homedir).expanduser())
        Path(homedir).mkdir(parents=True, exist_ok=True)
        chmod_safe(Path(homedir), 0o700)
        debug(f"GPG homedir: {homedir}", args.verbose)
    else:
        homedir = ""

    if args.output_dir:
        outdir = str(Path(args.output_dir).expanduser())
        Path(outdir).mkdir(parents=True, exist_ok=True)
        chmod_safe(Path(outdir), 0o700)
    else:
        outdir = ""

    # ── Non-interactive passphrase prompt ────────────────────────────────────
    if not args.interactive and not args.no_protection and not passphrase:
        if sys.stdin.isatty() and sys.stdout.isatty():
            while True:
                yn = input("  Passphrase protect key? (y/n) [y]: ").strip().lower() or "y"
                if yn in ("y", "yes"):
                    while True:
                        p1 = getpass.getpass("  Enter passphrase   : ")
                        p2 = getpass.getpass("  Confirm passphrase : ")
                        if p1 != p2:
                            err("Passphrases do not match. Try again.")
                        elif not p1:
                            err("Empty passphrase not allowed. Answer n to skip.")
                        else:
                            passphrase = p1
                            break
                    break
                elif yn in ("n", "no"):
                    args.no_protection = True
                    break
                else:
                    print("  Please answer y or n.")
        else:
            # No TTY — default to no passphrase to avoid hanging
            args.no_protection = True
            debug("No TTY detected; defaulting to %no-protection.", args.verbose)

    # ── Build batch content ──────────────────────────────────────────────────
    batch_content = build_batch(args, passphrase, gpg_major)
    batch_bytes   = batch_content.encode()

    # ── Temp file (auto-deleted on exit) ─────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(
        mode="wb", prefix="gpg-keygen-", suffix=".tmp",
        delete=False,
    )
    tmp.write(batch_bytes)
    tmp.flush()
    tmp.close()
    chmod_safe(Path(tmp.name), 0o600)
    atexit.register(lambda: Path(tmp.name).unlink(missing_ok=True))

    debug(f"Batch file written → {tmp.name}", args.verbose)

    # ── Dry run ──────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n  ┌─ Dry run — batch file ──────────────────────")
        for line in batch_content.splitlines():
            display = "[REDACTED]" if line.startswith("Passphrase:") else line
            print(f"  │  {display}")
        print("  └─────────────────────────────────────────────\n")
        sys.exit(0)

    # ── Save batch file ───────────────────────────────────────────────────────
    if args.save_batch and outdir:
        batch_out = Path(outdir) / "gpg-keygen-batch.txt"
        redacted = re.sub(r"(?m)^Passphrase: .*$", "Passphrase: [REDACTED]", batch_content)
        batch_out.write_text(redacted)
        chmod_safe(batch_out, 0o600)
        ok(f"Batch file saved → {batch_out}", args.quiet)

    # ── GPG agent config ──────────────────────────────────────────────────────
    configure_agent(gpg, gpg_major, gpg_minor, homedir, args.verbose)

    # ── Generate key ──────────────────────────────────────────────────────────
    info(f"Generating key for {args.name_real} <{args.name_email}> ...", args.quiet)

    success = generate_key(
        gpg, gpg_major, gpg_minor,
        homedir, tmp.name, batch_bytes, args.verbose,
    )
    if not success:
        die("All generation methods failed. See errors above.")

    # ── Key info ──────────────────────────────────────────────────────────────
    print()
    show_key_info(gpg, homedir, args.name_email)

    # ── Export ────────────────────────────────────────────────────────────────
    if args.export_pub:
        export_key(gpg, homedir, args.name_email,
                   secret=False, armor=args.armor,
                   output_dir=outdir, quiet=args.quiet)
    if args.export_sec:
        export_key(gpg, homedir, args.name_email,
                   secret=True,  armor=args.armor,
                   output_dir=outdir, quiet=args.quiet)

    print()
    ok("Done.", args.quiet)
    print()


if __name__ == "__main__":
    main()