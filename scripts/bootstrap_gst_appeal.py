#!/usr/bin/env python3
"""Bootstrap the GST appeal drafting toolkit from GitHub into the current folder.

This script is intentionally self-contained so an AI agent can run it directly
from a raw GitHub URL. It creates a local `.gst-appeal/` tool home, clones this
repository there, installs caselaws-cli and NotebookLM CLI into local virtual
environments, copies the GST drafting skill into project agent skill folders,
and writes wrapper commands under `.gst-appeal/bin`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

DEFAULT_REPO_URL = "https://github.com/Wadhawnaiya/gst-appeal.git"
DEFAULT_BRANCH = "main"
SKILL_NAME = "gst-appeal-drafting"


class InstallLayout:
    """Resolved folder-local installation paths."""

    def __init__(self, target_dir: Path, install_root: Path) -> None:
        self.target_dir = target_dir
        self.install_root = install_root
        self.repo_dir = install_root / "repo"
        self.venv_dir = install_root / "venvs"
        self.bin_dir = install_root / "bin"
        self.caselaws_venv = self.venv_dir / "caselaws-cli"
        self.notebooklm_venv = self.venv_dir / "notebooklm-cli"
        self.skill_targets = [
            target_dir / ".agents" / "skills" / SKILL_NAME,
            target_dir / ".codex" / "skills" / SKILL_NAME,
        ]

    @classmethod
    def for_target(cls, target: str | Path, install_root: str | Path | None = None) -> "InstallLayout":
        target_dir = Path(target).expanduser().resolve()
        root = Path(install_root).expanduser().resolve() if install_root else target_dir / ".gst-appeal"
        return cls(target_dir=target_dir, install_root=root)


def command_text(cmd: list[str]) -> str:
    return " ".join(cmd)


def run(cmd: list[str], *, cwd: Path | None = None, dry_run: bool = False, planned_steps: list[dict[str, Any]] | None = None, timeout: int | None = None) -> None:
    step = {"cmd": cmd, "cwd": str(cwd) if cwd else None}
    if planned_steps is not None:
        planned_steps.append(step)
    if dry_run:
        return
    quiet = os.environ.get("GST_BOOTSTRAP_QUIET_SUBPROCESS") == "1"
    subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        timeout=timeout,
        stdout=subprocess.PIPE if quiet else None,
        stderr=subprocess.PIPE if quiet else None,
        text=True,
    )


def ensure_dir(path: Path, *, dry_run: bool = False) -> None:
    if not dry_run:
        path.mkdir(parents=True, exist_ok=True)


def remove_path(path: Path, *, dry_run: bool = False) -> None:
    if dry_run or not path.exists():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def python_exe(venv: Path) -> Path:
    return venv / "Scripts" / "python.exe" if os.name == "nt" else venv / "bin" / "python"


def pip_exe(venv: Path) -> Path:
    return venv / "Scripts" / "pip.exe" if os.name == "nt" else venv / "bin" / "pip"


def bin_exe(venv: Path, name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    folder = "Scripts" if os.name == "nt" else "bin"
    return venv / folder / f"{name}{suffix}"


def download_repo_zip(repo_url: str, branch: str, destination: Path, *, dry_run: bool, planned_steps: list[dict[str, Any]]) -> None:
    """Fallback for systems without git."""
    archive_url = repo_url.rstrip("/")
    if archive_url.endswith(".git"):
        archive_url = archive_url[:-4]
    archive_url = f"{archive_url}/archive/refs/heads/{branch}.zip"
    planned_steps.append({"download_zip": archive_url, "destination": str(destination)})
    if dry_run:
        return
    ensure_dir(destination.parent)
    tmp_zip = destination.parent / "gst-appeal-bootstrap.zip"
    with urllib.request.urlopen(archive_url, timeout=120) as response:  # noqa: S310 - user-supplied URL is explicit installer input.
        tmp_zip.write_bytes(response.read())
    tmp_extract = destination.parent / "gst-appeal-bootstrap-extract"
    remove_path(tmp_extract)
    with zipfile.ZipFile(tmp_zip) as zf:
        zf.extractall(tmp_extract)
    roots = [p for p in tmp_extract.iterdir() if p.is_dir()]
    if not roots:
        raise RuntimeError(f"Archive {archive_url} did not contain a repository folder")
    remove_path(destination)
    shutil.move(str(roots[0]), str(destination))
    remove_path(tmp_extract)
    tmp_zip.unlink(missing_ok=True)


def ensure_repo(args: argparse.Namespace, layout: InstallLayout, planned_steps: list[dict[str, Any]]) -> None:
    git = shutil.which("git")
    repo_exists = (layout.repo_dir / ".git").exists()

    if repo_exists and args.update_repo:
        run([git or "git", "fetch", "origin", args.branch, "--depth", "1"], cwd=layout.repo_dir, dry_run=args.dry_run, planned_steps=planned_steps)
        run([git or "git", "checkout", args.branch], cwd=layout.repo_dir, dry_run=args.dry_run, planned_steps=planned_steps)
        run([git or "git", "reset", "--hard", "FETCH_HEAD"], cwd=layout.repo_dir, dry_run=args.dry_run, planned_steps=planned_steps)
        return
    if layout.repo_dir.exists() and not args.force and not repo_exists:
        planned_steps.append({"use_existing_repo_dir": str(layout.repo_dir)})
        return
    if layout.repo_dir.exists() and args.force:
        planned_steps.append({"remove_existing": str(layout.repo_dir)})
        remove_path(layout.repo_dir, dry_run=args.dry_run)

    ensure_dir(layout.repo_dir.parent, dry_run=args.dry_run)
    if git:
        run([git, "clone", "--depth", "1", "--branch", args.branch, args.repo_url, str(layout.repo_dir)], dry_run=args.dry_run, planned_steps=planned_steps)
    else:
        download_repo_zip(args.repo_url, args.branch, layout.repo_dir, dry_run=args.dry_run, planned_steps=planned_steps)


def create_venv(venv: Path, *, dry_run: bool, planned_steps: list[dict[str, Any]]) -> None:
    if venv.exists():
        planned_steps.append({"venv_exists": str(venv)})
        return
    run([sys.executable, "-m", "venv", str(venv)], dry_run=dry_run, planned_steps=planned_steps)


def install_caselaws(layout: InstallLayout, *, dry_run: bool, planned_steps: list[dict[str, Any]]) -> None:
    create_venv(layout.caselaws_venv, dry_run=dry_run, planned_steps=planned_steps)
    py = python_exe(layout.caselaws_venv)
    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], dry_run=dry_run, planned_steps=planned_steps)
    run([str(py), "-m", "pip", "install", "-e", str(layout.repo_dir / "caselaws-cli")], dry_run=dry_run, planned_steps=planned_steps)


def install_notebooklm(layout: InstallLayout, *, dry_run: bool, planned_steps: list[dict[str, Any]], skip_playwright: bool) -> None:
    create_venv(layout.notebooklm_venv, dry_run=dry_run, planned_steps=planned_steps)
    py = python_exe(layout.notebooklm_venv)
    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], dry_run=dry_run, planned_steps=planned_steps)
    run([str(py), "-m", "pip", "install", "notebooklm-py[browser]>=0.5.0"], dry_run=dry_run, planned_steps=planned_steps)
    if not skip_playwright:
        playwright = bin_exe(layout.notebooklm_venv, "playwright")
        run([str(playwright), "install", "chromium"], dry_run=dry_run, planned_steps=planned_steps, timeout=900)


def copy_skill(layout: InstallLayout, *, dry_run: bool) -> list[Path]:
    source = layout.repo_dir / ".agents" / "skills" / SKILL_NAME
    if not dry_run and not source.exists():
        raise RuntimeError(f"Skill source not found: {source}")
    copied: list[Path] = []
    for target in layout.skill_targets:
        copied.append(target)
        if dry_run:
            continue
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
    return copied


def write_executable(path: Path, text: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def write_text(path: Path, text: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def shell_quote_path(path: Path) -> str:
    return str(path).replace('"', '\\"')


def wrapper_prefix(layout: InstallLayout) -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        export GST_APPEAL_HOME="{shell_quote_path(layout.install_root)}"
        export GST_APPEAL_REPO="{shell_quote_path(layout.repo_dir)}"
        export CASELAWS_REPO="{shell_quote_path(layout.repo_dir / 'caselaws-cli')}"
        export CASELAWS_CLI="{shell_quote_path(python_exe(layout.caselaws_venv))} -m cli_anything.caselaws.main"
        export NOTEBOOKLM_CLI="{shell_quote_path(bin_exe(layout.notebooklm_venv, 'notebooklm'))}"
        export PATH="{shell_quote_path(layout.bin_dir)}:$PATH"
        """
    )


def write_wrappers(layout: InstallLayout, *, dry_run: bool) -> list[Path]:
    ensure_dir(layout.bin_dir, dry_run=dry_run)
    prefix = wrapper_prefix(layout)
    wrappers = {
        "caselaws-cli": f"#!/usr/bin/env bash\nexec \"{bin_exe(layout.caselaws_venv, 'caselaws-cli')}\" \"$@\"\n",
        "notebooklm": f"#!/usr/bin/env bash\nexec \"{bin_exe(layout.notebooklm_venv, 'notebooklm')}\" \"$@\"\n",
        "gst-appeal-check": prefix + f"exec \"{python_exe(layout.caselaws_venv)}\" \"{layout.repo_dir / '.agents' / 'skills' / SKILL_NAME / 'scripts' / 'check_environment.py'}\" \"$@\"\n",
        "gst-appeal-autodraft": prefix + f"exec \"{python_exe(layout.caselaws_venv)}\" \"{layout.repo_dir / '.agents' / 'skills' / SKILL_NAME / 'scripts' / 'gst_appeal_autodraft.py'}\" \"$@\"\n",
        "gst-appeal-research": prefix + f"exec \"{python_exe(layout.caselaws_venv)}\" \"{layout.repo_dir / '.agents' / 'skills' / SKILL_NAME / 'scripts' / 'gst_appeal_research.py'}\" \"$@\"\n",
    }
    written: list[Path] = []
    for name, text in wrappers.items():
        path = layout.bin_dir / name
        write_executable(path, text, dry_run=dry_run)
        written.append(path)

    env_text = textwrap.dedent(
        f"""\
        # Source this file to use the folder-local GST appeal tools.
        export GST_APPEAL_HOME="{shell_quote_path(layout.install_root)}"
        export GST_APPEAL_REPO="{shell_quote_path(layout.repo_dir)}"
        export CASELAWS_REPO="{shell_quote_path(layout.repo_dir / 'caselaws-cli')}"
        export CASELAWS_CLI="{shell_quote_path(python_exe(layout.caselaws_venv))} -m cli_anything.caselaws.main"
        export NOTEBOOKLM_CLI="{shell_quote_path(bin_exe(layout.notebooklm_venv, 'notebooklm'))}"
        export PATH="{shell_quote_path(layout.bin_dir)}:$PATH"
        """
    )
    write_text(layout.install_root / "env.sh", env_text, dry_run=dry_run)
    written.append(layout.install_root / "env.sh")
    return written


def write_usage_doc(layout: InstallLayout, *, dry_run: bool) -> Path:
    doc = layout.target_dir / "GST_APPEAL_LOCAL_INSTALL.md"
    text = f"""# GST Appeal Local Install

This folder has a local GST appeal drafting toolkit installed under:

```text
{layout.install_root}
```

## Use directly

```bash
source .gst-appeal/env.sh
caselaws-cli --help
notebooklm auth check --test --json
gst-appeal-check --json
gst-appeal-autodraft --matter-dir ./matter-folder --output-dir ./matter-folder/gst-appeal-workspace
```

## Tool paths

- Skill source copied to `.agents/skills/{SKILL_NAME}` and `.codex/skills/{SKILL_NAME}`.
- Repo checkout: `.gst-appeal/repo`
- Wrapper commands: `.gst-appeal/bin`
- caselaws-cli venv: `.gst-appeal/venvs/caselaws-cli`
- NotebookLM CLI venv: `.gst-appeal/venvs/notebooklm-cli`

## NotebookLM login

If `notebooklm auth check --test --json` says authentication is missing, run:

```bash
notebooklm login
```

Then set your GST law notebook ID:

```bash
export NOTEBOOKLM_NOTEBOOK="<your-gst-law-notebook-id>"
```
"""
    write_text(doc, text, dry_run=dry_run)
    return doc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL, help="GitHub repo URL to clone/download")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="Branch to install")
    parser.add_argument("--target", default=".", help="Folder where .gst-appeal/ and skill copies should be installed")
    parser.add_argument("--install-root", help="Override local install root; defaults to <target>/.gst-appeal")
    parser.add_argument("--force", action="store_true", help="Remove an existing non-git managed repo dir before installing")
    parser.add_argument("--no-update-repo", dest="update_repo", action="store_false", help="Do not update an existing managed repo checkout")
    parser.add_argument("--skip-notebooklm", action="store_true", help="Skip NotebookLM CLI venv installation")
    parser.add_argument("--skip-playwright", action="store_true", help="Skip Playwright Chromium install for NotebookLM browser login")
    parser.add_argument("--skip-caselaws", action="store_true", help="Skip caselaws-cli venv installation")
    parser.add_argument("--skip-skill-copy", action="store_true", help="Do not copy the skill into .agents/.codex")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing or downloading")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary")
    parser.set_defaults(update_repo=True)
    return parser.parse_args(argv)


def bootstrap(args: argparse.Namespace) -> dict[str, Any]:
    layout = InstallLayout.for_target(args.target, args.install_root)
    planned_steps: list[dict[str, Any]] = []
    old_quiet = os.environ.get("GST_BOOTSTRAP_QUIET_SUBPROCESS")
    if getattr(args, "json", False):
        os.environ["GST_BOOTSTRAP_QUIET_SUBPROCESS"] = "1"
    try:
        if not args.dry_run:
            layout.target_dir.mkdir(parents=True, exist_ok=True)
            layout.install_root.mkdir(parents=True, exist_ok=True)
            layout.venv_dir.mkdir(parents=True, exist_ok=True)
            layout.bin_dir.mkdir(parents=True, exist_ok=True)

        ensure_repo(args, layout, planned_steps)
        if not args.skip_caselaws:
            install_caselaws(layout, dry_run=args.dry_run, planned_steps=planned_steps)
        if not args.skip_notebooklm:
            install_notebooklm(layout, dry_run=args.dry_run, planned_steps=planned_steps, skip_playwright=args.skip_playwright)
        skill_targets: list[Path] = [] if args.skip_skill_copy else copy_skill(layout, dry_run=args.dry_run)
        wrappers = write_wrappers(layout, dry_run=args.dry_run)
        usage_doc = write_usage_doc(layout, dry_run=args.dry_run)
    finally:
        if getattr(args, "json", False):
            if old_quiet is None:
                os.environ.pop("GST_BOOTSTRAP_QUIET_SUBPROCESS", None)
            else:
                os.environ["GST_BOOTSTRAP_QUIET_SUBPROCESS"] = old_quiet

    return {
        "ok": True,
        "dry_run": args.dry_run,
        "repo_url": args.repo_url,
        "branch": args.branch,
        "target_dir": str(layout.target_dir),
        "install_root": str(layout.install_root),
        "repo_dir": str(layout.repo_dir),
        "bin_dir": str(layout.bin_dir),
        "caselaws_cli": str(layout.bin_dir / "caselaws-cli"),
        "notebooklm": str(layout.bin_dir / "notebooklm"),
        "gst_appeal_autodraft": str(layout.bin_dir / "gst-appeal-autodraft"),
        "skill_targets": [str(path) for path in skill_targets],
        "wrappers": [str(path) for path in wrappers],
        "usage_doc": str(usage_doc),
        "planned_steps": planned_steps,
        "next_steps": [
            "source .gst-appeal/env.sh",
            "gst-appeal-check --json",
            "notebooklm auth check --test --json",
            "gst-appeal-autodraft --matter-dir ./matter-folder --output-dir ./matter-folder/gst-appeal-workspace",
        ],
    }


def print_summary(summary: dict[str, Any], *, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(summary, indent=2))
        return
    print("GST Appeal toolkit bootstrap complete." if not summary["dry_run"] else "GST Appeal toolkit bootstrap dry-run complete.")
    print(f"Install root: {summary['install_root']}")
    print(f"Commands: {summary['bin_dir']}")
    print("Next:")
    for step in summary["next_steps"]:
        print(f"  {step}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = bootstrap(args)
    except subprocess.CalledProcessError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc), "cmd": exc.cmd, "returncode": exc.returncode}, indent=2))
        else:
            print(f"Bootstrap command failed: {command_text(list(exc.cmd))} (exit {exc.returncode})", file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:  # pragma: no cover - defensive CLI error reporting.
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"Bootstrap failed: {exc}", file=sys.stderr)
        return 1
    print_summary(summary, json_mode=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
