import json

from click.testing import CliRunner

from cli_anything.caselaws.main import main
from cli_anything.caselaws.providers.base import CaseLawDocument
from cli_anything.caselaws.research import build_notebooklm_prompt, build_research_queries, infer_provider_for_document


def test_build_research_queries_include_notebooklm_cbic_and_jurisdiction():
    queries = build_research_queries(
        "section 125 penalty for sign board",
        jurisdiction="Punjab",
        facts="SCN alleges sign board not displayed.",
        forum="first appeal",
    )

    providers = [item["provider"] for item in queries]
    assert providers[0] == "notebooklm"
    assert "cbic" in providers
    assert any("Punjab" in item["query"] for item in queries)
    prompt = queries[0]["query"]
    assert "source-backed material" in prompt
    assert "VERIFY BEFORE FILING" in prompt


def test_build_notebooklm_prompt_demands_filing_facts():
    prompt = build_notebooklm_prompt("GST appeal limitation", forum="first appeal")
    assert "order communication date" in prompt
    assert "pre-deposit" in prompt
    assert "Source title" in prompt


def test_infer_provider_for_document():
    assert infer_provider_for_document(CaseLawDocument("A", "notebooklm://nb/source/src", "NotebookLM", "")) == "notebooklm"
    assert infer_provider_for_document(CaseLawDocument("A", "https://indiankanoon.org/doc/1/", "Web", "")) == "kanoon"
    assert infer_provider_for_document(CaseLawDocument("A", "https://cbic-gst.gov.in/x.pdf", "Web", "")) == "cbic"
    assert infer_provider_for_document(CaseLawDocument("A", "https://example.test", "Web", "")) == "search"


def test_research_command_json_with_fake_providers(monkeypatch, tmp_path):
    class FakeProvider:
        def __init__(self, config):
            self.config = config

        def search(self, query, limit=10):
            return [
                CaseLawDocument(
                    title="Fake GST authority",
                    url="https://example.test/gst",
                    source="Fake Source",
                    snippet=query[:80],
                )
            ][:limit]

        def get_document(self, url):
            return "Full verified text for " + url

    def fake_get_provider(name, config):
        return FakeProvider(config)

    monkeypatch.setattr("cli_anything.caselaws.research.get_provider", fake_get_provider)
    facts = tmp_path / "facts.md"
    facts.write_text("SCN and order facts", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "research",
            "section 125 penalty",
            "--facts-file",
            str(facts),
            "--jurisdiction",
            "Punjab",
            "--limit",
            "1",
            "--fetch-top",
            "1",
            "--json",
        ],
    )

    assert result.exit_code == 0
    packet = json.loads(result.output)
    assert packet["issue"] == "section 125 penalty"
    assert packet["jurisdiction"] == "Punjab"
    assert packet["searches"]
    assert packet["fetched_documents"]
    assert packet["fetched_documents"][0]["ok"] is True
