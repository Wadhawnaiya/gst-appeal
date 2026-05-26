# Skill: GST Case Law Research

A highly robust, modular CLI tool to research Goods and Services Tax (GST) case laws, judgments, and official CBIC circulars/notifications in India. Specifically designed to support larger plugins, agents, and appeal drafting engines with pristine, structured `--json` outputs and rich terminal rendering.

---

## 🛠️ CLI Installation

Install the CLI in editable mode inside your Python environment:
```bash
pip install -e .
```

This will register the global command `caselaws-cli`.

---

## 🚀 Capabilities & Command Schema

### 1. `search`
Search for relevant GST case laws, GSTAT rulings, or CBIC circulars.

*   **Syntax:** `caselaws-cli search "QUERY" [OPTIONS]`
*   **Options:**
    *   `-p, --provider [search|kanoon|cbic|notebooklm]`: The database provider to query. (Defaults to `search`).
        *   `search`: Free general search engine aggregator (highly robust fallback).
        *   `kanoon`: Targeted Indian Kanoon search (uses direct API if token is set, or scrapes free index).
        *   `cbic`: Targeted search focusing exclusively on official GST notifications and circulars.
        *   `notebooklm`: Queries the configured NotebookLM GST knowledge-bank through `notebooklm-py`.
    *   `-l, --limit INTEGER`: Max number of documents to return. (Defaults to 10).
    *   `--json`: Output results in pure, machine-readable JSON.

#### Standard JSON Response Schema:
```json
[
  {
    "title": "Commissioner of CGST vs. M/s Oasis Trading",
    "url": "https://indiankanoon.org/doc/12345678/",
    "source": "Indian Kanoon (API - Supreme Court)",
    "snippet": "The dispute relates to Input Tax Credit mismatch between GSTR-2A and GSTR-3B under CGST Act...",
    "date": "2024-03-12",
    "citation": "2024 (3) GSTL 123",
    "content": null,
    "metadata": {}
  }
]
```

---

### 2. `get`
Fetch the full text content of a case law or circular.

*   **Syntax:** `caselaws-cli get TARGET [OPTIONS]`
    *   `TARGET` can be either the direct URL of the document, or the 1-based index number of the document from the last executed search query.
*   **Options:**
    *   `--json`: Output full text in machine-readable JSON.

#### Standard JSON Response Schema:
```json
{
  "title": "Commissioner of CGST vs. M/s Oasis Trading",
  "url": "https://indiankanoon.org/doc/12345678/",
  "content": "Full judgment or circular text parsed and cleaned..."
}
```

---


### 3. `research`
Generate an issue-level GST appeal research packet across NotebookLM, Indian Kanoon/search, CBIC/GST Council and adverse-risk searches.

*   **Syntax:** `caselaws-cli research "ISSUE" [OPTIONS]`
*   **Options:**
    *   `--facts-file FILE`: Include facts/order summary in NotebookLM and query-planning prompts.
    *   `--forum TEXT`: Appeal forum/stage, e.g. first appeal, GSTAT, High Court.
    *   `--jurisdiction TEXT`: State or jurisdictional High Court.
    *   `--notebook TEXT`: NotebookLM notebook ID override.
    *   `--limit INTEGER`: Results per provider query.
    *   `--fetch-top INTEGER`: Fetch full-text extracts for top N results per provider.
    *   `--no-notebooklm`: Skip NotebookLM provider.
    *   `--output FILE`: Write Markdown or JSON packet.
    *   `--json`: Emit machine-readable packet.

Example:
```bash
caselaws-cli research "GST section 125 sign board penalty section 126 proportionality" \
  --facts-file facts-digest.md \
  --forum "first appeal under section 107" \
  --jurisdiction Punjab \
  --notebook "$NOTEBOOKLM_NOTEBOOK" \
  --limit 5 \
  --output research-packet.md
```

The packet labels raw discovery hits as `SEARCH_ONLY`. Fetch/read full text before relying on an authority in a filing.

---

### 4. `config`
Manage local configuration options.

*   **Commands:**
    *   `caselaws-cli config show`: Displays current settings (e.g., default limits, masked tokens).
    *   `caselaws-cli config set KEY VALUE`: Update a config value.
*   **Configurable Keys:**
    *   `indian_kanoon_token`: Set your official API token for direct Indian Kanoon database access.
    *   `notebooklm_notebook_id`: Set the GST NotebookLM notebook ID for knowledge-bank queries.
    *   `default_provider`: The provider to default to if `-p` is omitted (e.g. `search`, `kanoon`, `cbic`).
    *   `default_limit`: Standard integer count of results per query.

---

## 🧩 Integration Strategy for Plugins

This CLI serves as a fast, CAPTCHA-proof agent resource. Appeal-drafting plugins can programmatically query it to find grounds of defense:

1.  **Search Cases:** Query the CLI:
    ```bash
    caselaws-cli search "Input tax credit mismatch section 16(4)" --json
    ```
2.  **Query NotebookLM:** Ask the connected GST law-bank for source-backed legal propositions:
    ```bash
    caselaws-cli search "GST section 107 limitation pre deposit" --provider notebooklm --json
    ```
3.  **Extract Text:** Fetch the full judgment/source text of the top matching result:
    ```bash
    caselaws-cli get 1 --json
    ```
4.  **Generate Issue Packets:** Use `caselaws-cli research` for each inferred appeal issue; it creates a repeatable query plan, NotebookLM synthesis and official-source/case-law leads.
5.  **Feed to Drafting LLM:** Feed the returned case/source content into the drafting engine, marking search-only or synthesis-only material as `VERIFY BEFORE FILING`.
