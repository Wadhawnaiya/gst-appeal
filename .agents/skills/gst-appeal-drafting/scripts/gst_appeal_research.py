#!/usr/bin/env python3
"""Build a GST appeal research packet from NotebookLM and caselaws-cli."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_CASELAWS_REPO = Path(os.environ.get("CASELAWS_REPO", "/home/wadhawaniya/gst-appeal/caselaws-cli"))


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        cp = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=run_env,
        )
        payload: dict[str, Any] = {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "returncode": cp.returncode,
            "ok": cp.returncode == 0,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
        }
        return payload
    except FileNotFoundError as exc:
        return {"cmd": cmd, "cwd": str(cwd) if cwd else None, "ok": False, "returncode": 127, "error": str(exc), "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "ok": False,
            "returncode": 124,
            "error": f"timeout after {timeout}s",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def parse_jsonish(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return text.strip()


def caselaws_command() -> tuple[list[str] | None, Path | None]:
    configured = os.environ.get("CASELAWS_CLI")
    if configured:
        return shlex.split(configured), None
    # Prefer the bundled/workspace repo so newly edited integration commands are used
    # before any older wrapper installed in ~/.local/bin or PATH.
    repo = DEFAULT_CASELAWS_REPO
    if (repo / "cli_anything" / "caselaws" / "main.py").exists():
        py = repo / ".venv" / "bin" / "python"
        if py.exists():
            return [str(py), "-m", "cli_anything.caselaws.main"], repo
        return ["python3", "-m", "cli_anything.caselaws.main"], repo
    found = shutil.which("caselaws-cli")
    if found:
        return [found], None
    return None, None


def notebooklm_command() -> tuple[list[str] | None, str]:
    """Resolve NotebookLM CLI from explicit env, PATH, bundled caselaws venv, or user wrapper."""
    configured = os.environ.get("NOTEBOOKLM_CLI")
    if configured:
        return shlex.split(configured), "NOTEBOOKLM_CLI"
    found = shutil.which("notebooklm")
    if found:
        return [found], "PATH"
    bundled = DEFAULT_CASELAWS_REPO / ".venv" / "bin" / "notebooklm"
    if bundled.exists():
        return [str(bundled)], "caselaws-cli/.venv"
    user_wrapper = Path.home() / ".local" / "bin" / "notebooklm"
    if user_wrapper.exists():
        return [str(user_wrapper)], "~/.local/bin"
    return None, "missing"


def build_notebooklm_ask_command(
    notebooklm: str | list[str],
    notebook: str | None,
    prompt_file: Path,
    timeout: int,
) -> list[str]:
    base = shlex.split(notebooklm) if isinstance(notebooklm, str) else list(notebooklm)
    cmd = [*base, "ask", "--json", "--timeout", str(timeout)]
    if notebook:
        cmd.extend(["--notebook", notebook])
    cmd.extend(["--prompt-file", str(prompt_file)])
    return cmd


def notebooklm_provider_search(prompt: str, notebook: str | None, timeout: int, limit: int = 8) -> dict[str, Any]:
    """Fallback through the local caselaws-cli NotebookLM provider when the raw CLI is unavailable."""
    cmd, cwd = caselaws_command()
    if not cmd:
        return {"ok": False, "error": "caselaws-cli not found for NotebookLM provider fallback", "parsed": None}
    env = {"NOTEBOOKLM_NOTEBOOK": notebook} if notebook else None
    res = run(
        [*cmd, "search", prompt, "--provider", "notebooklm", "--json", "--limit", str(limit)],
        cwd=cwd,
        timeout=timeout + 30,
        env=env,
    )
    parsed = parse_jsonish(res.get("stdout", "")) if res.get("stdout") else None
    return {"ok": bool(res.get("ok")) and not (isinstance(parsed, dict) and parsed.get("error")), "raw": res, "parsed": parsed, "source": "caselaws-cli notebooklm provider"}


def notebooklm_ask(prompt: str, notebook: str | None, timeout: int) -> dict[str, Any]:
    notebooklm_cmd, source = notebooklm_command()
    if not notebooklm_cmd:
        return notebooklm_provider_search(prompt, notebook, timeout)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
        handle.write(prompt)
        path = handle.name
    try:
        prompt_file = Path(path)
        cmd = build_notebooklm_ask_command(notebooklm_cmd, notebook, prompt_file, timeout)
        res = run(cmd, timeout=timeout + 30)
        parsed = parse_jsonish(res.get("stdout", ""))
        return {"ok": bool(res.get("ok")) and not (isinstance(parsed, dict) and parsed.get("error")), "raw": res, "parsed": parsed, "source": source}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def gst_query_prefix(issue: str) -> str:
    base = " ".join(issue.strip().split())
    return base if base.lower().startswith("gst ") else f"GST {base}"


def build_queries(issue: str, jurisdiction: str | None) -> list[tuple[str, str | None]]:
    base = gst_query_prefix(issue)
    queries: list[tuple[str, str | None]] = [
        (f"{base} Supreme Court", None),
        (f"{base} High Court", None),
        (f"{base} natural justice non speaking order", None),
        (f"CBIC circular {base}", "cbic"),
    ]
    if jurisdiction:
        queries.insert(1, (f"{base} {jurisdiction} High Court", None))
    # preserve order but remove duplicates
    seen = set()
    deduped = []
    for query, provider in queries:
        key = (query.lower(), provider)
        if key not in seen:
            deduped.append((query, provider))
            seen.add(key)
    return deduped


def search_cases(issue: str, jurisdiction: str | None, limit: int, timeout: int) -> dict[str, Any]:
    cmd, cwd = caselaws_command()
    if not cmd:
        return {"ok": False, "error": "caselaws-cli not found; install it or set CASELAWS_CLI/CASELAWS_REPO", "searches": []}
    searches = []
    for query, provider in build_queries(issue, jurisdiction):
        full_cmd = [*cmd, "search", query, "--json", "--limit", str(limit)]
        if provider:
            full_cmd.extend(["--provider", provider])
        res = run(full_cmd, cwd=cwd, timeout=timeout)
        parsed = parse_jsonish(res.get("stdout", "")) if res.get("stdout") else None
        searches.append({"query": query, "provider": provider or "default", "ok": res.get("ok"), "results": parsed, "raw": res})
    return {"ok": any(s.get("ok") for s in searches), "searches": searches}


def notebooklm_error_message(nb: dict[str, Any]) -> str:
    parsed = nb.get("parsed")
    if isinstance(parsed, dict):
        for key in ("message", "detail", "error"):
            value = parsed.get(key)
            if value and not isinstance(value, bool):
                return str(value)
        details = parsed.get("details")
        if isinstance(details, dict):
            for key in ("message", "detail", "error"):
                value = details.get(key)
                if value and not isinstance(value, bool):
                    return str(value)
        if parsed.get("status") and parsed.get("status") != "ok":
            return json.dumps(parsed, ensure_ascii=False)
    raw = nb.get("raw")
    if isinstance(raw, dict):
        if raw.get("stderr"):
            return str(raw["stderr"]).strip()
        if raw.get("stdout"):
            return str(raw["stdout"]).strip()
        if raw.get("error"):
            return str(raw["error"])
    return str(nb.get("error") or "unknown error")


def format_markdown(packet: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# GST Appeal Research Packet")
    lines.append("")
    lines.append(f"Generated: {packet['generated_at']}")
    lines.append(f"Issue: {packet['issue']}")
    if packet.get("jurisdiction"):
        lines.append(f"Jurisdiction: {packet['jurisdiction']}")
    lines.append("")
    lines.append("## Facts supplied")
    lines.append("")
    lines.append(packet.get("facts") or "No facts file supplied.")
    lines.append("")
    lines.append("## NotebookLM knowledge-bank response")
    lines.append("")
    nb = packet.get("notebooklm", {})
    if nb.get("ok"):
        parsed = nb.get("parsed")
        if isinstance(parsed, dict) and parsed.get("answer"):
            lines.append(str(parsed["answer"]))
            refs = parsed.get("references") or parsed.get("sources") or []
            if refs:
                lines.append("")
                lines.append("### NotebookLM references")
                lines.append("")
                for idx, ref in enumerate(refs, start=1):
                    lines.append(f"{idx}. `{json.dumps(ref, ensure_ascii=False)}`")
        elif isinstance(parsed, list):
            for idx, item in enumerate(parsed, start=1):
                if isinstance(item, dict):
                    title = item.get("title") or "NotebookLM result"
                    snippet = (item.get("snippet") or item.get("content") or "").replace("\n", " ")
                    lines.append(f"{idx}. **{title}** — {item.get('source') or 'NotebookLM'}")
                    if snippet:
                        lines.append(f"   {snippet}")
                else:
                    lines.append(f"{idx}. {item}")
        elif isinstance(parsed, dict):
            lines.append(json.dumps(parsed, indent=2, ensure_ascii=False))
        else:
            lines.append(str(parsed))
    else:
        lines.append(f"NotebookLM unavailable or failed: {notebooklm_error_message(nb)}")
    lines.append("")
    lines.append("## Case-law searches")
    lines.append("")
    for search in packet.get("case_law", {}).get("searches", []):
        lines.append(f"### {search.get('query')} [{search.get('provider')}]")
        results = search.get("results")
        if isinstance(results, list):
            for idx, item in enumerate(results[:10], start=1):
                if not isinstance(item, dict):
                    lines.append(f"{idx}. {item}")
                    continue
                title = item.get("title") or "Untitled"
                url = item.get("url") or ""
                source = item.get("source") or ""
                date = item.get("date") or ""
                snippet = (item.get("snippet") or "").replace("\n", " ")
                lines.append(f"{idx}. **{title}** — {source} {date}")
                if url:
                    lines.append(f"   URL: {url}")
                if snippet:
                    lines.append(f"   Snippet: {snippet}")
                lines.append("   Status: SEARCH_ONLY — fetch full text before citing.")
        elif isinstance(results, dict) and results.get("error"):
            lines.append(f"Error: {results['error']}")
        else:
            lines.append(str(results or search.get("raw", {}).get("stderr") or "No results."))
        lines.append("")
    lines.append("## Drafting implications checklist")
    lines.append("")
    lines.extend([
        "- Verify limitation, pre-deposit, authorization, and APL-01 requirements before filing.",
        "- Fetch full text for each case proposed above before citing it.",
        "- Classify each authority as binding, persuasive, adverse, or distinguishable.",
        "- Convert NotebookLM propositions into numbered grounds only after matching them to record evidence.",
        "- Mark any unverified source as VERIFY BEFORE FILING.",
    ])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, help="GST dispute issue/fact pattern")
    parser.add_argument("--facts-file", help="Markdown/text file containing facts and order summary")
    parser.add_argument("--jurisdiction", help="State or High Court jurisdiction, if known")
    parser.add_argument("--notebook", help="NotebookLM notebook ID; otherwise NOTEBOOKLM_NOTEBOOK/current context is used")
    parser.add_argument("--case-limit", type=int, default=5, help="Results per case-law query")
    parser.add_argument("--output", help="Write Markdown research packet to this path")
    parser.add_argument("--json", action="store_true", help="Emit JSON packet instead of Markdown")
    parser.add_argument("--timeout", type=int, default=120, help="Per command timeout seconds")
    args = parser.parse_args()

    facts = ""
    if args.facts_file:
        facts = Path(args.facts_file).read_text(encoding="utf-8")

    prompt = f"""You are assisting Indian GST appeal drafting. Use only source-backed material from the connected NotebookLM GST knowledge-bank.\n\nIssue: {args.issue}\nJurisdiction: {args.jurisdiction or 'not specified'}\nFacts:\n{facts or 'No detailed facts supplied.'}\n\nReturn: (1) applicable provisions/rules/forms, (2) circulars/notifications/instructions, (3) likely grounds of appeal, (4) adverse risks, (5) filing checklist. Include source titles/dates and mark anything uncertain.\n"""

    packet = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "issue": args.issue,
        "jurisdiction": args.jurisdiction,
        "facts": facts,
        "notebooklm": notebooklm_ask(prompt, args.notebook, args.timeout),
        "case_law": search_cases(args.issue, args.jurisdiction, args.case_limit, args.timeout),
    }

    output = json.dumps(packet, indent=2, ensure_ascii=False) if args.json else format_markdown(packet)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    print(output)
    # Non-zero only when both research channels fail; this lets case-law-only use work when NotebookLM is not installed locally.
    ok = bool(packet["notebooklm"].get("ok") or packet["case_law"].get("ok"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
