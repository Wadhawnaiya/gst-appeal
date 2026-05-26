from typing import Dict, Type, Any
from cli_anything.caselaws.providers.base import BaseProvider
from cli_anything.caselaws.providers.search import SearchAggregator
from cli_anything.caselaws.providers.kanoon import IndianKanoonProvider
from cli_anything.caselaws.providers.cbic import CbicProvider
from cli_anything.caselaws.providers.notebooklm import NotebookLmProvider

PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "search": SearchAggregator,
    "kanoon": IndianKanoonProvider,
    "cbic": CbicProvider,
    "notebooklm": NotebookLmProvider
}

def get_provider(name: str, config: Dict[str, Any]) -> BaseProvider:
    """Factory to get an initialized search provider by name."""
    provider_cls = PROVIDER_REGISTRY.get(name.lower())
    if not provider_cls:
        raise ValueError(f"Unknown search provider: {name}. Available: {list(PROVIDER_REGISTRY.keys())}")
    return provider_cls(config)
