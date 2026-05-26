#!/usr/bin/env python3
"""Create an automated GST appeal drafting workspace from a matter folder.

The script does not replace advocate/CA review. It scans local documents,
extracts a best-effort fact/intake packet, runs NotebookLM prompts and
caselaw research when available, and emits a drafting brief that the agent must
read before preparing the final appeal.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

try:  # sibling import when executed from scripts/.
    from gst_appeal_research import caselaws_command, notebooklm_ask, parse_jsonish, run as run_cmd
except Exception:  # pragma: no cover - defensive import fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gst_appeal_research import caselaws_command, notebooklm_ask, parse_jsonish, run as run_cmd

TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm", ".xml", ".log"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", ".omx"}
GENERATED_DIR_NAMES = {"case-laws", "case_laws", "caselaws", "research", "output", "gst-appeal-workspace"}
GENERATED_FILE_PATTERNS = (
    "research-packet",
    "appeal-drafting-brief",
    "autodraft-summary",
    "facts-digest",
    "gst-appeal-draft",
)

DOC_TYPE_PATTERNS: list[tuple[str, list[str]]] = [
    ("impugned_order", [r"impugned order", r"order[-\s]?in[-\s]?original", r"form\s+gst\s+drc[-\s]?07", r"summary of the order", r"adjudication order"]),
    ("show_cause_notice", [r"show cause notice", r"\bscn\b", r"form\s+gst\s+drc[-\s]?01", r"notice for"]),
    ("reply_or_submission", [r"reply to", r"written submission", r"objection", r"personal hearing", r"submitted that"]),
    ("demand_summary", [r"demand", r"tax payable", r"interest", r"penalty", r"fine", r"fee", r"summary of demand"]),
    ("pre_deposit_or_challan", [r"pre[-\s]?deposit", r"challan", r"drc[-\s]?03", r"payment reference", r"cin\b"]),
    ("return_or_reconciliation", [r"gstr[-\s]?1", r"gstr[-\s]?3b", r"gstr[-\s]?2a", r"gstr[-\s]?2b", r"reconciliation", r"ledger"]),
    ("invoice_or_transport", [r"invoice", r"e[-\s]?way bill", r"lorry receipt", r"transport", r"consignment"]),
    ("authorization", [r"board resolution", r"authori[sz]ation", r"letter of authority", r"vakalatnama"]),
]

ISSUE_PATTERNS: list[tuple[str, list[str]]] = [
    ("Penalty under GST section 125 for alleged failure to display sign board / GSTIN; consider section 126 proportionality and general disciplines", [r"section\s+125", r"sign\s*board", r"display.*gstin"]),
    ("Penalty under GST section 122 / 125 / 126 and proportionality of general penalty", [r"section\s+122", r"section\s+125", r"section\s+126", r"penalty"]),
    ("Input tax credit mismatch between GSTR-2A/2B and GSTR-3B, section 16 conditions, vendor compliance, reversal and evidence", [r"gstr[-\s]?2a", r"gstr[-\s]?2b", r"gstr[-\s]?3b", r"input tax credit", r"\bitc\b", r"mismatch"]),
    ("Demand under section 73/74/74A: limitation, suppression/fraud ingredients, tax computation, interest and penalty", [r"section\s+73", r"section\s+74", r"section\s+74a", r"suppression", r"fraud"]),
    ("Natural justice: no effective hearing, reply/evidence not considered, non-speaking order, mechanical confirmation", [r"personal hearing", r"not considered", r"natural justice", r"non[-\s]?speaking", r"reply"]),
    ("Order beyond show-cause notice or new basis introduced in adjudication order", [r"beyond.*show cause", r"new ground", r"not proposed", r"outside.*notice"]),
    ("Registration cancellation / revocation / appeal limitation under GST", [r"registration.*cancel", r"revocation", r"reg[-\s]?17", r"reg[-\s]?19"]),
    ("Detention/confiscation of goods or conveyance under sections 129/130", [r"section\s+129", r"section\s+130", r"detention", r"confiscation", r"mov[-\s]?0"]),
    ("Interest under section 50: liability, gross/net tax basis, cash ledger, computation", [r"section\s+50", r"interest"]),
    ("Refund rejection / deficiency memo / unjust enrichment / limitation", [r"refund", r"rfd[-\s]?", r"unjust enrichment"]),
]


def slugify(text: str, *, fallback: str = "issue") -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return value[:70] or fallback


def read_text_file(path: Path, max_chars: int) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return "", [f"Failed to read text file {path}: {exc}"]
    if len(text) > max_chars:
        warnings.append(f"Clipped {path.name} to {max_chars} characters for prompt safety.")
        text = text[:max_chars]
    return text, warnings


def read_pdf(path: Path, max_chars: int) -> tuple[str, list[str]]:
    try:
        from pypdf import PdfReader
    except Exception:
        return "", [f"PDF text extraction needs pypdf; skipped {path.name}."]
    try:
        reader = PdfReader(str(path))
        pages: list[str] = []
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"--- Page {page_num} ---\n{page_text}")
            if sum(len(p) for p in pages) >= max_chars:
                pages.append("...[clipped]")
                break
        return "\n\n".join(pages)[:max_chars], []
    except Exception as exc:
        return "", [f"Failed to extract PDF text from {path.name}: {exc}"]


def read_docx(path: Path, max_chars: int) -> tuple[str, list[str]]:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for para in root.findall(".//w:p", ns):
            parts = [node.text or "" for node in para.findall(".//w:t", ns)]
            joined = "".join(parts).strip()
            if joined:
                paragraphs.append(joined)
        text = "\n".join(paragraphs)
        return text[:max_chars], ([f"Clipped {path.name} to {max_chars} characters."] if len(text) > max_chars else [])
    except Exception as exc:
        return "", [f"Failed to extract DOCX text from {path.name}: {exc}"]


def read_image_ocr(path: Path, max_chars: int) -> tuple[str, list[str]]:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return "", [f"Image OCR skipped for {path.name}: tesseract is not installed or not in PATH."]
    try:
        cp = subprocess.run([tesseract, str(path), "stdout"], text=True, capture_output=True, timeout=60)
        if cp.returncode != 0:
            return "", [f"Image OCR failed for {path.name}: {cp.stderr.strip()}"]
        text = cp.stdout.strip()
        return text[:max_chars], ([f"Clipped OCR text for {path.name} to {max_chars} characters."] if len(text) > max_chars else [])
    except Exception as exc:
        return "", [f"Image OCR failed for {path.name}: {exc}"]


def iter_matter_files(root: Path, output_dir: Path | None = None, include_generated: bool = False) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        parts = set(path.parts)
        if parts & SKIP_DIRS:
            continue
        if not include_generated and {part.lower() for part in path.parts} & GENERATED_DIR_NAMES:
            continue
        if output_dir and output_dir in path.parents:
            continue
        lower_name = path.name.lower()
        if not include_generated and any(pattern in lower_name for pattern in GENERATED_FILE_PATTERNS):
            continue
        yield path


def extract_document(path: Path, matter_dir: Path, max_chars: int) -> dict[str, Any]:
    suffix = path.suffix.lower()
    warnings: list[str] = []
    text = ""
    extraction = "unsupported"
    if suffix in TEXT_EXTENSIONS:
        text, warnings = read_text_file(path, max_chars)
        extraction = "text"
    elif suffix in PDF_EXTENSIONS:
        text, warnings = read_pdf(path, max_chars)
        extraction = "pdf"
    elif suffix in DOCX_EXTENSIONS:
        text, warnings = read_docx(path, max_chars)
        extraction = "docx"
    elif suffix in IMAGE_EXTENSIONS:
        text, warnings = read_image_ocr(path, max_chars)
        extraction = "image_ocr" if text else "image_pending_ocr"
    else:
        warnings = [f"Unsupported file type {suffix or '(none)'}; file inventoried but not extracted."]
    try:
        rel = path.relative_to(matter_dir)
    except ValueError:
        rel = path
    return {
        "path": str(path),
        "relative_path": str(rel),
        "name": path.name,
        "suffix": suffix,
        "size_bytes": path.stat().st_size,
        "extraction": extraction,
        "text": text,
        "warnings": warnings,
        "doc_types": classify_document(text, path.name),
    }


def classify_document(text: str, filename: str = "") -> list[str]:
    haystack = f"{filename}\n{text}".lower()
    types: list[str] = []
    for doc_type, patterns in DOC_TYPE_PATTERNS:
        if any(re.search(pattern, haystack, re.IGNORECASE) for pattern in patterns):
            types.append(doc_type)
    return types or ["unclassified"]


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = " ".join(str(value).split())
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            out.append(normalized)
    return out


def extract_metadata(text: str) -> dict[str, Any]:
    sections = dedupe(
        match.group(0)
        for match in re.finditer(r"\b(?:section|u/s|under section)\s*\d{1,3}[A-Z]?(?:\s*\([^)]{1,8}\))*", text, re.IGNORECASE)
    )
    rules = dedupe(match.group(0) for match in re.finditer(r"\brule\s*\d{1,3}[A-Z]?", text, re.IGNORECASE))
    forms = dedupe(
        match.group(0)
        for match in re.finditer(r"\b(?:FORM\s+)?GST[-\s]?(?:DRC|APL|ASMT|MOV|REG|RFD|PMT)[-\s]?\d+[A-Z]?\b", text, re.IGNORECASE)
    )
    gstins = dedupe(re.findall(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", text))
    dates = dedupe(
        re.findall(
            r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
            text,
            flags=re.IGNORECASE,
        )
    )[:40]
    amounts = dedupe(
        match.group(0)
        for match in re.finditer(r"(?:₹|Rs\.?|INR)\s*[0-9][0-9,]*(?:\.\d+)?|[0-9][0-9,]*(?:\.\d+)?\s*(?:rupees|tax|penalty|interest)", text, re.IGNORECASE)
    )[:50]
    return {"sections": sections, "rules": rules, "forms": forms, "gstins": gstins, "dates": dates, "amounts": amounts}


def infer_issues(text: str, explicit_issues: list[str] | None = None) -> list[str]:
    issues = list(explicit_issues or [])
    haystack = text.lower()
    for issue, patterns in ISSUE_PATTERNS:
        if any(re.search(pattern, haystack, re.IGNORECASE) for pattern in patterns):
            issues.append(issue)
    # Always include maintainability because every appeal needs it.
    issues.append("Appeal maintainability under section 107: limitation from communication date, condonation, APL-01, admitted dues, statutory pre-deposit, certified copy and authorization")
    return dedupe(issues)


def build_facts_digest(documents: list[dict[str, Any]], metadata: dict[str, Any], issues: list[str], max_chars: int = 18000) -> str:
    chunks: list[str] = []
    chunks.append("# Matter facts digest")
    chunks.append("")
    chunks.append("## Extracted metadata")
    for key, values in metadata.items():
        chunks.append(f"- {key}: {', '.join(values) if values else 'not found'}")
    chunks.append("")
    chunks.append("## Inferred issues")
    for issue in issues:
        chunks.append(f"- {issue}")
    chunks.append("")
    chunks.append("## Document excerpts")
    remaining = max_chars - sum(len(c) + 1 for c in chunks)
    for doc in documents:
        text = (doc.get("text") or "").strip()
        if not text:
            continue
        header = f"\n### {doc['relative_path']} ({', '.join(doc.get('doc_types', []))})\n"
        allowed = max(0, min(3500, remaining - len(header)))
        if allowed <= 0:
            chunks.append("\n...[digest clipped]")
            break
        excerpt = text[:allowed]
        chunks.append(header + excerpt)
        remaining -= len(header) + len(excerpt)
    return "\n".join(chunks)


def build_notebook_prompts(facts_digest: str, issues: list[str], forum: str, jurisdiction: str | None) -> dict[str, str]:
    issue_block = "\n".join(f"- {issue}" for issue in issues)
    common = f"""Forum: {forum or 'not specified'}
Jurisdiction: {jurisdiction or 'not specified'}
Issues:
{issue_block}

Facts digest:
{facts_digest}
"""
    return {
        "01_provisions_forms_circulars": f"""You are a senior Indian GST appellate practitioner. Use only source-backed material from this NotebookLM GST law notebook.

Task: create a provisions/forms/circulars matrix for drafting this GST appeal.

{common}

Return columns: issue, section/rule/form/circular/notification, date/currentness caveat, exact proposition, source title/source id, how to plead it, what must be verified independently before filing. Mark uncertain items VERIFY BEFORE FILING.""",
        "02_grounds_risks_relief": f"""You are preparing grounds of appeal and written submissions for a GST appeal. Use only source-backed NotebookLM material and keep facts, grounds, arguments, and prayer separate.

{common}

Return: (1) strongest grounds, (2) alternate/subsidiary grounds, (3) adverse risks and distinctions, (4) evidence required for each ground, (5) relief/prayer options. Include source references for every legal proposition.""",
        "03_limitation_predeposit_filing": f"""Act as a GST appeal filing checklist reviewer. Use source-backed NotebookLM material.

{common}

Return a first-appeal/GSTAT/High Court filing checklist as applicable: limitation, condonation, admitted dues, disputed-tax pre-deposit, certified/uploaded order copy, APL form, authorization, fees, paper-book order, additional evidence, verification/signature, and portal caveats. Flag missing information.""",
        "04_case_law_query_plan": f"""Create a case-law research plan for caselaws-cli. Use the facts and issues below.

{common}

Return: prioritized search strings for Supreme Court, jurisdictional High Court, other High Courts, GSTAT/CESTAT analogies, CBIC circular/notification searches, and adverse authority searches. For each query, state why it matters and what result would be useful.""",
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_notebook_research(prompts: dict[str, str], output_dir: Path, notebook: str | None, timeout: int, skip: bool) -> list[dict[str, Any]]:
    prompt_dir = output_dir / "notebooklm-prompts"
    result_dir = output_dir / "notebooklm-results"
    runs: list[dict[str, Any]] = []
    for name, prompt in prompts.items():
        prompt_path = prompt_dir / f"{name}.txt"
        write_text(prompt_path, prompt)
        if skip:
            runs.append({"name": name, "prompt_file": str(prompt_path), "skipped": True})
            continue
        result = notebooklm_ask(prompt, notebook, timeout)
        json_path = result_dir / f"{name}.json"
        write_json(json_path, result)
        parsed = result.get("parsed")
        md_text = ""
        if isinstance(parsed, dict):
            md_text = str(parsed.get("answer") or json.dumps(parsed, indent=2, ensure_ascii=False))
        else:
            md_text = str(parsed)
        md_path = result_dir / f"{name}.md"
        write_text(md_path, md_text)
        runs.append({"name": name, "prompt_file": str(prompt_path), "json_file": str(json_path), "markdown_file": str(md_path), "ok": bool(result.get("ok")), "source": result.get("source")})
    return runs


def run_caselaw_research(
    issues: list[str],
    facts_digest_path: Path,
    output_dir: Path,
    jurisdiction: str | None,
    forum: str,
    notebook: str | None,
    case_limit: int,
    fetch_top: int,
    timeout: int,
    skip: bool,
) -> list[dict[str, Any]]:
    result_dir = output_dir / "caselaw-research"
    result_dir.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []
    cmd, cwd = caselaws_command()
    if not cmd:
        return [{"ok": False, "error": "caselaws-cli not found", "skipped": False}]
    for idx, issue in enumerate(issues, 1):
        slug = f"{idx:02d}-{slugify(issue)}"
        json_path = result_dir / f"{slug}.json"
        md_path = result_dir / f"{slug}.md"
        base_cmd = [
            *cmd,
            "research",
            issue,
            "--facts-file",
            str(facts_digest_path),
            "--forum",
            forum,
            "--limit",
            str(case_limit),
            "--fetch-top",
            str(fetch_top),
        ]
        if jurisdiction:
            base_cmd.extend(["--jurisdiction", jurisdiction])
        if notebook:
            base_cmd.extend(["--notebook", notebook])
        if skip:
            runs.append({"issue": issue, "command": base_cmd, "skipped": True})
            continue
        json_res = run_cmd([*base_cmd, "--json"], cwd=cwd, timeout=timeout + 60)
        parsed = parse_jsonish(json_res.get("stdout", "")) if json_res.get("stdout") else None
        write_json(json_path, parsed if parsed is not None else json_res)
        md_res = run_cmd([*base_cmd, "--no-notebooklm"], cwd=cwd, timeout=timeout + 60)
        write_text(md_path, md_res.get("stdout") or md_res.get("stderr") or "")
        runs.append({"issue": issue, "command": base_cmd, "json_file": str(json_path), "markdown_file": str(md_path), "ok": bool(json_res.get("ok") or md_res.get("ok")), "json_returncode": json_res.get("returncode"), "markdown_returncode": md_res.get("returncode")})
    return runs


def format_brief(packet: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# GST Appeal Automated Drafting Brief")
    lines.append("")
    lines.append(f"Generated: {packet['generated_at']}")
    lines.append(f"Matter folder: `{packet['matter_dir']}`")
    lines.append(f"Forum: {packet.get('forum') or 'not specified'}")
    if packet.get("jurisdiction"):
        lines.append(f"Jurisdiction: {packet['jurisdiction']}")
    lines.append("")
    lines.append("## 1. Document inventory and extraction status")
    lines.append("")
    lines.append("| File | Types | Extraction | Warnings |")
    lines.append("|---|---|---|---|")
    for doc in packet.get("documents", []):
        warnings = "; ".join(doc.get("warnings") or [])
        lines.append(f"| `{doc['relative_path']}` | {', '.join(doc.get('doc_types', []))} | {doc.get('extraction')} | {warnings or '-'} |")
    lines.append("")
    lines.append("## 2. Extracted metadata")
    lines.append("")
    for key, values in packet.get("metadata", {}).items():
        lines.append(f"- **{key}:** {', '.join(values) if values else 'not found'}")
    lines.append("")
    lines.append("## 3. Inferred appeal issues")
    lines.append("")
    for issue in packet.get("issues", []):
        lines.append(f"- {issue}")
    lines.append("")
    lines.append("## 4. Research artifacts produced")
    lines.append("")
    lines.append("### NotebookLM prompts/results")
    for run in packet.get("notebooklm_runs", []):
        status = "SKIPPED" if run.get("skipped") else ("OK" if run.get("ok") else "CHECK")
        lines.append(f"- **{run.get('name')}** [{status}] prompt: `{run.get('prompt_file')}` result: `{run.get('markdown_file') or run.get('json_file') or '-'}`")
    lines.append("")
    lines.append("### Case-law research packets")
    for run in packet.get("caselaw_runs", []):
        status = "SKIPPED" if run.get("skipped") else ("OK" if run.get("ok") else "CHECK")
        lines.append(f"- **{run.get('issue', 'caselaws-cli')}** [{status}] packet: `{run.get('markdown_file') or run.get('json_file') or '-'}`")
    lines.append("")
    lines.append("## 5. Drafting skeleton to use after reading research")
    lines.append("")
    lines.extend([
        "1. Cause title and appellant/respondent particulars.",
        "2. Maintainability paragraph: order communication date, limitation, condonation if any, admitted dues, disputed-tax pre-deposit, authorization, certified/uploaded order copy.",
        "3. Synopsis and list of dates from SCN → reply/evidence/hearing → impugned order → appeal filing.",
        "4. Statement of facts: neutral chronology only, with annexure references.",
        "5. Grounds of appeal: one concise error per ground; include jurisdiction/procedure/facts/law/computation/penalty grounds as applicable.",
        "6. Written submissions: finding challenged → record evidence → statutory provision → circular/notification → verified case law → application → relief.",
        "7. Case-law table: authority, forum, date/citation, proposition, applicability, limits/adverse risk, verification status.",
        "8. Prayer: primary deletion/set aside, alternate remand/recompute, consequential relief, stay/recovery relief, hearing, additional evidence if needed.",
        "9. Verification and paper-book index.",
    ])
    lines.append("")
    lines.append("## 6. Mandatory filing/proofread checklist before final output")
    lines.append("")
    checklist = [
        "SCN allegations, reply/evidence, findings, and appeal grounds mapped issue-by-issue.",
        "Demand breakup captured: tax, interest, penalty, fine, fee; admitted vs disputed amounts separated.",
        "Limitation computed from date of communication/receipt; condonation drafted if required.",
        "Pre-deposit and admitted dues checked against current forum rule; challan/DRC-03/DRC-03A evidence listed.",
        "Every cited case/circular/rule read in full or marked VERIFY BEFORE FILING.",
        "Binding hierarchy checked: Supreme Court, jurisdictional High Court, then persuasive authorities.",
        "Adverse authorities/department risks identified and distinguished.",
        "Facts, grounds, submissions, prayer, and verification kept separate.",
        "No personal allegations against officer; attack only jurisdictional, factual, legal, procedural, and computation errors.",
        "Annexures indexed, paginated, legible, and cross-referenced in the draft.",
        "Final draft proofread for party names, GSTIN, dates, order numbers, tax periods, amounts, sections/rules/forms, and contradictions.",
    ]
    for item in checklist:
        lines.append(f"- [ ] {item}")
    lines.append("")
    lines.append("## 7. Information still required before filing")
    lines.append("")
    missing = packet.get("missing_information") or []
    for item in missing:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("**Agent instruction:** Read the facts digest, NotebookLM result files, and caselaw packets above before drafting. Do not cite SEARCH_ONLY results as final authorities. Mark unverified propositions as VERIFY BEFORE FILING.")
    lines.append("")
    return "\n".join(lines)


def find_missing_information(metadata: dict[str, Any], documents: list[dict[str, Any]]) -> list[str]:
    doc_types = {dt for doc in documents for dt in doc.get("doc_types", [])}
    missing: list[str] = []
    if "impugned_order" not in doc_types:
        missing.append("Impugned order / DRC-07 not clearly identified.")
    if "show_cause_notice" not in doc_types:
        missing.append("Show-cause notice / DRC-01 not clearly identified.")
    if not metadata.get("dates"):
        missing.append("Critical dates not extracted; manually confirm order communication date and limitation.")
    if not metadata.get("amounts"):
        missing.append("Demand amounts not extracted; manually prepare tax/interest/penalty breakup.")
    if "pre_deposit_or_challan" not in doc_types:
        missing.append("Pre-deposit/admitted dues payment proof not found.")
    if "authorization" not in doc_types:
        missing.append("Authorization/board resolution/vakalatnama not found.")
    return missing


def build_workspace(args: argparse.Namespace) -> dict[str, Any]:
    matter_dir = Path(args.matter_dir).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else matter_dir / "gst-appeal-workspace"
    output_dir.mkdir(parents=True, exist_ok=True)

    documents = [extract_document(path, matter_dir, args.max_chars_per_document) for path in iter_matter_files(matter_dir, output_dir, args.include_generated)]
    combined_text = "\n\n".join(doc.get("text") or "" for doc in documents)
    metadata = extract_metadata(combined_text)
    issues = infer_issues(combined_text + "\n" + "\n".join(doc["name"] for doc in documents), args.issue or [])
    facts_digest = build_facts_digest(documents, metadata, issues, max_chars=args.max_facts_chars)
    facts_digest_path = output_dir / "facts-digest.md"
    write_text(facts_digest_path, facts_digest)

    prompts = build_notebook_prompts(facts_digest, issues, args.forum, args.jurisdiction)
    notebook_runs = run_notebook_research(prompts, output_dir, args.notebook, args.timeout, args.skip_live_research or args.skip_notebooklm)
    caselaw_runs = run_caselaw_research(
        issues,
        facts_digest_path,
        output_dir,
        args.jurisdiction,
        args.forum,
        args.notebook,
        args.case_limit,
        args.fetch_top,
        args.timeout,
        args.skip_live_research or args.skip_caselaws,
    )

    packet = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "matter_dir": str(matter_dir),
        "output_dir": str(output_dir),
        "forum": args.forum,
        "jurisdiction": args.jurisdiction,
        "documents": [{k: v for k, v in doc.items() if k != "text"} for doc in documents],
        "metadata": metadata,
        "issues": issues,
        "facts_digest_file": str(facts_digest_path),
        "notebooklm_runs": notebook_runs,
        "caselaw_runs": caselaw_runs,
        "missing_information": find_missing_information(metadata, documents),
    }
    write_json(output_dir / "autodraft-summary.json", packet)
    brief = format_brief(packet)
    write_text(output_dir / "appeal-drafting-brief.md", brief)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matter-dir", default=".", help="Folder containing notices/orders/evidence for the GST matter")
    parser.add_argument("--output-dir", help="Workspace folder for extracted facts, prompts, research packets and brief")
    parser.add_argument("--issue", action="append", help="Explicit issue/fact pattern; can be repeated. Auto-inferred issues are added too")
    parser.add_argument("--forum", default="first appeal under CGST Act section 107", help="Appeal forum/stage")
    parser.add_argument("--jurisdiction", help="State or jurisdictional High Court, if known")
    parser.add_argument("--notebook", help="NotebookLM notebook ID; otherwise NOTEBOOKLM_NOTEBOOK/config/current context is used")
    parser.add_argument("--case-limit", type=int, default=5, help="Case-law results per query")
    parser.add_argument("--fetch-top", type=int, default=0, help="Fetch top N full texts per caselaws-cli research provider")
    parser.add_argument("--timeout", type=int, default=120, help="Per external command timeout seconds")
    parser.add_argument("--max-chars-per-document", type=int, default=30000, help="Extraction cap per document")
    parser.add_argument("--max-facts-chars", type=int, default=18000, help="Facts digest cap for prompts")
    parser.add_argument("--include-generated", action="store_true", help="Also read prior generated drafts/research packets in the matter folder")
    parser.add_argument("--skip-live-research", action="store_true", help="Only scan/extract and write prompts; do not call NotebookLM or caselaws-cli")
    parser.add_argument("--skip-notebooklm", action="store_true", help="Skip NotebookLM prompt execution")
    parser.add_argument("--skip-caselaws", action="store_true", help="Skip caselaws-cli research execution")
    parser.add_argument("--json", action="store_true", help="Print summary JSON")
    args = parser.parse_args()

    packet = build_workspace(args)
    if args.json:
        print(json.dumps(packet, indent=2, ensure_ascii=False))
    else:
        print(f"GST appeal autodraft workspace created: {packet['output_dir']}")
        print(f"Read: {Path(packet['output_dir']) / 'appeal-drafting-brief.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
