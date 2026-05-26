import requests
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from cli_anything.caselaws.providers.base import BaseProvider, CaseLawDocument

class SearchAggregator(BaseProvider):
    """General search aggregator utilizing DuckDuckGo HTML search for free, robust, and CAPTCHA-free results."""

    def search(self, query: str, limit: int = 10) -> List[CaseLawDocument]:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://duckduckgo.com/"
        }

        # We can pass query in the form post parameters
        data = {"q": query}

        try:
            response = requests.post(url, data=data, headers=headers, timeout=15)
            if response.status_code != 200:
                # Fallback to GET just in case
                response = requests.get(url, params={"q": query}, headers=headers, timeout=15)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.select(".result")

            documents = []
            for result in results:
                if len(documents) >= limit:
                    break

                title_elem = result.select_one(".result__a")
                snippet_elem = result.select_one(".result__snippet")

                if not title_elem:
                    continue

                title = title_elem.text.strip()
                raw_href = title_elem.get("href", "")

                # Extract real URL from DuckDuckGo redirect format:
                # e.g., //duckduckgo.com/l/?uddg=https%3A%2F%2Findiankanoon.org%2Fdoc%2F12345%2F
                parsed_url = raw_href
                if "uddg=" in raw_href:
                    try:
                        parsed = urllib.parse.urlparse(raw_href)
                        queries = urllib.parse.parse_qs(parsed.query)
                        if "uddg" in queries and len(queries["uddg"]) > 0:
                            parsed_url = queries["uddg"][0]
                    except Exception:
                        pass

                # Skip duckduckgo internal URLs if any
                if parsed_url.startswith("//") or "duckduckgo.com" in parsed_url:
                    if parsed_url.startswith("//"):
                        parsed_url = "https:" + parsed_url
                    else:
                        continue

                snippet = snippet_elem.text.strip() if snippet_elem else ""

                # Determine source from URL
                source = "General Web"
                if "indiankanoon.org" in parsed_url:
                    source = "Indian Kanoon"
                elif "cbic" in parsed_url:
                    source = "CBIC"
                elif "gstat.gov.in" in parsed_url:
                    source = "GSTAT"
                elif "taxmann.com" in parsed_url:
                    source = "Taxmann"
                elif "scconline.com" in parsed_url:
                    source = "SCC Online"
                elif "gstcouncil.gov.in" in parsed_url:
                    source = "GST Council"

                # Simple date heuristic (often present at the start of snippet or in title)
                doc_date = None

                doc = CaseLawDocument(
                    title=title,
                    url=parsed_url,
                    source=source,
                    snippet=snippet,
                    date=doc_date
                )
                documents.append(doc)

            return documents

        except Exception as e:
            # Silently return empty on failure for resiliency
            return []

    def get_document(self, url: str) -> Optional[str]:
        """Fetches and cleans plain text content from the target URL."""
        headers = {"User-Agent": self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove scripts, styles, navigations
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()

            # Get text and clean it
            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines)

        except Exception:
            return None
