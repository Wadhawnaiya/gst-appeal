import requests
from typing import List, Optional, Dict, Any
from cli_anything.caselaws.providers.base import BaseProvider, CaseLawDocument
from cli_anything.caselaws.providers.search import SearchAggregator

class IndianKanoonProvider(BaseProvider):
    """Provider specifically targeting Indian Kanoon. Supports both the official API and a search aggregator fallback."""

    def search(self, query: str, limit: int = 10) -> List[CaseLawDocument]:
        token = self.config.get("indian_kanoon_token", "").strip()

        if not token:
            # Fallback: Query Indian Kanoon via domain-restricted web search
            aggregator = SearchAggregator(self.config)
            restricted_query = f"site:indiankanoon.org {query}"
            docs = aggregator.search(restricted_query, limit=limit)

            # Label properly as coming from Kanoon Scraper
            for doc in docs:
                doc.source = "Indian Kanoon (Web)"
            return docs

        # Official API execution
        url = "https://api.indiankanoon.org/search/"
        headers = {
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "User-Agent": self.user_agent
        }
        params = {
            "formInput": query,
            "pagenum": 0
        }

        try:
            # Note: Indian Kanoon API handles formInput as GET or POST
            response = requests.post(url, data=params, headers=headers, timeout=15)
            if response.status_code != 200:
                response = requests.get(url, params=params, headers=headers, timeout=15)

            if response.status_code != 200:
                # Fallback to search if API is down/rate-limited
                aggregator = SearchAggregator(self.config)
                return aggregator.search(f"site:indiankanoon.org {query}", limit=limit)

            data = response.json()
            results = data.get("results", [])

            documents = []
            for item in results:
                if len(documents) >= limit:
                    break

                tid = item.get("tid")
                title = item.get("title", "Untitled Document")
                source = item.get("docSource", "Indian Kanoon")
                headline = item.get("headline", "")
                publish_date = item.get("publishdate", "")

                # Construct official URL
                doc_url = f"https://indiankanoon.org/doc/{tid}/" if tid else ""

                doc = CaseLawDocument(
                    title=title,
                    url=doc_url,
                    source=f"Indian Kanoon (API - {source})",
                    snippet=headline,
                    date=publish_date,
                    citation=item.get("citation")
                )
                documents.append(doc)

            return documents

        except Exception:
            # Resilient fallback
            aggregator = SearchAggregator(self.config)
            return aggregator.search(f"site:indiankanoon.org {query}", limit=limit)

    def get_document(self, url: str) -> Optional[str]:
        """Fetches a document. Supports fetching structured Kanoon text via API if available, or HTML scraping."""
        token = self.config.get("indian_kanoon_token", "").strip()

        # Parse document ID from URL if using API
        doc_id = None
        if "/doc/" in url:
            parts = url.rstrip("/").split("/")
            for i, part in enumerate(parts):
                if part == "doc" and i + 1 < len(parts):
                    doc_id = parts[i+1]
                    break

        if token and doc_id:
            api_url = f"https://api.indiankanoon.org/doc/{doc_id}/"
            headers = {
                "Authorization": f"Token {token}",
                "Accept": "application/json",
                "User-Agent": self.user_agent
            }
            try:
                response = requests.get(api_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    # Return clean document text if available
                    return data.get("doc", "")
            except Exception:
                pass

        # Scrape fallback
        aggregator = SearchAggregator(self.config)
        return aggregator.get_document(url)
