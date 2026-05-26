# GST Case Law Research CLI ⚖️

A highly responsive, modular, and CAPTCHA-proof Command Line Interface (CLI) to research Goods and Services Tax (GST) case laws, judicial precedents, and official circulars in India.

This tool is specifically designed to be integrated inside larger legal plugins, automated agents, or AI-powered appeal drafting systems by providing standard, machine-readable JSON interfaces alongside gorgeous human-readable terminals.

---

## ✨ Features

*   🔍 **Multi-Provider Search:** Query general search aggregators, CBIC portals, Indian Kanoon, or a NotebookLM knowledge-bank.
*   🛡️ **CAPTCHA Resilience:** Leverages search indexing aggregation to bypass government web CAPTCHAs and rate limits completely.
*   💾 **Result Caching:** Caches search results locally to allow instant, index-based fetching (e.g. `caselaws-cli get 1` to get the first result's text).
*   🤖 **Agent & Plugin Native:** Supports a `--json` output flag on all commands, yielding structured JSON for integration.
*   🎨 **Premium Terminal Visuals:** Styled with the `rich` python package, providing interactive progress indicators and clean, colorful tables.
*   ⚙️ **Local Configurations:** Easily set default parameters and API tokens.

---

## 🚀 Quick Start

### 1. Installation
Install the project in editable mode so it registers in your terminal path:
```bash
pip install -e .
```

### 2. Basic Search
Search for recent cases or circulars on any GST topic:
```bash
caselaws-cli search "Input Tax Credit GSTR-2A mismatch section 16(4)"
```

### 3. Retrieve Case Text
Get the full text of the top matched case by its index number:
```bash
caselaws-cli get 1
```

Or target a specific URL directly:
```bash
caselaws-cli get "https://indiankanoon.org/doc/13579246/"
```

### 4. Integration Mode (JSON)
To query the CLI programmatically from other plugins or scripts:
```bash
caselaws-cli search "Section 50 interest on gross tax" --json
```

### 5. NotebookLM Knowledge-Bank Search
If `notebooklm-py` is installed and authenticated, query your GST law NotebookLM notebook as another provider:
```bash
export NOTEBOOKLM_NOTEBOOK="<gst-law-notebook-id>"
caselaws-cli search "GST section 107 appeal limitation and pre-deposit" --provider notebooklm --json --limit 5
caselaws-cli get 1 --json
```

You can also persist the notebook ID:
```bash
caselaws-cli config set notebooklm_notebook_id "<gst-law-notebook-id>"
```

---

### 6. Full Appeal Research Packet
Run one command to generate a structured packet across NotebookLM, Indian Kanoon/search, CBIC/GST Council and adverse-risk queries:

```bash
caselaws-cli research "GST section 125 sign board penalty section 126 proportionality" \
  --facts-file facts-digest.md \
  --forum "first appeal under section 107" \
  --jurisdiction "Punjab" \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --limit 5 \
  --output research-packet.md

# Optional: fetch top full-text extracts per provider for verification
caselaws-cli research "GST natural justice non speaking order DRC-07" --fetch-top 1 --json
```

The packet labels discovery hits as `SEARCH_ONLY`; fetch and read full text before citing.


## 📁 Directory Structure

```text
caselaws-cli/
├── setup.py                 # Setuptools package configuration
├── pyproject.toml           # Modern package metadata
├── requirements.txt         # Package dependencies
├── README.md                # General readme
├── SKILL.md                 # Agent-discoverable skills description
├── cli_anything/            # Package namespace
│   └── caselaws/            # Main source folder
│       ├── main.py          # Click CLI Entrypoint & Subcommands
│       ├── config.py        # Config loader/saver
│       ├── providers/       # Data providers
│       │   ├── base.py      # Abstract Provider & CaseLawDocument schema
│       │   ├── search.py    # DuckDuckGo HTML aggregator
│       │   ├── kanoon.py    # Indian Kanoon API/Web crawler
│       │   ├── cbic.py      # CBIC Circular/Notification crawler
│       │   └── notebooklm.py # NotebookLM knowledge-bank bridge
│       └── utils/
│           └── term.py      # Rich tables and JSON output formatters
└── tests/                   # Pytest suite
```
