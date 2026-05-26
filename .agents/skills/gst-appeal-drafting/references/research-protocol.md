# Research Protocol

## NotebookLM prompts

Use the GST NotebookLM knowledge-bank for current law, circulars, notifications, and issue framing. Prefer exact prompts:

```text
You are assisting GST appeal drafting in India. For the issue below, extract only source-backed propositions from the notebook. Return a table with section/rule/circular/notification/case reference, date, short holding/proposition, source title, and any caveat/supersession risk.

Issue: <issue>
Facts: <brief facts>
Forum: <first appeal/GSTAT/High Court>
Jurisdiction: <state/high court if known>
```

```text
For these facts, identify appeal drafting points under GST law: jurisdiction, limitation, natural justice, evidence ignored, statutory interpretation, tax computation, interest, penalty, and relief. Keep facts separate from grounds.
```

NotebookLM CLI examples:

```bash
notebooklm auth check --test --json
notebooklm metadata --notebook "$NOTEBOOKLM_NOTEBOOK" --json
notebooklm ask --notebook "$NOTEBOOKLM_NOTEBOOK" --json --timeout 120 --prompt-file prompt.txt
caselaws-cli search "GST section 107 appeal limitation" --provider notebooklm --json --limit 5
```

If the installed CLI version does not support `--notebook`, set `NOTEBOOKLM_NOTEBOOK` or run `notebooklm use <id>` outside parallel workflows. Do not use `notebooklm ask --new` unless the user explicitly accepts losing the notebook's current server-side conversation.

## Case-law query patterns

Create multiple narrow searches:

```bash
caselaws-cli search "GST <issue> section <section> Supreme Court" --json --limit 5
caselaws-cli search "GST <issue> <jurisdiction High Court> natural justice non speaking order" --json --limit 5
caselaws-cli search "CBIC circular GST <issue>" --provider cbic --json --limit 5
caselaws-cli search "GST <issue> source-backed legal propositions" --provider notebooklm --json --limit 5
caselaws-cli get 1 --json
```

Query templates:

- `GST input tax credit GSTR-2A mismatch section 16 High Court`
- `GST section 74 suppression no mens rea penalty natural justice`
- `GST cancellation registration appeal limitation condonation section 107`
- `GST DRC-01 DRC-07 summary order non speaking order High Court`
- `GST pre deposit electronic credit ledger section 107 appeal`

## Reliability filter

For every candidate authority:

1. Read full text or official PDF.
2. Confirm court/forum, date, and final outcome.
3. Confirm it has not been overruled, stayed, or superseded by amendment/circular.
4. Confirm fact similarity.
5. Rank as binding / persuasive / adverse / distinguishable.
6. Quote only short excerpts; summarize the rest.

## Research packet minimum contents

- Issue summary and factual assumptions.
- Applicable provisions from NotebookLM knowledge-bank.
- Circulars/notifications/instructions.
- Case-law search log and selected authorities.
- NotebookLM source references with source IDs/titles where available.
- Adverse authorities and distinctions.
- Drafting implications: facts needed, best grounds, weak points, relief options.
