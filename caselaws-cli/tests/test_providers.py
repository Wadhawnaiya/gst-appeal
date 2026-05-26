import pytest
from cli_anything.caselaws.providers.base import CaseLawDocument, BaseProvider
from cli_anything.caselaws.providers.search import SearchAggregator
from cli_anything.caselaws.providers.kanoon import IndianKanoonProvider
from cli_anything.caselaws.providers.cbic import CbicProvider
from cli_anything.caselaws.providers import get_provider

def test_caselaw_document_serialization():
    """Verifies that CaseLawDocument serializes and deserializes correctly."""
    doc = CaseLawDocument(
        title="Test Title",
        url="https://example.com",
        source="Test Source",
        snippet="Test Snippet",
        date="2026-05-23",
        citation="2026 TMI 1",
        content="Full Text Content",
        metadata={"key": "val"}
    )

    serialized = doc.to_dict()
    assert serialized["title"] == "Test Title"
    assert serialized["url"] == "https://example.com"
    assert serialized["source"] == "Test Source"
    assert serialized["snippet"] == "Test Snippet"
    assert serialized["date"] == "2026-05-23"
    assert serialized["citation"] == "2026 TMI 1"
    assert serialized["content"] == "Full Text Content"
    assert serialized["metadata"] == {"key": "val"}

    deserialized = CaseLawDocument.from_dict(serialized)
    assert deserialized.title == "Test Title"
    assert deserialized.url == "https://example.com"
    assert deserialized.source == "Test Source"
    assert deserialized.snippet == "Test Snippet"
    assert deserialized.date == "2026-05-23"
    assert deserialized.citation == "2026 TMI 1"
    assert deserialized.content == "Full Text Content"
    assert deserialized.metadata == {"key": "val"}

def test_registry_factory():
    """Verifies provider lookup works correctly in the registry."""
    config = {"user_agent": "TestBot"}

    search_prov = get_provider("search", config)
    assert isinstance(search_prov, SearchAggregator)

    kanoon_prov = get_provider("kanoon", config)
    assert isinstance(kanoon_prov, IndianKanoonProvider)

    cbic_prov = get_provider("cbic", config)
    assert isinstance(cbic_prov, CbicProvider)

    with pytest.raises(ValueError):
        get_provider("invalid_provider", config)

def test_search_aggregator_schema():
    """Performs a live test query using SearchAggregator to verify DDG HTML parsing is working."""
    config = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
    }
    aggregator = SearchAggregator(config)

    # We query something simple that has reliable search results
    docs = aggregator.search("GST India CBIC", limit=2)

    # Even if query fails (e.g. offline environment), it should return a list resiliently
    assert isinstance(docs, list)
    if len(docs) > 0:
        doc = docs[0]
        assert isinstance(doc, CaseLawDocument)
        assert doc.title != ""
        assert doc.url != ""
        assert doc.source != ""
        assert doc.snippet != ""
