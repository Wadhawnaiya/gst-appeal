"""Structured multi-provider GST appeal research helpers for caselaws-cli."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from cli_anything.caselaws.config import load_config
from cli_anything.caselaws.providers import get_provider
from cli_anything.caselaws.providers.base import CaseLawDocument


def _clean(text: str | None) -> str:
    return " ".join((text or "").strip().split())


def _clip(text: str | None, limit: int = 2500) -> str:
    value = (text or "").strip()
    return value if len(value) <= limit else value[:limit].rstrip() + "\n...[clipped]"


def _dedupe_queries(queries: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for item in queries:
        key = (item["provider"].lower(), _clean(item["query"]).lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def build_notebooklm_prompt(issue: str, *, facts: str = "", forum: str = "not specified", jurisdiction: str | None = None) -> str:
    """Build the source-backed prompt used for the NotebookLM law-bank provider."""
    return f"""You are assisting Indian GST appeal drafting. Use only source-backed material from the connected NotebookLM GST law knowledge-bank.

Issue / fact pattern:
{issue}

Forum: {forum or 'not specified'}
Jurisdiction: {jurisdiction or 'not specified'}
Facts supplied:
{facts or 'No detailed facts supplied.'}

Return a structured appeal research table with these columns:
1. Provision / rule / form / circular / notification / case reference
2. Date / currentness caveat
3. Exact legal proposition or filing requirement
4. How it applies to these facts
5. Appellant-friendly use
6. Department/adverse risk or distinction
7. Source title / source id / citation marker

Also identify missing filing facts: order communication date, demand breakup, admitted dues, disputed tax, pre-deposit, limitation, authorization, certified copy, and annexures. Mark every uncertain proposition as VERIFY BEFORE FILING."""


def build_research_queries(
    issue: str,
    *,
    jurisdiction: str | None = None,
    facts: str = "",
    forum: str = "not specified",
    include_notebooklm: bool = True,
) -> list[dict[str, str]]:
    """Return a deterministic multi-provider query plan for GST appeal research."""
    base = _clean(issue)
    gst_base = base if base.lower().startswith("gst ") else f"GST {base}"
    queries: list[dict[str, str]] = []

    if include_notebooklm:
        queries.append(
            {
                "provider": "notebooklm",
                "purpose": "Source-backed GST law-bank synthesis, provisions, filing requirements, risks",
                "query": build_notebooklm_prompt(base, facts=facts, forum=forum, jurisdiction=jurisdiction),
            }
        )

    if jurisdiction:
        queries.append(
            {
                "provider": "kanoon",
                "purpose": "Jurisdictional High Court / Indian Kanoon authorities",
                "query": f'{gst_base} "{jurisdiction}" High Court appeal natural justice non speaking order',
            }
        )
        queries.append(
            {
                "provider": "search",
                "purpose": "Jurisdiction-specific broad web discovery",
                "query": f'{gst_base} "{jurisdiction}" GST appeal High Court',
            }
        )

    queries.extend(
        [
            {
                "provider": "kanoon",
                "purpose": "Supreme Court and High Court case-law discovery",
                "query": f"{gst_base} Supreme Court High Court GST appeal",
            },
            {
                "provider": "search",
                "purpose": "Broad case-law and tribunal discovery",
                "query": f"{gst_base} GSTAT CESTAT High Court natural justice appeal",
            },
            {
                "provider": "cbic",
                "purpose": "Official circulars, notifications, instructions, rules and forms",
                "query": f"{gst_base} circular notification instruction rule form appeal",
            },
            {
                "provider": "search",
                "purpose": "Adverse / department-side risk discovery",
                "query": f"{gst_base} GST appeal dismissed adverse pre deposit limitation",
            },
        ]
    )
    return _dedupe_queries(queries)


def _doc_to_dict(doc: CaseLawDocument) -> dict[str, Any]:
    data = doc.to_dict()
    # Keep provider payloads machine-usable but avoid accidentally huge cached content in search rows.
    if data.get("content") and len(data["content"]) > 5000:
        data["content_preview"] = _clip(data["content"], 5000)
        data.pop("content", None)
    return data


def infer_provider_for_document(doc: CaseLawDocument) -> str:
    """Choose the provider most likely to fetch this document's full text."""
    source = (doc.source or "").lower()
    url = (doc.url or "").lower()
    if url.startswith("notebooklm://") or "notebooklm" in source:
        return "notebooklm"
    if "indiankanoon" in url or "kanoon" in source:
        return "kanoon"
    if "cbic" in url or "gstcouncil" in url or "cbic" in source or "gst council" in source:
        return "cbic"
    return "search"


def _search_provider(provider_name: str, query: str, config: dict[str, Any], limit: int) -> dict[str, Any]:
    provider = get_provider(provider_name, config)
    docs = provider.search(query, limit=limit)
    return {
        "provider": provider_name,
        "query": query,
        "ok": True,
        "count": len(docs),
        "results": [_doc_to_dict(doc) for doc in docs],
    }


def _fetch_full_text(doc: CaseLawDocument, config: dict[str, Any], max_chars: int) -> dict[str, Any]:
    provider_name = infer_provider_for_document(doc)
    payload = {"provider": provider_name, "title": doc.title, "url": doc.url, "source": doc.source}
    try:
        provider = get_provider(provider_name, config)
        content = provider.get_document(doc.url)
        payload.update({"ok": bool(content), "content": _clip(content or "", max_chars)})
    except Exception as exc:  # pragma: no cover - exercised via CLI/manual use more than unit tests
        payload.update({"ok": False, "error": str(exc)})
    return payload


def run_research(
    issue: str,
    *,
    facts: str = "",
    jurisdiction: str | None = None,
    forum: str = "not specified",
    notebook: str | None = None,
    limit: int = 5,
    fetch_top: int = 0,
    fetch_max_chars: int = 12000,
    include_notebooklm: bool = True,
) -> dict[str, Any]:
    """Run NotebookLM, case-law, and official-source searches and return a research packet."""
    config = load_config()
    if notebook:
        config = {**config, "notebooklm_notebook_id": notebook}

    query_plan = build_research_queries(
        issue,
        jurisdiction=jurisdiction,
        facts=facts,
        forum=forum,
        include_notebooklm=include_notebooklm,
    )
    searches: list[dict[str, Any]] = []
    fetched: list[dict[str, Any]] = []
    seen_fetch_urls: set[str] = set()

    for planned in query_plan:
        provider_name = planned["provider"]
        query = planned["query"]
        try:
            result = _search_provider(provider_name, query, config, limit)
            result["purpose"] = planned.get("purpose")
            searches.append(result)
            if fetch_top > 0:
                docs = [CaseLawDocument.from_dict(item) for item in result.get("results", []) if isinstance(item, dict)]
                for doc in docs[:fetch_top]:
                    if not doc.url or doc.url in seen_fetch_urls:
                        continue
                    seen_fetch_urls.add(doc.url)
                    fetched.append(_fetch_full_text(doc, config, fetch_max_chars))
        except Exception as exc:
            searches.append(
                {
                    "provider": provider_name,
                    "query": query,
                    "purpose": planned.get("purpose"),
                    "ok": False,
                    "error": str(exc),
                    "results": [],
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "issue": issue,
        "forum": forum,
        "jurisdiction": jurisdiction,
        "facts": facts,
        "query_plan": query_plan,
        "searches": searches,
        "fetched_documents": fetched,
        "verification_warnings": [
            "SEARCH_ONLY rows are discovery leads, not filing-ready citations.",
            "Use fetched full text / official PDF before marking an authority VERIFIED_FULL_TEXT.",
            "Confirm currentness: amendments, superseding circulars, stay/overruling, and jurisdictional binding value.",
            "NotebookLM output is source-backed synthesis, not independent verification; check underlying sources before filing.",
        ],
    }


def format_research_markdown(packet: dict[str, Any]) -> str:
    """Render a research packet as filing-team-friendly Markdown."""
    lines: list[str] = []
    lines.append("# GST Appeal Case-Law Research Packet")
    lines.append("")
    lines.append(f"Generated: {packet.get('generated_at')}")
    lines.append(f"Issue: {packet.get('issue')}")
    lines.append(f"Forum: {packet.get('forum') or 'not specified'}")
    if packet.get("jurisdiction"):
        lines.append(f"Jurisdiction: {packet.get('jurisdiction')}")
    lines.append("")
    lines.append("## Facts supplied")
    lines.append("")
    lines.append(packet.get("facts") or "No facts supplied.")
    lines.append("")
    lines.append("## Query plan")
    lines.append("")
    for idx, item in enumerate(packet.get("query_plan", []), 1):
        lines.append(f"{idx}. **{item.get('provider')}** — {item.get('purpose')}")
        lines.append(f"   Query/prompt: `{_clip(item.get('query'), 500)}`")
    lines.append("")
    lines.append("## Search results")
    lines.append("")
    for search in packet.get("searches", []):
        lines.append(f"### {search.get('provider')} — {search.get('purpose')}")
        lines.append("")
        if not search.get("ok"):
            lines.append(f"Error: {search.get('error')}")
            lines.append("")
            continue
        results = search.get("results") or []
        if not results:
            lines.append("No results returned.")
            lines.append("")
            continue
        for idx, doc in enumerate(results, 1):
            title = doc.get("title") or "Untitled"
            source = doc.get("source") or ""
            url = doc.get("url") or ""
            date = doc.get("date") or ""
            snippet = _clip((doc.get("snippet") or doc.get("content_preview") or "").replace("\n", " "), 500)
            lines.append(f"{idx}. **{title}** — {source} {date}")
            if url:
                lines.append(f"   URL: {url}")
            if snippet:
                lines.append(f"   Snippet: {snippet}")
            status = "NOTEBOOKLM_SYNTHESIS" if "NotebookLM" in source else "SEARCH_ONLY"
            lines.append(f"   Status: {status}; fetch/read full text before citing.")
        lines.append("")
    if packet.get("fetched_documents"):
        lines.append("## Fetched full-text verification extracts")
        lines.append("")
        for idx, fetched in enumerate(packet.get("fetched_documents", []), 1):
            lines.append(f"### {idx}. {fetched.get('title')} [{fetched.get('provider')}]")
            lines.append(f"URL: {fetched.get('url')}")
            if fetched.get("ok"):
                lines.append("")
                lines.append("```text")
                lines.append(_clip(fetched.get("content"), 2000))
                lines.append("```")
                lines.append("Status: FETCHED_EXTRACT — still verify currentness and final outcome.")
            else:
                lines.append(f"Fetch error: {fetched.get('error') or 'No content returned'}")
            lines.append("")
    lines.append("## Verification warnings")
    lines.append("")
    for warning in packet.get("verification_warnings", []):
        lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)


def facts_from_file(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")
