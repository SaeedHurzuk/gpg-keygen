```
 ██████╗ ██████╗  ██████╗        ██╗  ██╗███████╗██╗   ██╗ ██████╗ ███████╗███╗   ██╗
██╔════╝ ██╔══██╗██╔════╝        ██║ ██╔╝██╔════╝╚██╗ ██╔╝██╔════╝ ██╔════╝████╗  ██║
██║  ███╗██████╔╝██║  ███╗       █████╔╝ █████╗   ╚████╔╝ ██║  ███╗█████╗  ██╔██╗ ██║
██║   ██║██╔═══╝ ██║   ██║       ██╔═██╗ ██╔══╝    ╚██╔╝  ██║   ██║██╔══╝  ██║╚██╗██║
╚██████╔╝██║     ╚██████╔╝       ██║  ██╗███████╗   ██║   ╚██████╔╝███████╗██║ ╚████║
 ╚═════╝ ╚═╝      ╚═════╝        ╚═╝  ╚═╝╚══════╝   ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═══╝
```

<div align="center">

**Portable batch GPG key generation for macOS and Linux**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Shell: Bash](https://img.shields.io/badge/Shell-Bash%203.2%2B-4EAA25?style=flat-square&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20BSD-lightgrey?style=flat-square)]()
[![GPG](https://img.shields.io/badge/GnuPG-1.4%2B%20%2F%202.x-0093DD?style=flat-square)]()

</div>

---

## Overview

`gpg-keygen` is a single-file Bash utility that takes the friction out of GPG key generation. It wraps GPG's batch mode into either a polished interactive wizard or a fully scriptable CLI — whichever fits your workflow.

No dependencies beyond `bash` and `gpg`. Works out of the box on macOS (GPG Suite or Homebrew), every major Linux distribution, and BSD.

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
- **Zero install** — one file, `chmod +x`, done

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Bash | 3.2 or later |
| GnuPG | 1.4+ or 2.x (`gpg` or `gpg2`) |

**macOS** — install via [GPG Suite](https://gpgtools.org) or Homebrew:
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

---

## Installation

```sh
# Clone the repo
git clone https://github.com/SaeedHurzuk/gpg-keygen.git
cd gpg-keygen

# Make executable
chmod +x gpg-keygen

# Optional: move to somewhere on your PATH
sudo mv gpg-keygen /usr/local/bin/gpg-keygen
```

Or grab it directly:

```sh
curl -fsSL https://raw.githubusercontent.com/SaeedHurzuk/gpg-keygen/refs/heads/master/gpg-keygen \
  -o gpg-keygen && chmod +x gpg-keygen
```

---

## Usage

```
gpg-keygen [options]
```

Running with no arguments prints help and a quick-start tip.

---

## Modes

### Interactive wizard

The guided mode walks you through every option with a structured, framed UI. Recommended for first-time use or when generating keys manually.

```sh
gpg-keygen --interactive
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

Supply everything via flags. If a passphrase decision is missing, the script will ask once when connected to a terminal, or silently default to `--no-protection` when piped/scripted.

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

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Fatal error — missing binary, GPG failure, bad argument value |
| `2` | Usage error — unknown flag, missing required field |

---

## macOS notes

GPG Suite ships its own `gpg-agent` which overrides `--pinentry-mode loopback` at the agent level. `gpg-keygen` automatically writes `allow-loopback-pinentry` to `gpg-agent.conf` in the target homedir and reloads the agent before generating, so batch passphrase injection works reliably without any manual configuration.

---

## Security notes

- The GPG batch file (containing the passphrase if one was set) is written to a `chmod 600` temp file and deleted on exit via `trap`, regardless of how the script terminates.
- The `--save-batch` flag saves a **redacted** copy only — the passphrase line is replaced with `[REDACTED]`.
- Secret key exports are written `chmod 600`. Treat them like passwords — never commit them to version control.
- `--no-protection` generates a key with no passphrase. Appropriate for automated/CI contexts where the key is stored in a secrets manager; not recommended for personal keys.

---

## License

MIT © 2025 — see [LICENSE](LICENSE) for the full text.

---

<div align="center">
  <sub>Built with care · works on my machine and yours</sub>
</div>
