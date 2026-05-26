# Agent Bootstrap from GitHub

Use this when a user gives an AI agent this repository link and wants the GST appeal drafting skill, `caselaws-cli`, and NotebookLM CLI installed inside the current project folder.

Repository:

```text
https://github.com/Wadhawnaiya/gst-appeal
```

## One command for Codex, Gemini CLI, Claude Code, OpenCode, Antigravity

From the folder where the user wants the tools installed, run:

```bash
python3 -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/Wadhawnaiya/gst-appeal/main/scripts/bootstrap_gst_appeal.py').read().decode())" --target .
```

If `curl` is preferred:

```bash
curl -fsSL https://raw.githubusercontent.com/Wadhawnaiya/gst-appeal/main/scripts/bootstrap_gst_appeal.py | python3 - --target .
```

This creates a folder-local install:

```text
.gst-appeal/repo                       # cloned gst-appeal repo
.gst-appeal/venvs/caselaws-cli          # local caselaws-cli venv
.gst-appeal/venvs/notebooklm-cli        # local notebooklm-py CLI venv
.gst-appeal/bin                         # wrapper commands
.agents/skills/gst-appeal-drafting      # universal agent skill copy
.codex/skills/gst-appeal-drafting       # Codex skill copy
GST_APPEAL_LOCAL_INSTALL.md             # local usage note
```

## Direct use after install

```bash
source .gst-appeal/env.sh
caselaws-cli --help
notebooklm auth check --test --json
gst-appeal-check --json
```

If NotebookLM auth is missing:

```bash
notebooklm login
export NOTEBOOKLM_NOTEBOOK="<your-gst-law-notebook-id>"
```

Then run a matter workflow:

```bash
gst-appeal-autodraft \
  --matter-dir ./matter-folder \
  --forum "first appeal under CGST Act section 107" \
  --jurisdiction "<State/High Court>" \
  --output-dir ./matter-folder/gst-appeal-workspace
```

## Bootstrap options

```bash
python3 scripts/bootstrap_gst_appeal.py --help
```

Useful options:

- `--target <folder>`: install into another folder.
- `--skip-playwright`: skip Chromium download for NotebookLM login.
- `--skip-notebooklm`: install only skill + caselaws-cli.
- `--dry-run --json`: show actions without downloading or writing.
- `--force`: replace an existing non-git `.gst-appeal/repo` folder.

## Agent instruction

When the user gives only the GitHub link, do not ask them to manually clone or install dependencies. Run the bootstrap command, then run `source .gst-appeal/env.sh` in subsequent shell commands and verify with `gst-appeal-check --json`.
