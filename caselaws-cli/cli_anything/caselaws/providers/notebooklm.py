import asyncio
import os
import re
from typing import List, Optional, Dict, Any
from cli_anything.caselaws.providers.base import BaseProvider, CaseLawDocument

class NotebookLmProvider(BaseProvider):
    """Search provider using NotebookLM API via notebooklm-py."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.notebook_id = (
            config.get("notebooklm_notebook_id", "").strip() or
            os.environ.get("NOTEBOOKLM_NOTEBOOK", "").strip()
        )

    def search(self, query: str, limit: int = 10) -> List[CaseLawDocument]:
        """Queries NotebookLM for the query, returns the synthesized answer and cited sources."""
        try:
            return asyncio.run(self._search_async(query, limit))
        except Exception as e:
            # Re-raise with a clear message
            raise RuntimeError(f"NotebookLM search failed: {str(e)}")

    @staticmethod
    def _attr(obj: Any, *names: str, default: Any = None) -> Any:
        """Return the first present attribute/key from SDK objects or dict payloads."""
        for name in names:
            if isinstance(obj, dict) and name in obj:
                return obj[name]
            value = getattr(obj, name, None)
            if value is not None:
                return value
        return default

    @staticmethod
    def _clip(text: str, limit: int = 300) -> str:
        text = (text or "").strip()
        return text[:limit] + "..." if len(text) > limit else text

    async def _search_async(self, query: str, limit: int) -> List[CaseLawDocument]:
        try:
            from notebooklm import NotebookLMClient
        except ImportError:
            raise ImportError(
                "The 'notebooklm-py' library is required to use this provider. "
                "Install it with: pip install 'notebooklm-py[browser]'"
            )

        try:
            # Initialize client from saved authentication
            async with NotebookLMClient.from_storage() as client:
                notebook_id = self.notebook_id

                # If notebook_id is not configured, try to automatically discover it
                if not notebook_id:
                    notebooks = await client.notebooks.list()
                    if not notebooks:
                        raise ValueError(
                            "No NotebookLM notebooks found. Please create a notebook "
                            "at https://notebooklm.google.com/ and add your sources first."
                        )
                    elif len(notebooks) == 1:
                        notebook_id = self._attr(notebooks[0], "id")
                    else:
                        notebook_list = "\n".join([
                            f"- {self._attr(n, 'title', default='Untitled')} (ID: {self._attr(n, 'id', default='unknown')})"
                            for n in notebooks
                        ])
                        raise ValueError(
                            "Multiple notebooks found. Please configure a default notebook ID "
                            "in your CLI settings or set the NOTEBOOKLM_NOTEBOOK environment variable.\n"
                            f"Available notebooks:\n{notebook_list}"
                        )

                # Fetch sources in the notebook to map citations to titles and URLs
                sources_map = {}
                try:
                    sources_list = await client.sources.list(notebook_id)
                    sources_map = {
                        self._attr(src, "id", "source_id"): src
                        for src in sources_list
                        if self._attr(src, "id", "source_id")
                    }
                except Exception:
                    # Non-fatal: list sources failure won't block querying the notebook
                    pass

                # Query the notebook
                result = await client.chat.ask(notebook_id, query)
                answer = self._attr(result, "answer", "text", "content", default="")
                if not answer:
                    raise ValueError("NotebookLM returned an empty answer.")

                documents = []

                # 1. First document: Synthesis / Answer
                synthesis_url = f"notebooklm://{notebook_id}/synthesis"
                doc_title = f"NotebookLM Synthesis: {query[:50]}"
                if len(query) > 50:
                    doc_title += "..."

                synthesis_doc = CaseLawDocument(
                    title=doc_title,
                    url=synthesis_url,
                    source="NotebookLM (Synthesis)",
                    snippet=self._clip(answer),
                    content=answer,
                    metadata={"notebook_id": notebook_id, "query": query}
                )
                documents.append(synthesis_doc)

                # 2. Cite references as additional documents
                seen_citations = set()
                references = self._attr(result, "references", "sources", default=[]) or []
                if references:
                    for ref in references:
                        source_id = self._attr(ref, "source_id", "sourceId", "id")
                        if not source_id or source_id in seen_citations:
                            continue

                        seen_citations.add(source_id)
                        if len(documents) >= limit:
                            break

                        # Resolve source details
                        source_obj = sources_map.get(source_id)
                        title = self._attr(source_obj, "title", default=None) or self._attr(ref, "title", default=None) or f"Cited Source ({source_id})"
                        url = f"notebooklm://{notebook_id}/source/{source_id}"

                        # Use actual URL from source object if available and it's a web link
                        original_url = self._attr(source_obj, "url", default=None) if source_obj else None

                        snippet = self._attr(ref, "cited_text", "citedText", "text", default=None) or f"Reference inside source: '{title}'"

                        citation_doc = CaseLawDocument(
                            title=title,
                            url=url,
                            source="NotebookLM (Citation)",
                            snippet=self._clip(snippet),
                            citation=f"Citation #{self._attr(ref, 'citation_number', 'citationNumber')}" if self._attr(ref, "citation_number", "citationNumber") else None,
                            metadata={
                                "notebook_id": notebook_id,
                                "source_id": source_id,
                                "original_url": original_url
                            }
                        )
                        documents.append(citation_doc)

                return documents

        except Exception as e:
            # Detect authentication issues
            err_str = str(e).lower()
            if "auth" in err_str or "login" in err_str or "cookie" in err_str:
                raise RuntimeError(
                    "NotebookLM authentication failed. Please run 'notebooklm login' "
                    "in your terminal to authenticate with your Google account."
                ) from e
            raise

    def get_document(self, url: str) -> Optional[str]:
        """Retrieves either the cached synthesis or the full text of a source from NotebookLM."""
        # Check if it is a synthesis URL
        if "synthesis" in url:
            try:
                # Retrieve from local results cache
                from cli_anything.caselaws.main import load_from_cache
                cached_docs = load_from_cache()
                for doc in cached_docs:
                    if doc.url == url and doc.content:
                        return doc.content
            except Exception:
                pass
            return "Unable to retrieve synthesis content from cache. Please run search again."

        # Check if it's a notebooklm source URL
        match = re.match(r"notebooklm://([^/]+)/source/([^/]+)", url)
        if match:
            notebook_id, source_id = match.group(1), match.group(2)
            try:
                return asyncio.run(self._get_source_content_async(notebook_id, source_id))
            except Exception as e:
                return f"Failed to retrieve source content from NotebookLM: {str(e)}"

        return None

    async def _get_source_content_async(self, notebook_id: str, source_id: str) -> str:
        from notebooklm import NotebookLMClient
        async with NotebookLMClient.from_storage() as client:
            fulltext = await client.sources.get_fulltext(notebook_id, source_id)
            return self._attr(fulltext, "content", "text", "markdown", default=str(fulltext))
