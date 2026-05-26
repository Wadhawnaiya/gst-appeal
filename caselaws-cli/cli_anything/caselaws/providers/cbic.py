from typing import List, Optional, Dict, Any
from cli_anything.caselaws.providers.base import BaseProvider, CaseLawDocument
from cli_anything.caselaws.providers.search import SearchAggregator

class CbicProvider(BaseProvider):
    """Provider targeting CBIC and GST Council notifications and circulars."""

    def search(self, query: str, limit: int = 10) -> List[CaseLawDocument]:
        aggregator = SearchAggregator(self.config)

        # Build targeted query search for circulars and notifications on cbic and gstcouncil websites
        targeted_query = f"(site:cbic.gov.in OR site:cbic-gst.gov.in OR site:gstcouncil.gov.in) (circular OR notification OR \"trade notice\") {query}"

        docs = aggregator.search(targeted_query, limit=limit)

        # Post-process results to format titles and metadata for CBIC standard
        for doc in docs:
            doc.source = "CBIC / GST Council"

            # Simple circular/notification classification heuristic
            title_upper = doc.title.upper()
            if "CIRCULAR" in title_upper:
                doc.metadata["doc_type"] = "Circular"
            elif "NOTIFICATION" in title_upper:
                doc.metadata["doc_type"] = "Notification"
            elif "TRADE NOTICE" in title_upper:
                doc.metadata["doc_type"] = "Trade Notice"
            else:
                doc.metadata["doc_type"] = "Official Order"

        return docs

    def get_document(self, url: str) -> Optional[str]:
        """Fetches the document text from CBIC portal (supports scraping or PDF parsing if the URL is a PDF)."""
        aggregator = SearchAggregator(self.config)

        # If it's a PDF link, we could theoretically download it and extract text
        if url.lower().endswith(".pdf"):
            return self._download_and_parse_pdf(url)

        return aggregator.get_document(url)

    def _download_and_parse_pdf(self, url: str) -> Optional[str]:
        """Downloads a PDF and extracts plain text from it."""
        import requests
        import io
        from pypdf import PdfReader

        headers = {"User-Agent": self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                return None

            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)

            text_pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_pages.append(f"--- Page {i+1} ---\n{text}")

            return "\n\n".join(text_pages)
        except Exception as e:
            return f"Error reading PDF from {url}: {str(e)}"
