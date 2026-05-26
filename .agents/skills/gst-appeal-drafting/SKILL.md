---
name: gst-appeal-drafting
description: Draft, review, or research Indian GST appeals using a connected NotebookLM GST law knowledge-bank and a local GST case-law CLI. Use when the task involves GST APL-01/GSTAT/High Court appeal drafting, statement of facts, grounds of appeal, prayers, limitation/pre-deposit checks, paper-book planning, or precedent research for GST notices/orders in India.
---

# GST Appeal Drafting

Use this skill to produce professional, evidence-grounded GST appeal drafts. It does **not** replace Chartered Accountant/advocate review; always preserve citations, assumptions, verification gaps, and filing caveats.

## Core rule: first prompt should trigger the whole workflow

When the user asks to draft, review, or prepare a GST appeal and provides a matter folder/documents, do **not** ask the user to run separate research commands. The agent must automatically:

1. check tool availability;
2. scan the matter folder for SCN/order/reply/evidence/payment/authorization documents;
3. extract facts and infer issues;
4. run NotebookLM law-bank prompts for source-backed provisions, forms, grounds, risks, limitation/pre-deposit and filing checklist;
5. run `caselaws-cli research` for each issue across NotebookLM, Indian Kanoon/search, CBIC/GST Council and adverse-risk queries;
6. read the generated packets;
7. fetch/read full text for authorities selected for citation;
8. draft the appeal;
9. fact-check, source-check, and proofread before final output.

If a critical item is missing, continue with clearly marked assumptions and an “Information required before filing” list.

## Required inputs to collect or infer

- Forum/stage: first appeal under CGST/SGST Act section 107 / GSTAT / High Court / writ / other.
- Impugned order: order number, issuing authority, date of order, date of communication/receipt, tax periods, demand breakup.
- SCN/notice: form/number/date, allegations, proposed demand, statutory sections/rules, relied documents.
- Assessee response: reply, evidence, reconciliations, hearing requests, hearing records, submissions.
- Order findings: facts accepted/rejected, law applied, computation, penalty/interest reasoning, new grounds beyond SCN.
- Limitation and pre-deposit: filing deadline, condonation need, admitted dues paid, disputed-tax/penalty pre-deposit, challans/DRC-03/DRC-03A.
- Evidence: returns, ledgers, invoices, e-way bills, notices, DRC forms, challans, correspondence, authorization, certified/uploaded order copy.

## Automated matter workflow

Run this first for a drafting/review task with a folder of notices/orders/evidence:

```bash
python3 <skill>/scripts/check_environment.py --install --json
python3 <skill>/scripts/gst_appeal_autodraft.py \
  --matter-dir <matter-folder> \
  --forum "first appeal under CGST Act section 107" \
  --jurisdiction "<State or High Court if known>" \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --output-dir <matter-folder>/gst-appeal-workspace
```

Notes:
- Omit `--notebook` if the CLI already has `NOTEBOOKLM_NOTEBOOK` or an active notebook context.
- Use `--issue "..."` for user-specified issues; the script also infers issues from documents.
- Use `--fetch-top 1` only when the user wants slower full-text verification extracts during the automated run. Otherwise fetch selected authorities later.
- Use `--skip-live-research` only for tests, offline environments, or when the user explicitly wants extraction without live NotebookLM/case-law calls.
- By default the scanner ignores prior generated drafts/research folders (`case-laws/`, `research/`, `output/`, `gst-appeal-workspace/`) to avoid circular reasoning. Use `--include-generated` only when a prior draft/research packet is intentionally part of the review.

After the command finishes, read:

```text
<matter-folder>/gst-appeal-workspace/facts-digest.md
<matter-folder>/gst-appeal-workspace/appeal-drafting-brief.md
<matter-folder>/gst-appeal-workspace/notebooklm-results/*.md
<matter-folder>/gst-appeal-workspace/caselaw-research/*.md
```

The brief is not the final appeal; it is the intake and research workbench for the agent.

## Tool dependency behavior

Agents must install missing CLIs automatically when the user asks to use this plugin on this laptop:

```bash
python3 <skill>/scripts/check_environment.py --install --json
```

Or install directly:

```bash
python3 <skill>/scripts/install_dependencies.py --only all
```

This installs/uses `caselaws-cli` from the bundled/local repo or `https://github.com/Wadhawnaiya/caselaws-cli` and `notebooklm` from `notebooklm-py[browser]`. If NotebookLM is installed but not authenticated, run `notebooklm login`; Google sign-in requires human browser authentication.

## NotebookLM law-bank extraction

- Use the already-connected NotebookLM CLI or the `caselaws-cli --provider notebooklm` bridge. Prefer explicit notebook IDs via `--notebook` / `NOTEBOOKLM_NOTEBOOK`; avoid relying on shared `notebooklm use` state in parallel agents.
- Ask targeted questions, not broad “tell me GST law” prompts.
- Require source-backed answers with section/rule/circular/notification references, source titles/IDs, dates, caveats and supersession risks.
- Never upload/paste privileged client material into NotebookLM unless the user has authorized that notebook for the matter. Reading from an already-authorized law notebook is fine.
- Useful commands:
  ```bash
  notebooklm auth check --test --json
  notebooklm metadata --notebook "$NOTEBOOKLM_NOTEBOOK" --json
  notebooklm ask --notebook "$NOTEBOOKLM_NOTEBOOK" --json --timeout 120 --prompt-file prompt.txt
  caselaws-cli search "GST section 107 appeal limitation" --provider notebooklm --json --limit 5
  ```

## Case-law and official-source research

Use the integrated research command for issue-level packets:

```bash
caselaws-cli research "GST section 125 sign board penalty section 126 proportionality" \
  --facts-file facts-digest.md \
  --forum "first appeal under section 107" \
  --jurisdiction "Punjab" \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --limit 5 \
  --output research-packet.md
```

Provider discipline:
- `notebooklm`: source-backed law-bank synthesis and source references.
- `kanoon`: Indian Kanoon / court-oriented discovery.
- `search`: broad web/index discovery, including GSTAT/CESTAT analogies.
- `cbic`: official CBIC/GST Council circulars, notifications, rules, instructions.
- Prefer Supreme Court and jurisdictional High Court; then other High Courts, GSTAT/CESTAT analogies; AAR/AAAR only as narrow persuasive material.
- Fetch/read full text for selected hits with `caselaws-cli get <index-or-url> --json` before relying on them.
- Distinguish binding, persuasive, adverse, and distinguishable authorities.

The legacy single-issue helper remains available:

```bash
python3 <skill>/scripts/gst_appeal_research.py \
  --issue "ITC mismatch between GSTR-2A and GSTR-3B" \
  --facts-file facts.md \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --output research-packet.md
```

## Drafting structure

Use this order unless forum rules require another format:

1. **Cause title and party details**
2. **Index / list of annexures**
3. **Synopsis and list of dates**
4. **Statement of facts** — neutral, chronological, numbered, evidence-linked; no arguments.
5. **Grounds of appeal** — concise numbered legal errors; one ground per issue/error.
6. **Detailed written submissions** — facts, law, circulars, case law, application, relief.
7. **Prayer / relief sought** — quashing/set aside/modification, deletion/recompute, remand, stay/recovery relief, consequential relief, personal hearing.
8. **Verification**
9. **Paper-book checklist and annexures**
10. **Filing-risk checklist** — limitation, pre-deposit, certified/uploaded copy, authorization, fees, condonation, jurisdiction, portal defects.

For first appeals, ensure compatibility with FORM GST APL-01 grounds and verification requirements.

## Mandatory quality gate before final answer

Load `references/icai-guide-principles.md` before preparing any appeal draft or review checklist.

Before providing the final draft, perform and report this gate:

- Facts, grounds, submissions, prayer and verification are separated.
- SCN allegation → reply/evidence → order finding → error → relief is mapped for every major issue.
- Demand breakup, admitted/disputed dues and pre-deposit are captured or flagged.
- Limitation is computed from communication/receipt date or flagged.
- Each legal proposition is tied to a provision/rule/circular/case/source or marked `VERIFY BEFORE FILING`.
- Search-only cases are not cited as final authorities.
- Selected authorities have full text/official source checked or their status is expressly not final.
- Binding hierarchy and jurisdictional value are identified.
- Adverse authorities/risks are identified and distinguished where possible.
- Order-beyond-SCN, natural justice, non-speaking order, evidence ignored, jurisdiction, limitation, computation and penalty ingredients are checked.
- Names, GSTIN, dates, order numbers, tax periods, forms, amounts and annexure labels are proofread.
- The draft attacks the adjudication error, not the officer personally.
- Filing caveats and professional-review notes are included.

## References to load as needed

- `references/auto-installation.md` — automatic dependency installation rules for agents.
- `references/drafting-playbook.md` — detailed drafting architecture and model output format.
- `references/research-protocol.md` — NotebookLM and caselaws-cli prompts/queries.
- `references/source-map.md` — authoritative source hierarchy and key GST appeal provisions.
- `references/templates.md` — appeal skeleton, grounds patterns, case-law table, SCN/reply/order matrix.
- `references/icai-guide-principles.md` — concise drafting and filing discipline derived from the ICAI Practical Guide to GST Adjudication and Appeals including GSTAT. Load this for all appeal drafting tasks.

## Output contract

Return drafts with these sections:

```markdown
# GST Appeal Draft

## Assumptions and missing information
## Filing and maintainability checklist
## Synopsis
## List of dates
## Statement of facts
## Grounds of appeal
## Written submissions
## Case-law table
## Prayer
## Verification
## Annexure / paper-book index
## Final professional-review checklist
```

Use footnote-style citations or parenthetical source references. Mark every unverified proposition as `VERIFY BEFORE FILING`.
