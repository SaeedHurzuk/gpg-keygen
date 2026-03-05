```
 ██████╗ ██████╗  ██████╗        ██╗  ██╗███████╗██╗   ██╗ ██████╗ ███████╗███╗   ██╗
██╔════╝ ██╔══██╗██╔════╝        ██║ ██╔╝██╔════╝╚██╗ ██╔╝██╔════╝ ██╔════╝████╗  ██║
██║  ███╗██████╔╝██║  ███╗       █████╔╝ █████╗   ╚████╔╝ ██║  ███╗█████╗  ██╔██╗ ██║
██║   ██║██╔═══╝ ██║   ██║       ██╔═██╗ ██╔══╝    ╚██╔╝  ██║   ██║██╔══╝  ██║╚██╗██║
╚██████╔╝██║     ╚██████╔╝       ██║  ██╗███████╗   ██║   ╚██████╔╝███████╗██║ ╚████║
 ╚═════╝ ╚═╝      ╚═════╝        ╚═╝  ╚═╝╚══════╝   ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═══╝
```

<div align="center">

**Portable batch GPG key generation — available in Bash and Python**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Shell: Bash](https://img.shields.io/badge/Shell-Bash%203.2%2B-4EAA25?style=flat-square&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows%20%7C%20BSD-lightgrey?style=flat-square)]()
[![GPG](https://img.shields.io/badge/GnuPG-1.4%2B%20%2F%202.x-0093DD?style=flat-square)]()

</div>

---

## Overview

`gpg-keygen` takes the friction out of GPG key generation. It wraps GPG's batch mode into either a polished interactive wizard or a fully scriptable CLI — whichever fits your workflow.

It comes in **two flavours** with full feature parity:

| | `gpg-keygen` | `gpg-keygen.py` |
|---|---|---|
| **Runtime** | Bash 3.2+ | Python 3.7+ |
| **Platform** | macOS · Linux · BSD | macOS · Linux · Windows · BSD |
| **Dependencies** | `gpg` / `gpg2` only | `gpg` / `gpg2` + `colorama` |
| **Dependency check** | Manual | Automatic — offers to install |
| **Windows support** | WSL / Git Bash only | Native |
| **Zero install** | ✔ one file, `chmod +x` | ✔ one file, `pip install colorama` |

Pick the Bash version if you're on macOS or Linux and want zero setup. Pick the Python version if you're on Windows or want automatic dependency management.

---

## ✨ Features

- **Interactive wizard** — guided step-by-step prompts with a clean framed UI
- **Full CLI flag support** — scriptable, CI-friendly, zero interaction required
- **Key type menu** — RSA, DSA, ECDSA, EdDSA with sensible defaults
- **Key length menu** — preset options or custom bits, with per-type validation
- **Passphrase protection** — prompted securely with confirmation; or skip with `--no-protection`
- **Public + secret key export** — ASCII-armored `.asc` or binary `.gpg`
- **Custom GPG homedir** — fully isolated keyring, nothing touches `~/.gnupg` unless you want it to
- **macOS GPG Suite compatibility** — automatically configures `allow-loopback-pinentry` so batch mode never hangs
- **Dry-run mode** — inspect the generated batch file before committing
- **Coloured output** — green `✔` on success, red `✖` on error; stripped automatically when piped
- **Automatic dependency check** *(Python)* — detects missing packages, offers to install them, writes `INSTALL_DEPENDENCIES.txt` if declined

---

## Requirements

### Bash version

| Requirement | Version |
|-------------|---------|
| Bash | 3.2 or later |
| GnuPG | 1.4+ or 2.x (`gpg` or `gpg2`) |

### Python version

| Requirement | Version |
|-------------|---------|
| Python | 3.7 or later |
| GnuPG | 1.4+ or 2.x (`gpg` or `gpg2`) |
| colorama | any (auto-installed if missing) |

### Installing GnuPG

**macOS** — [GPG Suite](https://gpgtools.org) or Homebrew:
```sh
brew install gnupg
```

**Debian / Ubuntu:**
```sh
sudo apt install gnupg
```

**Arch Linux:**
```sh
sudo pacman -S gnupg
```

**RHEL / Fedora:**
```sh
sudo dnf install gnupg2
```

**Windows** — [Gpg4win](https://www.gpg4win.org) (required for the Python version on Windows)

---

## Installation

```sh
# Clone the repo
git clone https://github.com/SaeedHurzuk/gpg-keygen.git
cd gpg-keygen
```

**Bash:**
```sh
chmod +x gpg-keygen

# Optional: install system-wide
sudo mv gpg-keygen /usr/local/bin/gpg-keygen
```

**Python:**
```sh
pip install colorama   # or let the script install it for you on first run

# Optional: install system-wide
sudo mv gpg-keygen.py /usr/local/bin/gpg-keygen.py
```

Or grab individual files directly:

```sh
# Bash
curl -fsSL https://raw.githubusercontent.com/SaeedHurzuk/gpg-keygen/refs/heads/master/gpg-keygen \
  -o gpg-keygen && chmod +x gpg-keygen

# Python
curl -fsSL https://raw.githubusercontent.com/SaeedHurzuk/gpg-keygen/refs/heads/master/gpg-keygen.py \
  -o gpg-keygen.py
```

---

## Dependency check (Python only)

The Python script checks all dependencies automatically on startup before doing anything else.

**Missing Python package — offered for automatic install:**
```
  ┌─ Dependency check ──────────────────────────
  │
  │  Missing Python packages:
  │    ✖  colorama
  │
  └─────────────────────────────────────────────

  ➜  Install 'colorama' via pip? (y/n) [y]: y
  ➜  Installing colorama ...
  ✔  colorama installed successfully.
```

**If you decline**, or if GnuPG is missing (which can't be auto-installed), the script exits cleanly and writes an `INSTALL_DEPENDENCIES.txt` file next to the script with the exact commands you need:

```
  ➜  Install instructions saved → INSTALL_DEPENDENCIES.txt
  ✖  Cannot continue. Run the install commands above, then re-run.
```

**Missing GnuPG** shows platform-specific install instructions:
```
  ┌─ Install GnuPG ──────────────────────────────
  │  macOS (Homebrew):   brew install gnupg
  │  macOS (GPG Suite):  https://gpgtools.org
  │  Ubuntu / Debian:    sudo apt install gnupg
  │  Arch Linux:         sudo pacman -S gnupg
  │  RHEL / Fedora:      sudo dnf install gnupg2
  │  Windows:            https://www.gpg4win.org
  └─────────────────────────────────────────────
```

---

## Usage

Both scripts share identical flags and behaviour. Just swap the command.

```sh
# Bash
gpg-keygen [options]

# Python
python3 gpg-keygen.py [options]
```

Running with no arguments prints help and a quick-start tip.

---

## Modes

### Interactive wizard

The guided mode walks you through every option with a structured, framed UI. Recommended for first-time use or when generating keys manually.

```sh
gpg-keygen --interactive
# or
python3 gpg-keygen.py --interactive
```

```
  ┌─ Identity ──────────────────────────────────
  │  Name-Real  : Alice Example
  │  Name-Email : alice@example.com
  │  Comment    : (optional, Enter to skip)
  ├─ Key settings ──────────────────────────────
  │
  │  Key type:
  │    1) RSA    — universal compatibility, widely supported
  │    2) DSA    — legacy signing key, no encryption subkey
  │    3) ECDSA  — elliptic curve, compact & fast
  │    4) EdDSA  — modern Ed25519 curve, recommended
  │
  │  Choice [1]: 1
  │
  │  Key length:
  │    1) 2048 — minimum acceptable
  │    2) 3072 — NIST recommended
  │    3) 4096 — strong, slightly slower  (default)
  │    4) custom
  │
  │  Choice [3]: 3
  │
  │  Expire date (0=never, Ny/Nm/Nd) [1y]: 2y
  │  GPG homedir [default: ~/.gnupg]: ./my-keyring
  ├─ Security ──────────────────────────────────
  │  Passphrase protect key? (y/n) [y]: y
  │  Enter passphrase   :
  │  Confirm passphrase :
  ├─ Export ────────────────────────────────────
  │  Export keys? (pub · both · no) [pub]: both
  │  Output directory [default: current dir]: ./keys
  └─────────────────────────────────────────────

  ➜  Generating key for Alice Example <alice@example.com> ...
  │  gpg: keybox './my-keyring/pubring.kbx' created
  │  gpg: revocation certificate stored as './my-keyring/openpgp-revocs.d/...rev'

  ┌─ Key info ──────────────────────────────────
  │  Fingerprint :  A1B2C3D4E5F6...
  │  UID :          Alice Example <alice@example.com>
  │  Key ID :       E5F6A7B8C9D0
  └─────────────────────────────────────────────
  ✔  Public key  → ./keys/pubkey-alice@example.com.asc
  ✔  Secret key  → ./keys/seckey-alice@example.com.asc

  ✔  Done.
```

### CLI / scriptable mode

Supply everything via flags. Passphrase will be asked once if connected to a terminal, or silently defaults to `--no-protection` when piped/scripted.

```sh
gpg-keygen \
  --name "Alice Example" \
  --email "alice@example.com" \
  --comment "Work key" \
  --length 4096 \
  --expire 2y \
  --export-public \
  --export-secret \
  --output-dir ~/keys \
  --homedir ~/my-keyring
```

---

## Options

All flags are identical between both versions.

### Identity

| Flag | Description |
|------|-------------|
| `-n, --name NAME` | Real name — embedded in the key UID **(required)** |
| `-e, --email EMAIL` | Email address — embedded in the key UID **(required)** |
| `-c, --comment COMMENT` | Optional comment shown in the UID as `Name (Comment) <email>` |

### Key options

| Flag | Description |
|------|-------------|
| `-t, --type TYPE` | Key algorithm: `RSA` · `DSA` · `ECDSA` · `EdDSA` (default: `RSA`) |
| `-s, --subkey-type TYPE` | Subkey algorithm (default: mirrors `--type`) |
| `-l, --length BITS` | Key size in bits (default: `4096`) |
| `--subkey-length BITS` | Subkey size (default: mirrors `--length`) |
| `-x, --expire DATE` | Expiry: `0`=never · `Ny`=years · `Nm`=months · `Nd`=days (default: `1y`) |
| `--homedir DIR` | GPG home directory — isolates the keyring from `~/.gnupg` |
| `--no-protection` | Generate key without a passphrase |

### Export

| Flag | Description |
|------|-------------|
| `--export-public` | Export the public key after generation |
| `--export-secret` | Export the secret key (implies `--export-public`) |
| `--no-armor` | Write binary `.gpg` instead of ASCII-armored `.asc` |
| `--output-dir DIR` | Destination directory — created automatically if missing |

### Misc

| Flag | Description |
|------|-------------|
| `--interactive` | Launch the guided wizard |
| `--dry-run` | Print the GPG batch file and exit — no key is generated |
| `--save-batch` | Save a redacted copy of the batch file to `--output-dir` |
| `-v, --verbose` | Show debug output |
| `-q, --quiet` | Suppress all informational output |
| `-h, --help` | Show help |

---

## Key types

| Type | Subkey | Strength | Notes |
|------|--------|----------|-------|
| **RSA** | RSA | ★★★★☆ | Best compatibility — works everywhere |
| **DSA** | ELG-E | ★★☆☆☆ | Legacy; max 3072 bits; avoid for new keys |
| **ECDSA** | ECDH | ★★★★☆ | Compact, fast; NIST curves |
| **EdDSA** | ECDH | ★★★★★ | Ed25519; modern, recommended for new keys |

> **Not sure which to pick?** Go with **RSA 4096** for maximum compatibility, or **EdDSA** if you know your toolchain supports it.

---

## Examples

The examples below use the Bash script. For Python, replace `gpg-keygen` with `python3 gpg-keygen.py` — all flags are identical.

**Quick key, no passphrase, export public key only:**
```sh
gpg-keygen -n "Bob" -e "bob@example.com" --no-protection --export-public
```

**Long-lived key in an isolated keyring, export both keys:**
```sh
gpg-keygen \
  -n "Bob" -e "bob@example.com" \
  --expire 0 \
  --homedir ./bob-keyring \
  --export-secret \
  --output-dir ./bob-keys
```

**Dry-run to inspect the batch file before generating:**
```sh
gpg-keygen -n "Bob" -e "bob@example.com" --no-protection --dry-run
```

```
  ┌─ Dry run — batch file ──────────────────────
  │  Key-Type: RSA
  │  Key-Length: 4096
  │  Key-Usage: sign,cert
  │  Subkey-Type: RSA
  │  Subkey-Usage: encrypt
  │  Subkey-Length: 4096
  │  Name-Real: Bob
  │  Name-Email: bob@example.com
  │  Expire-Date: 1y
  │  %no-protection
  │  %commit
  └─────────────────────────────────────────────
```

**CI / automation — fully silent, no passphrase:**
```sh
gpg-keygen \
  -n "Deploy Bot" -e "deploy@ci.example.com" \
  --no-protection --quiet \
  --export-public --output-dir /etc/deploy/keys
```

**EdDSA key (modern, compact):**
```sh
gpg-keygen -n "Alice" -e "alice@example.com" --type EdDSA --expire 1y --export-public
```

**Windows (Python only):**
```sh
python3 gpg-keygen.py -n "Alice" -e "alice@example.com" --interactive
```

---

## Exported file naming

| Key | Armor | Filename |
|-----|-------|----------|
| Public | `.asc` | `pubkey-alice@example.com.asc` |
| Public | `.gpg` | `pubkey-alice@example.com.gpg` |
| Secret | `.asc` | `seckey-alice@example.com.asc` |
| Secret | `.gpg` | `seckey-alice@example.com.gpg` |

Exported files are created with strict permissions:

- Public key → `644` (safe to share)
- Secret key → `600` (private — never share this file)

> On Windows, `chmod` has no effect on NTFS. Secure your keys using filesystem ACLs or store them in a secrets manager.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Fatal error — missing binary, GPG failure, bad argument value |
| `2` | Usage error — unknown flag, missing required field |

---

## macOS notes

GPG Suite ships its own `gpg-agent` which overrides `--pinentry-mode loopback` at the agent level. Both scripts automatically write `allow-loopback-pinentry` to `gpg-agent.conf` in the target homedir and reload the agent before generating, so batch passphrase injection works reliably without any manual configuration.

---

## Windows notes (Python only)

The Python version runs natively on Windows once [Gpg4win](https://www.gpg4win.org) is installed. The script automatically checks both standard Gpg4win install paths in addition to `PATH` when locating the GPG binary.

`chmod` calls for key permissions are silently skipped on Windows since NTFS does not support Unix-style file permissions. Protect exported secret keys using Windows file ACLs or store them in a dedicated secrets manager.

---

## Security notes

- The GPG batch file (containing the passphrase if one was set) is written to a `chmod 600` temp file and deleted on exit via `trap` (Bash) or `atexit` (Python), regardless of how the script terminates.
- The `--save-batch` flag saves a **redacted** copy only — the passphrase line is replaced with `[REDACTED]`.
- Secret key exports are written `chmod 600`. Treat them like passwords — never commit them to version control.
- `--no-protection` generates a key with no passphrase. Appropriate for automated/CI contexts where the key is stored in a secrets manager; not recommended for personal keys.

---

## Files in this repo

| File | Description |
|------|-------------|
| `gpg-keygen` | Bash version — macOS, Linux, BSD |
| `gpg-keygen.py` | Python version — macOS, Linux, Windows, BSD |
| `LICENSE` | MIT license |

---

## License

MIT © 2025 — see [LICENSE](LICENSE) for the full text.

---

<div align="center">
  <sub>Built with care · works on my machine and yours</sub>
</div>
