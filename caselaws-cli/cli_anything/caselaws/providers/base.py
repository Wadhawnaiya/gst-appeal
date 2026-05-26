from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class CaseLawDocument:
    """Standardized representation of a GST case law, circular, or legal document."""
    def __init__(
        self,
        title: str,
        url: str,
        source: str,
        snippet: str,
        date: Optional[str] = None,
        citation: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.title = title.strip()
        self.url = url.strip()
        self.source = source.strip()
        self.snippet = snippet.strip()
        self.date = date.strip() if date else None
        self.citation = citation.strip() if citation else None
        self.content = content.strip() if content else None
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the document to a dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "snippet": self.snippet,
            "date": self.date,
            "citation": self.citation,
            "content": self.content,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseLawDocument":
        """Creates a CaseLawDocument from a serialized dictionary."""
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            source=data.get("source", ""),
            snippet=data.get("snippet", ""),
            date=data.get("date"),
            citation=data.get("citation"),
            content=data.get("content"),
            metadata=data.get("metadata")
        )


class BaseProvider(ABC):
    """Abstract base class for all GST search providers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.user_agent = config.get("user_agent", "Mozilla/5.0")

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[CaseLawDocument]:
        """Executes a search query and returns a list of standardized CaseLawDocuments."""
        pass

    @abstractmethod
    def get_document(self, url: str) -> Optional[str]:
        """Fetches the full text content of a legal document given its URL."""
        pass
