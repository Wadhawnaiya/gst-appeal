import os
import json
import click
from pathlib import Path
from typing import List, Dict, Any

from cli_anything.caselaws.config import load_config, update_config_key, CONFIG_DIR
from cli_anything.caselaws.providers import get_provider
from cli_anything.caselaws.providers.base import CaseLawDocument
from cli_anything.caselaws.research import facts_from_file, format_research_markdown, run_research
from cli_anything.caselaws.utils.term import (
    console,
    print_error,
    print_success,
    print_info,
    print_json,
    display_search_results,
    display_document
)

CACHE_FILE = CONFIG_DIR / "last_results.json"

def save_to_cache(documents: List[CaseLawDocument]):
    """Caches the last search results to enable index-based document retrieval."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        serialized = [doc.to_dict() for doc in documents]
        with open(CACHE_FILE, "w") as f:
            json.dump(serialized, f, indent=4)
    except Exception:
        pass

def load_from_cache() -> List[CaseLawDocument]:
    """Loads the last search results from local cache."""
    if not CACHE_FILE.exists():
        return []
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            return [CaseLawDocument.from_dict(item) for item in data]
    except Exception:
        return []


@click.group()
def main():
    """GST Appeal Research CLI - A powerful tool to search Indian GST case laws and circulars.

    Perfectly structured to integrate with larger plugins and appeal drafting agents.
    """
    pass


@main.command(name="search")
@click.argument("query", required=True)
@click.option("--provider", "-p", type=click.Choice(["search", "kanoon", "cbic", "notebooklm"]), help="Search provider to use.")
@click.option("--limit", "-l", type=int, help="Limit the number of results.")
@click.option("--json", "json_mode", is_flag=True, help="Output results in machine-readable JSON.")
def search_cmd(query: str, provider: str, limit: int, json_mode: bool):
    """Search for relevant GST case laws, GSTAT rulings, or CBIC circulars."""
    config = load_config()

    selected_provider = provider or config.get("default_provider", "search")
    selected_limit = limit or config.get("default_limit", 10)

    if not json_mode:
        print_info(f"Searching using provider: [bold cyan]{selected_provider}[/] (Limit: {selected_limit})...")

    try:
        provider_instance = get_provider(selected_provider, config)

        # Display rich spinner for interactive CLI feel
        if not json_mode:
            with console.status("[bold green]Querying legal databases...", spinner="dots"):
                results = provider_instance.search(query, limit=selected_limit)
        else:
            results = provider_instance.search(query, limit=selected_limit)

        save_to_cache(results)

        if json_mode:
            print_json([doc.to_dict() for doc in results])
        else:
            display_search_results(results, query)

    except Exception as e:
        if json_mode:
            print_json({"error": str(e)})
        else:
            print_error(str(e))


@main.command(name="research")
@click.argument("issue", required=True)
@click.option("--facts-file", type=click.Path(exists=True, dir_okay=False), help="Facts / order summary file to include in the research prompts.")
@click.option("--forum", default="not specified", show_default=True, help="Appeal forum/stage, e.g. first appeal, GSTAT, High Court.")
@click.option("--jurisdiction", help="State or jurisdictional High Court, if known.")
@click.option("--notebook", help="NotebookLM notebook ID; overrides config/env for this run.")
@click.option("--limit", "limit", type=int, default=5, show_default=True, help="Results per provider query.")
@click.option("--fetch-top", type=int, default=0, show_default=True, help="Fetch full text for top N results per provider for verification extracts.")
@click.option("--no-notebooklm", is_flag=True, help="Skip NotebookLM provider and run only case-law / official-source searches.")
@click.option("--output", type=click.Path(dir_okay=False), help="Write packet to this file.")
@click.option("--json", "json_mode", is_flag=True, help="Output packet as machine-readable JSON.")
def research_cmd(issue: str, facts_file: str, forum: str, jurisdiction: str, notebook: str, limit: int, fetch_top: int, no_notebooklm: bool, output: str, json_mode: bool):
    """Run a structured appeal research packet across NotebookLM, case-law, and official sources."""
    try:
        facts = facts_from_file(facts_file)
        packet = run_research(
            issue,
            facts=facts,
            forum=forum,
            jurisdiction=jurisdiction,
            notebook=notebook,
            limit=limit,
            fetch_top=fetch_top,
            include_notebooklm=not no_notebooklm,
        )
        rendered = json.dumps(packet, indent=2) if json_mode else format_research_markdown(packet)
        if output:
            Path(output).write_text(rendered, encoding="utf-8")
        if json_mode:
            print_json(packet)
        else:
            click.echo(rendered)
    except Exception as e:
        if json_mode:
            print_json({"error": str(e)})
        else:
            print_error(str(e))



@main.command(name="get")
@click.argument("target", required=True)
@click.option("--json", "json_mode", is_flag=True, help="Output content in machine-readable JSON.")
def get_cmd(target: str, json_mode: bool):
    """Retrieve full text content of a case law or circular.

    TARGET can be either a URL or the 1-based index number from the last 'search' command.
    """
    config = load_config()
    url = target
    doc_title = "Document"
    provider_name = "search"

    # Check if target is a cached index number
    if target.isdigit():
        cached_docs = load_from_cache()
        idx = int(target) - 1
        if 0 <= idx < len(cached_docs):
            doc = cached_docs[idx]
            url = doc.url
            doc_title = doc.title
            # Use cached provider if available
            if "Kanoon" in doc.source:
                provider_name = "kanoon"
            elif "CBIC" in doc.source:
                provider_name = "cbic"
            elif "NotebookLM" in doc.source:
                provider_name = "notebooklm"
        else:
            if json_mode:
                print_json({"error": f"Index {target} out of range of last search results."})
            else:
                print_error(f"Index {target} is out of range. Run 'search' again to refresh cache.")
            return

    if not json_mode:
        print_info(f"Fetching full text from URL: [dim blue]{url}[/]...")

    try:
        provider_instance = get_provider(provider_name, config)

        if not json_mode:
            with console.status("[bold green]Fetching document content...", spinner="dots"):
                content = provider_instance.get_document(url)
        else:
            content = provider_instance.get_document(url)

        if not content:
            raise ValueError("Failed to retrieve or parse document content.")

        if json_mode:
            print_json({
                "title": doc_title,
                "url": url,
                "content": content
            })
        else:
            display_document(doc_title, content, url)

    except Exception as e:
        if json_mode:
            print_json({"error": str(e)})
        else:
            print_error(str(e))


@click.group(name="config")
def config_group():
    """Manage CLI settings and credentials (such as Indian Kanoon API tokens)."""
    pass

@config_group.command(name="show")
def config_show():
    """Display current configuration parameters."""
    config = load_config()
    # Mask token for security
    masked_config = config.copy()
    if masked_config.get("indian_kanoon_token"):
        token = masked_config["indian_kanoon_token"]
        masked_config["indian_kanoon_token"] = token[:4] + "*" * (len(token) - 4) if len(token) > 4 else "****"

    print_success("Current configuration:")
    print_json(masked_config)

@config_group.command(name="set")
@click.argument("key", required=True)
@click.argument("value", required=True)
def config_set(key: str, value: str):
    """Set a configuration value.

    Keys: indian_kanoon_token, notebooklm_notebook_id, default_provider, default_limit, user_agent
    """
    config = load_config()
    if key not in config:
        print_error(f"Invalid config key '{key}'. Available: {list(config.keys())}")
        return

    # Convert limit to int if needed
    if key == "default_limit":
        try:
            value = int(value)
        except ValueError:
            print_error("default_limit must be an integer.")
            return

    update_config_key(key, value)
    print_success(f"Config key '[bold cyan]{key}[/]' updated successfully.")

# Register subcommands
main.add_command(config_group)

if __name__ == '__main__':
    main()
