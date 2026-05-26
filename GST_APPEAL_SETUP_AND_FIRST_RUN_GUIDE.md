# GST Appeal Research/Drafting Setup + First-Run Guide

This guide explains how to set up and run the **3 connected parts** in this workspace:

1. **GST appeal drafting skill** — `.agents/skills/gst-appeal-drafting/`
2. **Case-law research CLI** — `caselaws-cli/`
3. **NotebookLM / notebooklm-py knowledge-bank integration** — `notebooklm` CLI and `caselaws-cli --provider notebooklm`

The intended flow is:

```text
Your GST facts/order summary
  -> GST appeal drafting skill
  -> NotebookLM knowledge-bank for source-backed law/provisions
  -> caselaws-cli for cases/circulars
  -> research packet
  -> appeal draft / grounds / written submissions
```

> Filing warning: outputs are drafting/research aids only. Verify current law, full judgment text, limitation, pre-deposit, portal requirements, and have a CA/advocate review before filing.

---

## 0. Folder map

Run commands from:

```bash
cd /home/wadhawaniya/gst-appeal
```

Important paths:

```text
.agents/skills/gst-appeal-drafting/                 # Codex skill
.agents/skills/gst-appeal-drafting/scripts/         # setup/check/research scripts
caselaws-cli/                                       # GST case-law CLI source
caselaws-cli/.venv/bin/caselaws-cli                 # bundled caselaws CLI, if installed
caselaws-cli/.venv/bin/notebooklm                   # bundled NotebookLM CLI
GST_APPEAL_SETUP_AND_FIRST_RUN_GUIDE.md             # this guide
demo/first-run.sh                                   # safe first-run demo
demo/first-run-facts.md                             # demo facts input
demo/output/                                        # generated demo outputs
```

---

## 1. Component A — GST appeal drafting skill

### What it does

The skill tells Codex how to draft/review/research Indian GST appeals using:

- statutory GST appeal drafting discipline,
- ICAI-style filing checks,
- NotebookLM knowledge-bank extraction,
- local case-law/circular research through `caselaws-cli`, and
- a research packet before drafting.

### How to use it in Codex

Use natural language like:

```text
Use gst-appeal-drafting. Draft APL-01 grounds from this order and facts.
```

or:

```text
Research GST natural justice non-speaking order under section 74 using my GST appeal drafting skill.
```

The skill should load from:

```text
/home/wadhawaniya/gst-appeal/.agents/skills/gst-appeal-drafting/SKILL.md
```

### Verify skill scripts compile

```bash
python3 -m py_compile .agents/skills/gst-appeal-drafting/scripts/*.py
```

---

## 2. Component B — caselaws-cli

### What it does

`caselaws-cli` searches GST case-law and official materials through providers:

| Provider | Purpose |
|---|---|
| `search` | Broad web/search-index discovery |
| `kanoon` | Indian Kanoon search/get where available |
| `cbic` | CBIC circular/notification-oriented search |
| `notebooklm` | Your NotebookLM GST knowledge-bank through `notebooklm-py` |

### Use existing bundled venv

This workspace already has a Python venv under `caselaws-cli/.venv`. Prefer it for repeatable local runs:

```bash
cd /home/wadhawaniya/gst-appeal/caselaws-cli
.venv/bin/python -m cli_anything.caselaws.main --help
.venv/bin/python -m pytest -q
```

### Optional: expose wrapper in PATH

If you want `caselaws-cli` globally in this shell:

```bash
export PATH="$HOME/.local/bin:/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin:$PATH"
```

If needed, install/update dependencies:

```bash
cd /home/wadhawaniya/gst-appeal/caselaws-cli
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .
```

### Basic case-law search

```bash
cd /home/wadhawaniya/gst-appeal/caselaws-cli
.venv/bin/python -m cli_anything.caselaws.main search \
  "GST natural justice non speaking order section 74" \
  --json --limit 3
```

### Fetch full text from last search

After a search, fetch result 1:

```bash
cd /home/wadhawaniya/gst-appeal/caselaws-cli
.venv/bin/python -m cli_anything.caselaws.main get 1 --json
```

Do not cite a case from a snippet alone. Use `get` or an official PDF/full text before relying on it.

### Configure caselaws-cli

Show config:

```bash
caselaws-cli config show
```

Set default limit:

```bash
caselaws-cli config set default_limit 5
```

Set NotebookLM notebook ID for the `notebooklm` provider:

```bash
caselaws-cli config set notebooklm_notebook_id "<your-gst-law-notebook-id>"
```

---

## 3. Component C — NotebookLM / notebooklm-py knowledge-bank

### What it does

NotebookLM is your private GST law knowledge-bank. `notebooklm-py` gives a local `notebooklm` CLI so scripts can ask your notebook and receive source-backed answers.

### Check NotebookLM CLI

From the project root:

```bash
/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm --version
```

Expected shape:

```text
NotebookLM CLI, version 0.5.0
```

### Authenticate NotebookLM

Authentication requires a human browser sign-in:

```bash
/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm login
```

Then verify:

```bash
/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm auth check --test --json
```

If auth is missing, you will see something like:

```json
{
  "error": true,
  "code": "AUTH_REQUIRED",
  "message": "Auth not found. Run 'notebooklm login' first."
}
```

### Set the GST law notebook

Set it for the current shell:

```bash
export NOTEBOOKLM_NOTEBOOK="<your-gst-law-notebook-id>"
```

Optional persistent CLI config:

```bash
caselaws-cli config set notebooklm_notebook_id "$NOTEBOOKLM_NOTEBOOK"
```

### Test metadata

```bash
/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm metadata \
  --notebook "$NOTEBOOKLM_NOTEBOOK" --json
```

### Ask NotebookLM directly

Create a prompt:

```bash
cat > /tmp/gst_prompt.txt <<'EOF'
You are assisting Indian GST appeal drafting. For section 107 appeal limitation and pre-deposit, return only source-backed propositions with source title/date and caveats.
EOF
```

Ask:

```bash
/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm ask \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --json --timeout 120 \
  --prompt-file /tmp/gst_prompt.txt
```

### Ask NotebookLM through caselaws-cli

```bash
cd /home/wadhawaniya/gst-appeal/caselaws-cli
.venv/bin/python -m cli_anything.caselaws.main search \
  "GST section 107 appeal limitation pre deposit source-backed propositions" \
  --provider notebooklm --json --limit 5
```

Then fetch the synthesis/source result:

```bash
.venv/bin/python -m cli_anything.caselaws.main get 1 --json
```

---

## 4. One-command environment check

From project root:

```bash
cd /home/wadhawaniya/gst-appeal
python3 .agents/skills/gst-appeal-drafting/scripts/check_environment.py --json
```

If a tool is missing and you want auto-install/update:

```bash
python3 .agents/skills/gst-appeal-drafting/scripts/check_environment.py --install --json
```

Manual installer:

```bash
python3 .agents/skills/gst-appeal-drafting/scripts/install_dependencies.py --only all
```

Install only one:

```bash
python3 .agents/skills/gst-appeal-drafting/scripts/install_dependencies.py --only caselaws
python3 .agents/skills/gst-appeal-drafting/scripts/install_dependencies.py --only notebooklm
```

---

## 5. Generate a full GST research packet

Prepare facts in a Markdown file. Minimal example:

```markdown
# Facts

- Forum: first appeal under section 107.
- Issue: order under section 74 confirmed demand without discussing reply/evidence.
- Jurisdiction: Gujarat.
- Tax period: FY 2021-22.
- Relief needed: set aside or remand for fresh adjudication after hearing.
```

Run:

```bash
cd /home/wadhawaniya/gst-appeal
python3 .agents/skills/gst-appeal-drafting/scripts/gst_appeal_research.py \
  --issue "natural justice non-speaking order section 74" \
  --facts-file demo/first-run-facts.md \
  --jurisdiction Gujarat \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --case-limit 3 \
  --timeout 120 \
  --output demo/output/research-packet.md
```

Open the packet:

```bash
sed -n '1,220p' demo/output/research-packet.md
```

Expected behavior:

- If NotebookLM is authenticated and `NOTEBOOKLM_NOTEBOOK` is set, the packet includes NotebookLM synthesis/source references.
- If NotebookLM is not authenticated, the packet still runs case-law search and clearly reports the NotebookLM auth issue.

---

## 6. First-run demo

Run the included demo:

```bash
cd /home/wadhawaniya/gst-appeal
bash demo/first-run.sh
```

The demo will:

1. Print resolved tool paths.
2. Run environment checks.
3. Run a broad `caselaws-cli` search.
4. Generate a GST appeal research packet from `demo/first-run-facts.md`.
5. Save outputs to `demo/output/`.
6. Explain the NotebookLM login step if auth is missing.

Demo output files:

```text
demo/output/environment-check.json
demo/output/caselaws-search.json
demo/output/research-packet.md
```

To rerun after NotebookLM login:

```bash
export NOTEBOOKLM_NOTEBOOK="<your-gst-law-notebook-id>"
bash demo/first-run.sh
```

---

## 7. Recommended daily workflow

### Step 1 — Start with facts

Create a matter file:

```bash
cp demo/first-run-facts.md matter-facts.md
nano matter-facts.md
```

Include:

- order number/date/communication date,
- forum/stage,
- tax period,
- demand breakup,
- disputed issues,
- SCN allegations,
- reply/evidence filed,
- order findings,
- limitation/pre-deposit details,
- relief needed.

### Step 2 — Generate research packet

```bash
python3 .agents/skills/gst-appeal-drafting/scripts/gst_appeal_research.py \
  --issue "<issue + section + fact pattern>" \
  --facts-file matter-facts.md \
  --jurisdiction "<state/high court>" \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --output matter-research-packet.md
```

### Step 3 — Ask Codex to draft

```text
Use gst-appeal-drafting. Read matter-facts.md and matter-research-packet.md. Draft APL-01 statement of facts, grounds, written submissions, prayer, case-law table, and filing checklist. Mark all unverified authorities VERIFY BEFORE FILING.
```

### Step 4 — Verify before filing

Checklist:

- Full text read for every case relied upon.
- Binding/persuasive/adverse status classified.
- Limitation computed from communication date.
- Condonation need checked.
- Pre-deposit/admitted dues checked.
- SCN → reply/evidence → order finding → error mapping complete.
- Order-beyond-SCN checked.
- Annexures indexed and paginated.
- Final professional review completed.

---

## 8. Troubleshooting

### `notebooklm` says auth missing

Run:

```bash
/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm login
```

Then:

```bash
/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm auth check --test --json
```

### `NOTEBOOKLM_NOTEBOOK` not set

Set it:

```bash
export NOTEBOOKLM_NOTEBOOK="<your-gst-law-notebook-id>"
```

Or configure caselaws-cli:

```bash
caselaws-cli config set notebooklm_notebook_id "<your-gst-law-notebook-id>"
```

### `caselaws-cli` not found

Use module form:

```bash
cd /home/wadhawaniya/gst-appeal/caselaws-cli
.venv/bin/python -m cli_anything.caselaws.main --help
```

Or add wrappers to PATH:

```bash
export PATH="$HOME/.local/bin:/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin:$PATH"
```

### Search returns weak results

Use narrower queries:

```bash
caselaws-cli search "GST DRC-07 non speaking order reply not considered Gujarat High Court" --json --limit 5
caselaws-cli search "GST section 74 natural justice personal hearing reply evidence not considered" --json --limit 5
caselaws-cli search "CBIC circular GST adjudication personal hearing natural justice" --provider cbic --json --limit 5
```

### Do not cite from search snippets

Always fetch/read full text:

```bash
caselaws-cli get 1 --json
```

Mark as `SEARCH_ONLY` until verified.
