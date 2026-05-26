#!/usr/bin/env python3
"""Install GST Appeal Drafter runtime CLIs for agents.

Installs:
- caselaws-cli from https://github.com/Wadhawnaiya/caselaws-cli
- notebooklm CLI from notebooklm-py

The installer is idempotent and keeps everything in user space under
~/.local/share/gst-appeal-drafter, with wrapper commands in ~/.local/bin.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

APP_HOME = Path(os.environ.get("GST_APPEAL_DRAFTER_HOME", Path.home() / ".local" / "share" / "gst-appeal-drafter"))
SRC_HOME = APP_HOME / "src"
VENV_HOME = APP_HOME / "venvs"
BIN_HOME = Path(os.environ.get("GST_APPEAL_DRAFTER_BIN", Path.home() / ".local" / "bin"))
CASELAWS_REPO_URL = "https://github.com/Wadhawnaiya/caselaws-cli.git"
CASELAWS_SRC = SRC_HOME / "caselaws-cli"
CASELAWS_VENV = VENV_HOME / "caselaws-cli"
NOTEBOOKLM_VENV = VENV_HOME / "notebooklm-cli"


class Installer:
    def __init__(self, dry_run: bool = False, verbose: bool = False) -> None:
        self.dry_run = dry_run
        self.verbose = verbose
        self.actions: list[dict[str, Any]] = []

    def record(self, action: str, **extra: Any) -> None:
        payload = {"action": action, **extra}
        self.actions.append(payload)
        if self.verbose or self.dry_run:
            print(json.dumps(payload, indent=2))

    def run(self, cmd: list[str], *, cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str] | None:
        self.record("run", cmd=cmd, cwd=str(cwd) if cwd else None)
        if self.dry_run:
            return None
        return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, check=True, timeout=timeout)

    def ensure_dir(self, path: Path) -> None:
        self.record("ensure_dir", path=str(path))
        if not self.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    def write_text(self, path: Path, text: str) -> None:
        self.record("write", path=str(path))
        if not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            path.chmod(0o755)


def ensure_python() -> str:
    py = shutil.which("python3") or sys.executable
    if not py:
        raise RuntimeError("python3 not found")
    return py


def ensure_git() -> str:
    git = shutil.which("git")
    if not git:
        raise RuntimeError("git not found; install git before cloning caselaws-cli")
    return git


def create_venv(installer: Installer, venv: Path) -> Path:
    python3 = ensure_python()
    if not venv.exists():
        installer.run([python3, "-m", "venv", str(venv)])
    pip = venv / "bin" / "pip"
    python = venv / "bin" / "python"
    installer.run([str(python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    return python


def install_caselaws(installer: Installer, branch: str = "main") -> dict[str, Any]:
    git = ensure_git()
    installer.ensure_dir(SRC_HOME)
    if CASELAWS_SRC.exists():
        installer.run([git, "fetch", "--all", "--prune"], cwd=CASELAWS_SRC)
        installer.run([git, "checkout", branch], cwd=CASELAWS_SRC)
        installer.run([git, "pull", "--ff-only", "origin", branch], cwd=CASELAWS_SRC)
    else:
        installer.run([git, "clone", "--branch", branch, CASELAWS_REPO_URL, str(CASELAWS_SRC)])
    python = create_venv(installer, CASELAWS_VENV)
    installer.run([str(python), "-m", "pip", "install", "-e", str(CASELAWS_SRC)])
    wrapper = BIN_HOME / "caselaws-cli"
    installer.write_text(wrapper, f"#!/usr/bin/env bash\nexec {CASELAWS_VENV}/bin/caselaws-cli \"$@\"\n")
    if not installer.dry_run:
        installer.run([str(wrapper), "--help"])
    return {"name": "caselaws-cli", "source": CASELAWS_REPO_URL, "src": str(CASELAWS_SRC), "venv": str(CASELAWS_VENV), "command": str(wrapper)}


def install_notebooklm(installer: Installer, *, playwright: bool = True, cookies: bool = False, login: bool = False) -> dict[str, Any]:
    python = create_venv(installer, NOTEBOOKLM_VENV)
    installer.run([str(python), "-m", "pip", "install", "notebooklm-py[browser]>=0.5.0"])
    if cookies and sys.version_info < (3, 13):
        installer.run([str(python), "-m", "pip", "install", "notebooklm-py[cookies]>=0.5.0"])
    elif cookies:
        installer.record("skip", reason="notebooklm-py[cookies] skipped on Python 3.13+ because rookiepy may not build")
    if playwright:
        playwright_bin = NOTEBOOKLM_VENV / "bin" / "playwright"
        installer.run([str(playwright_bin), "install", "chromium"], timeout=600)
    wrapper = BIN_HOME / "notebooklm"
    installer.write_text(wrapper, f"#!/usr/bin/env bash\nexec {NOTEBOOKLM_VENV}/bin/notebooklm \"$@\"\n")
    if not installer.dry_run:
        installer.run([str(wrapper), "--version"])
        if login:
            installer.run([str(wrapper), "login"], timeout=600)
    return {"name": "notebooklm", "source": "notebooklm-py[browser]>=0.5.0", "venv": str(NOTEBOOKLM_VENV), "command": str(wrapper)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["all", "caselaws", "notebooklm"], default="all", help="Which dependency to install")
    parser.add_argument("--caselaws-branch", default="main", help="Git branch for caselaws-cli")
    parser.add_argument("--skip-playwright", action="store_true", help="Skip Chromium browser install for NotebookLM login")
    parser.add_argument("--with-cookies-extra", action="store_true", help="Also install notebooklm-py[cookies] where supported")
    parser.add_argument("--login-notebooklm", action="store_true", help="Run notebooklm login after installing; opens a browser and needs human sign-in")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing anything")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    installer = Installer(dry_run=args.dry_run, verbose=args.verbose)
    installed: list[dict[str, Any]] = []
    installer.ensure_dir(BIN_HOME)
    installer.ensure_dir(VENV_HOME)

    if args.only in {"all", "caselaws"}:
        installed.append(install_caselaws(installer, branch=args.caselaws_branch))
    if args.only in {"all", "notebooklm"}:
        installed.append(install_notebooklm(
            installer,
            playwright=not args.skip_playwright,
            cookies=args.with_cookies_extra,
            login=args.login_notebooklm,
        ))

    path_note = None
    current_path = os.environ.get("PATH", "").split(os.pathsep)
    if str(BIN_HOME) not in current_path:
        path_note = f"Add {BIN_HOME} to PATH, e.g. export PATH=\"{BIN_HOME}:$PATH\""

    summary = {
        "ok": True,
        "dry_run": args.dry_run,
        "installed": installed,
        "bin_home": str(BIN_HOME),
        "path_note": path_note,
        "next_steps": [
            "Run: notebooklm auth check --test --json",
            "If not authenticated, run: notebooklm login",
            "Set GST notebook when known: export NOTEBOOKLM_NOTEBOOK=<notebook-id>",
            "Run: caselaws-cli search \"GST input tax credit section 16\" --json --limit 3",
        ],
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("GST Appeal Drafter dependency install complete." if not args.dry_run else "GST Appeal Drafter dependency install dry-run complete.")
        for item in installed:
            print(f"- {item['name']}: {item['command']}")
        if path_note:
            print(path_note)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc.cmd} (exit {exc.returncode})", file=sys.stderr)
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
