# Research Protocol

This protocol turns a bare user prompt such as “draft an appeal from this folder” into a complete research-and-drafting workbench. The agent should run it automatically; the user should not have to issue separate NotebookLM or case-law commands.

## Automated folder-to-appeal pipeline

```bash
python3 <skill-root>/scripts/check_environment.py --install --json
python3 <skill-root>/scripts/gst_appeal_autodraft.py \
  --matter-dir <matter-folder> \
  --forum "first appeal under CGST Act section 107" \
  --jurisdiction "<State/High Court if known>" \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --output-dir <matter-folder>/gst-appeal-workspace
```

Read these files before drafting:

```text
gst-appeal-workspace/facts-digest.md
gst-appeal-workspace/appeal-drafting-brief.md
gst-appeal-workspace/notebooklm-prompts/*.txt
gst-appeal-workspace/notebooklm-results/*.md
gst-appeal-workspace/caselaw-research/*.md
```

The autodraft script performs best-effort local extraction from text/Markdown/JSON/CSV/HTML/XML/PDF/DOCX and images (if `tesseract` exists). If OCR or extraction is incomplete, list those files under “Information required before filing”.

## NotebookLM prompts

Use the GST NotebookLM knowledge-bank for current law, circulars, notifications, issue framing and source-backed checklists. Always demand source titles/IDs/dates and uncertainty flags.

### Provision/form/circular matrix

```text
You are a senior Indian GST appellate practitioner. Use only source-backed material from this NotebookLM GST law notebook.

Task: create a provisions/forms/circulars matrix for drafting this GST appeal.

Forum: <first appeal/GSTAT/High Court>
Jurisdiction: <state/high court if known>
Issues:
- <issue 1>
- <issue 2>

Facts digest:
<facts digest>

Return columns: issue, section/rule/form/circular/notification, date/currentness caveat, exact proposition, source title/source id, how to plead it, what must be verified independently before filing. Mark uncertain items VERIFY BEFORE FILING.
```

### Grounds, risks and relief

```text
You are preparing grounds of appeal and written submissions for a GST appeal. Use only source-backed NotebookLM material and keep facts, grounds, arguments, and prayer separate.

Facts: <facts digest>
Issues: <issues>

Return: (1) strongest grounds, (2) alternate/subsidiary grounds, (3) adverse risks and distinctions, (4) evidence required for each ground, (5) relief/prayer options. Include source references for every legal proposition.
```

### Limitation, pre-deposit and filing defects

```text
Act as a GST appeal filing checklist reviewer. Use source-backed NotebookLM material.

Facts: <facts digest>
Forum: <forum>
Jurisdiction: <jurisdiction>

Return a filing checklist: limitation, condonation, admitted dues, disputed-tax/penalty pre-deposit, certified/uploaded order copy, APL form, authorization, fees, paper-book order, additional evidence, verification/signature, and portal caveats. Flag missing information.
```

### Case-law query plan

```text
Create a case-law research plan for caselaws-cli. Use the facts and issues below.

Facts: <facts digest>
Issues: <issues>
Jurisdiction: <jurisdiction>

Return prioritized search strings for Supreme Court, jurisdictional High Court, other High Courts, GSTAT/CESTAT analogies, CBIC circular/notification searches, and adverse authority searches. For each query, state why it matters and what result would be useful.
```

NotebookLM CLI examples:

```bash
notebooklm auth check --test --json
notebooklm metadata --notebook "$NOTEBOOKLM_NOTEBOOK" --json
notebooklm ask --notebook "$NOTEBOOKLM_NOTEBOOK" --json --timeout 120 --prompt-file prompt.txt
caselaws-cli search "GST section 107 appeal limitation" --provider notebooklm --json --limit 5
```

If the installed CLI version does not support `--notebook`, set `NOTEBOOKLM_NOTEBOOK` or run `notebooklm use <id>` outside parallel workflows. Do not use `notebooklm ask --new` unless the user explicitly accepts losing the notebook's current server-side conversation.

## Case-law and source query patterns

Prefer the integrated command:

```bash
caselaws-cli research "GST <issue> section <section> <fact pattern>" \
  --facts-file gst-appeal-workspace/facts-digest.md \
  --forum "first appeal under section 107" \
  --jurisdiction "<State/High Court>" \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --limit 5 \
  --output gst-appeal-workspace/caselaw-research/<issue>.md
```

The command generates a query plan across NotebookLM, Indian Kanoon/search, CBIC/GST Council and adverse-risk searches. For manual follow-up, use narrow queries:

```bash
caselaws-cli search "GST <issue> section <section> Supreme Court" --json --limit 5
caselaws-cli search "GST <issue> <jurisdiction High Court> natural justice non speaking order" --json --limit 5
caselaws-cli search "CBIC circular GST <issue>" --provider cbic --json --limit 5
caselaws-cli search "GST <issue> source-backed legal propositions" --provider notebooklm --json --limit 5
caselaws-cli get <index-or-url> --json
```

Query templates:

- `GST input tax credit GSTR-2A mismatch section 16 High Court`
- `GST section 74 suppression no mens rea penalty natural justice`
- `GST cancellation registration appeal limitation condonation section 107`
- `GST DRC-01 DRC-07 summary order non speaking order High Court`
- `GST pre deposit electronic credit ledger section 107 appeal`
- `GST section 125 sign board penalty section 126 proportionality`
- `GST order beyond show cause notice section 75 natural justice`

## Reliability filter

For every candidate authority:

1. Read full text or official PDF.
2. Confirm court/forum, date, parties, final outcome and exact holding.
3. Confirm it has not been overruled, stayed, reversed, superseded by amendment/circular, or distinguished on the point relied on.
4. Confirm fact similarity and forum relevance.
5. Rank as binding / persuasive / adverse / distinguishable.
6. Quote only short excerpts; summarize the rest.
7. Do not convert NotebookLM synthesis or search snippets into final citations without checking the underlying source.

## Research packet minimum contents

- Issue summary and factual assumptions.
- Applicable provisions, rules, forms and filing requirements from NotebookLM/official sources.
- Circulars/notifications/instructions and currentness caveats.
- Case-law search log and selected authorities.
- NotebookLM source references with source IDs/titles where available.
- Adverse authorities and distinctions.
- Drafting implications: facts needed, best grounds, weak points, relief options.
- Filing proof checklist: limitation, pre-deposit, authorization, certified/uploaded order, annexures, verification.
