# Automatic CLI Installation for Agents

When a user asks to use the GST Appeal Drafter plugin, an AI agent should not stop and ask the user to manually install dependencies. It should run the installer itself unless the environment forbids downloads or writes.

## One-command install

```bash
python3 <skill-root>/scripts/install_dependencies.py --only all
```

This installs, in user space:

- `caselaws-cli` from `https://github.com/Wadhawnaiya/caselaws-cli`
- `notebooklm` CLI from `notebooklm-py[browser]`

Locations:

```text
~/.local/share/gst-appeal-drafter/src/caselaws-cli
~/.local/share/gst-appeal-drafter/venvs/caselaws-cli
~/.local/share/gst-appeal-drafter/venvs/notebooklm-cli
~/.local/bin/caselaws-cli
~/.local/bin/notebooklm
```

If `~/.local/bin` is not in PATH, agents should either call the wrappers by absolute path or export:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Install only one dependency

```bash
python3 <skill-root>/scripts/install_dependencies.py --only caselaws
python3 <skill-root>/scripts/install_dependencies.py --only notebooklm
```

## NotebookLM authentication

The installer can download and install NotebookLM CLI automatically, but Google authentication requires a human browser login.

After install, run:

```bash
notebooklm auth check --test --json
```

If authentication is missing/stale:

```bash
notebooklm login
```

Then set the GST law notebook:

```bash
export NOTEBOOKLM_NOTEBOOK="<gst-law-notebook-id>"
```

The local caselaws repo may already contain a usable NotebookLM CLI at:

```text
/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm
```

The skill scripts detect this automatically. Override tool discovery with:

```bash
export CASELAWS_REPO=/home/wadhawaniya/gst-appeal/caselaws-cli
export CASELAWS_CLI="/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/python -m cli_anything.caselaws.main"
export NOTEBOOKLM_CLI=/home/wadhawaniya/gst-appeal/caselaws-cli/.venv/bin/notebooklm
```

## Agent behavior rule

When this plugin is invoked:

1. Run `<skill-root>/scripts/check_environment.py --json`.
2. If `caselaws-cli` or `notebooklm` is missing, run `install_dependencies.py --only all` automatically.
3. Re-run `check_environment.py --json`.
4. If only NotebookLM authentication is missing, run `notebooklm login` or report that browser sign-in is required.
5. Continue drafting/research once tools are available.

Do not cite case-law snippets as final authorities; fetch full text with `caselaws-cli get` before relying on a case.
