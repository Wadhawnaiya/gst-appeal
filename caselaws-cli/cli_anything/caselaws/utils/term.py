import json
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from cli_anything.caselaws.providers.base import CaseLawDocument

console = Console()

def print_error(message: str):
    """Prints an error message to stderr."""
    console.print(f"[bold red]Error:[/] {message}", style="red")

def print_success(message: str):
    """Prints a success message."""
    console.print(f"[bold green]✓[/] {message}", style="green")

def print_info(message: str):
    """Prints an informational message."""
    console.print(f"[bold blue]ℹ[/] {message}")

def print_json(data: Any):
    """Outputs data in clean, formatted JSON to stdout."""
    # We use python's standard json to print raw string to ensure machine-readability is perfect
    print(json.dumps(data, indent=2))

def display_search_results(documents: List[CaseLawDocument], query: str):
    """Renders search results in a highly premium, styled Rich table."""
    if not documents:
        console.print(f"\n[yellow]No results found for query:[/] '{query}'\n")
        return

    table = Table(
        title=f"GST Case Law Search Results for: '{query}'",
        title_style="bold cyan",
        show_header=True,
        header_style="bold magenta",
        border_style="dim blue",
        expand=True
    )

    table.add_column("#", style="dim", width=4, justify="center")
    table.add_column("Source", style="green", width=15)
    table.add_column("Title / Document Name", style="bold white")
    table.add_column("URL / Reference", style="dim blue", max_width=40, overflow="ellipsis")

    for idx, doc in enumerate(documents, 1):
        table.add_row(
            str(idx),
            doc.source,
            doc.title,
            doc.url
        )

        # Add snippet as a nested, slightly indented row for superb visual layout
        snippet_text = Text(f"   ↳ {doc.snippet}", style="italic dim yellow")
        table.add_row("", "", snippet_text, "")

    console.print(table)
    console.print(f"[dim cyan]Tip: Run 'caselaws-cli get <url_or_index>' to view full text.[/]\n")

def display_document(doc_title: str, content: str, url: str):
    """Renders the full text of a case/circular inside a premium panel."""
    # Strip double quotes or brackets for neat formatting
    header_text = Text(f"Document: {doc_title}", style="bold cyan")

    # We can try to render it as markdown if possible
    # Since court cases are unstructured, a scrollable panel works best
    panel = Panel(
        Markdown(content) if content.strip().startswith("#") or "judgment" in content.lower() else content,
        title=header_text,
        subtitle=f"Source: {url}",
        subtitle_align="right",
        border_style="bold blue",
        padding=(1, 2)
    )
    console.print(panel)
