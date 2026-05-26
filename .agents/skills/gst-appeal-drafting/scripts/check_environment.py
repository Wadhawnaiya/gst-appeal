#!/usr/bin/env python3
"""Check local GST appeal drafting plugin dependencies."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_CASELAWS_REPO = Path(os.environ.get("CASELAWS_REPO", "/home/wadhawaniya/gst-appeal/caselaws-cli"))


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 20) -> dict:
    try:
        cp = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout)
        return {"ok": cp.returncode == 0, "returncode": cp.returncode, "stdout": cp.stdout.strip(), "stderr": cp.stderr.strip(), "cmd": cmd}
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "error": f"timeout after {timeout}s", "stdout": (exc.stdout or "").strip(), "stderr": (exc.stderr or "").strip(), "cmd": cmd}


def caselaws_command() -> tuple[list[str] | None, str]:
    configured = os.environ.get("CASELAWS_CLI")
    if configured:
        return shlex.split(configured), "CASELAWS_CLI"
    found = shutil.which("caselaws-cli")
    if found:
        return [found], "PATH"
    user_wrapper = Path.home() / ".local" / "bin" / "caselaws-cli"
    if user_wrapper.exists():
        return [str(user_wrapper)], "~/.local/bin"
    repo = DEFAULT_CASELAWS_REPO
    venv_python = repo / ".venv" / "bin" / "python"
    if (repo / "cli_anything" / "caselaws" / "main.py").exists() and venv_python.exists():
        return [str(venv_python), "-m", "cli_anything.caselaws.main"], f"repo:{repo}"
    if (repo / "cli_anything" / "caselaws" / "main.py").exists():
        return ["python3", "-m", "cli_anything.caselaws.main"], f"repo:{repo}"
    return None, "missing"


def notebooklm_command() -> tuple[list[str] | None, str]:
    configured = os.environ.get("NOTEBOOKLM_CLI")
    if configured:
        return shlex.split(configured), "NOTEBOOKLM_CLI"
    found = shutil.which("notebooklm")
    if found:
        return [found], "PATH"
    user_wrapper = Path.home() / ".local" / "bin" / "notebooklm"
    if user_wrapper.exists():
        return [str(user_wrapper)], "~/.local/bin"
    bundled = DEFAULT_CASELAWS_REPO / ".venv" / "bin" / "notebooklm"
    if bundled.exists():
        return [str(bundled)], "caselaws-cli/.venv"
    return None, "missing"


def maybe_install_dependencies(only: str, json_mode: bool) -> dict:
    installer = Path(__file__).resolve().with_name("install_dependencies.py")
    if not installer.exists():
        # Skill-level symlink points to plugin scripts; fallback to parent traversal.
        for candidate in Path(__file__).resolve().parents:
            possible = candidate / "scripts" / "install_dependencies.py"
            if possible.exists():
                installer = possible
                break
    cmd = [sys.executable, str(installer), "--only", only, "--json"]
    res = run(cmd, timeout=900)
    return {"cmd": cmd, "ok": res.get("ok"), "result": parse_json(res.get("stdout", "")), "raw": res}


def parse_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return text.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--install", action="store_true", help="Automatically install missing caselaws-cli and notebooklm CLI in user space")
    parser.add_argument("--install-only", choices=["all", "caselaws", "notebooklm"], default="all", help="Installer scope when --install is used")
    args = parser.parse_args()

    install_result = None
    if args.install:
        install_result = maybe_install_dependencies(args.install_only, args.json)

    notebooklm_cmd, notebooklm_source = notebooklm_command()
    result = {
        "installer": install_result,
        "notebooklm": {
            "found": bool(notebooklm_cmd),
            "source": notebooklm_source,
            "command": notebooklm_cmd,
            "version_test": None,
            "auth_test": None,
        },
        "caselaws_cli": {
            "found": False,
            "source": None,
            "command": None,
            "help_test": None,
        },
    }

    if notebooklm_cmd:
        result["notebooklm"]["version_test"] = run([*notebooklm_cmd, "--version"], timeout=20)
        result["notebooklm"]["auth_test"] = run([*notebooklm_cmd, "auth", "check", "--test", "--json"], timeout=45)

    case_cmd, source = caselaws_command()
    result["caselaws_cli"]["source"] = source
    if case_cmd:
        result["caselaws_cli"]["found"] = True
        result["caselaws_cli"]["command"] = case_cmd
        cwd = DEFAULT_CASELAWS_REPO if source.startswith("repo:") else None
        result["caselaws_cli"]["help_test"] = run([*case_cmd, "--help"], cwd=cwd)

    ok = bool(result["caselaws_cli"]["found"] and result["caselaws_cli"]["help_test"] and result["caselaws_cli"]["help_test"].get("ok"))
    # NotebookLM may be intentionally pre-installed later; report but do not require for local script validation.
    result["overall_ok"] = ok

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("NotebookLM:", "found" if result["notebooklm"]["found"] else "missing", result["notebooklm"]["source"])
        print("caselaws-cli:", "found" if result["caselaws_cli"]["found"] else "missing", result["caselaws_cli"]["source"])
        if not ok:
            print(f"Install dependencies with: python3 {Path(__file__).resolve().with_name('install_dependencies.py')} --only all")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
