---
name: gst-appeal-drafting
description: Draft, review, or research Indian GST appeals using a connected NotebookLM GST law knowledge-bank and a local GST case-law CLI. Use when the task involves GST APL-01/GSTAT/High Court appeal drafting, statement of facts, grounds of appeal, prayers, limitation/pre-deposit checks, paper-book planning, or precedent research for GST notices/orders in India.
---

# GST Appeal Drafting

Use this skill to produce professional, evidence-grounded GST appeal drafts. It does **not** replace a Chartered Accountant/advocate review; always preserve citations, assumptions, and verification gaps.

## Required inputs

Before final drafting, collect or infer from documents:
- Forum/stage: first appeal under CGST Act section 107 / GSTAT / High Court / other.
- Impugned order: date of communication, order number, issuing authority, tax periods, demand breakup.
- Disputed issues: section/rule involved, facts found, assessee position, department reasoning.
- Limitation and pre-deposit facts: filing deadline, condonation need, admitted dues paid, disputed tax pre-deposit.
- Evidence: SCN, reply, hearing records, returns, reconciliation, ledgers, invoices, e-way bills, notices, DRC forms, challans, correspondence.

If any critical item is missing, continue with a clearly marked assumption and an “Information required before filing” list.

## Research-first workflow

1. **Check and self-install tool dependencies**
   Agents must install missing CLIs automatically when the user asks to use this plugin on this laptop:
   ```bash
   python3 <skill>/scripts/check_environment.py --install --json
   ```
   Or install directly:
   ```bash
   python3 <skill>/scripts/install_dependencies.py --only all
   ```
   This installs/uses `caselaws-cli` from the local repo or `https://github.com/Wadhawnaiya/caselaws-cli` and `notebooklm` from `notebooklm-py[browser]`. The checker also detects the bundled `caselaws-cli/.venv/bin/notebooklm`. If NotebookLM is installed but not authenticated, run `notebooklm login`; Google sign-in requires human browser authentication.

2. **NotebookLM law-bank extraction**
   - Use the already-connected NotebookLM CLI or the `caselaws-cli --provider notebooklm` bridge. Prefer explicit notebook IDs via `--notebook` / `NOTEBOOKLM_NOTEBOOK`; avoid relying on shared `notebooklm use` state in parallel agents.
   - Ask targeted questions, not broad “tell me GST law” prompts.
   - Require source-backed answers with section/rule/circular/notification references and dates.
   - Never paste client secrets or privileged material unless the user has authorized that NotebookLM notebook for the matter.
   - Useful commands:
     ```bash
     notebooklm auth check --test --json
     notebooklm metadata --notebook "$NOTEBOOKLM_NOTEBOOK" --json
     notebooklm ask --notebook "$NOTEBOOKLM_NOTEBOOK" --json --prompt-file prompt.txt
     caselaws-cli search "GST section 107 limitation pre deposit" --provider notebooklm --json --limit 5
     ```

3. **Case-law research**
   - Use `caselaws-cli search "<issue + section + fact pattern>" --json`.
   - Use `--provider search` for broad web/index discovery, `--provider kanoon` for Indian Kanoon, `--provider cbic` for official CBIC circulars/notifications, and `--provider notebooklm` for your NotebookLM knowledge-bank.
   - Prefer Supreme Court and jurisdictional High Court; then other High Courts, GSTAT/CESTAT analogies, AAAR/AAR only as persuasive and with caution.
   - Fetch full text for the best hits with `caselaws-cli get <index-or-url> --json` before relying on them.
   - Distinguish binding, persuasive, adverse, and distinguishable authorities.

4. **Generate a research packet**
   ```bash
   python3 <skill>/scripts/gst_appeal_research.py \
     --issue "ITC mismatch between GSTR-2A and GSTR-3B" \
     --facts-file facts.md \
     --notebook "$NOTEBOOKLM_NOTEBOOK" \
     --output research-packet.md
   ```
   Read the packet before drafting. The packet may contain NotebookLM synthesis, source references, broad case-law search hits, CBIC results, and verification warnings. Do not cite authorities that remain unverified.

## Drafting structure

Use this order unless the forum rules require another format:

1. **Cause title and party details**
2. **Index / list of annexures**
3. **Synopsis and list of dates**
4. **Statement of facts** — neutral, chronological, numbered, evidence-linked; no arguments.
5. **Grounds of appeal** — concise numbered legal errors. One ground per issue/error. Avoid argumentative submissions inside grounds.
6. **Detailed written submissions** — where facts, law, circulars, and case law are applied.
7. **Prayer / relief sought** — quashing, setting aside/modification, remand, stay/recovery relief, consequential relief, personal hearing.
8. **Verification**
9. **Paper-book checklist and annexures**
10. **Filing-risk checklist** — limitation, pre-deposit, certified copy, authorization, appeal fees, condonation, jurisdiction.

For first appeals, ensure the draft is compatible with FORM GST APL-01 grounds and verification requirements.

## Quality bar

Load `references/icai-guide-principles.md` before preparing any appeal draft or appeal-review checklist.

A good GST appeal draft must:
- Separate facts, grounds, submissions, and prayers.
- Attack the adjudication error, not the officer personally.
- Tie each ground to record evidence and legal authority.
- Preserve every factual concession and disputed amount clearly.
- Include alternate/subsidiary grounds without contradiction.
- Identify procedural violations: jurisdiction, limitation, natural justice, non-speaking order, non-consideration of reply/evidence, wrong section invoked, penalty mens rea where relevant.
- Include a case-law table: citation, forum, holding, applicability, limits/adverse treatment, verification status.
- Include an `ICAI-guide compliance check` in the final review checklist covering limitation proof, demand breakup, pre-deposit, SCN/reply/order mapping, order-beyond-SCN, additional evidence/grounds, case-law currency, and annexure discipline.
- End with explicit filing caveats and professional-review notes.
- Prefer “source-backed but not final” language for NotebookLM material until the underlying Act/rule/circular/judgment text has been independently checked.

## References to load as needed

- `references/auto-installation.md` — automatic dependency installation rules for agents; load when tools are missing or when setting up a new laptop.
- `references/drafting-playbook.md` — detailed drafting architecture and model output format.
- `references/research-protocol.md` — NotebookLM and caselaws-cli prompts/queries.
- `references/source-map.md` — authoritative source hierarchy and key GST appeal provisions.
- `references/templates.md` — appeal skeleton, grounds patterns, and case-law table.
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
