import importlib.util
import json
import sys
import types
from pathlib import Path

from click.testing import CliRunner

from cli_anything.caselaws.main import main
from cli_anything.caselaws.providers.notebooklm import NotebookLmProvider
from cli_anything.caselaws.providers.base import CaseLawDocument


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPT = REPO_ROOT / ".agents" / "skills" / "gst-appeal-drafting" / "scripts" / "gst_appeal_research.py"


def load_research_script():
    spec = importlib.util.spec_from_file_location("gst_appeal_research", SKILL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_config_set_help_mentions_notebooklm_notebook_id():
    runner = CliRunner()
    result = runner.invoke(main, ["config", "set", "--help"])
    assert result.exit_code == 0
    assert "notebooklm_notebook_id" in result.output


def test_requirements_declares_notebooklm_py_runtime_dependency():
    requirements = (REPO_ROOT / "caselaws-cli" / "requirements.txt").read_text(encoding="utf-8")
    assert "notebooklm-py>=0.5.0" in requirements


def test_research_script_finds_bundled_notebooklm_cli_when_not_on_path(monkeypatch):
    research = load_research_script()
    monkeypatch.delenv("NOTEBOOKLM_CLI", raising=False)
    monkeypatch.setenv("PATH", "/nonexistent")

    cmd, source = research.notebooklm_command()

    assert cmd is not None
    assert cmd[0].endswith("caselaws-cli/.venv/bin/notebooklm")
    assert source == "caselaws-cli/.venv"


def test_research_script_builds_current_notebooklm_ask_command(tmp_path):
    research = load_research_script()
    prompt_file = tmp_path / "prompt.txt"

    cmd = research.build_notebooklm_ask_command(
        notebooklm="notebooklm",
        notebook="gst-law-bank",
        prompt_file=prompt_file,
        timeout=90,
    )

    assert cmd == [
        "notebooklm",
        "ask",
        "--json",
        "--timeout",
        "90",
        "--notebook",
        "gst-law-bank",
        "--prompt-file",
        str(prompt_file),
    ]


def test_research_packet_surfaces_notebooklm_json_error():
    research = load_research_script()
    markdown = research.format_markdown(
        {
            "generated_at": "2026-05-26T00:00:00+00:00",
            "issue": "section 107 limitation",
            "jurisdiction": None,
            "facts": "",
            "notebooklm": {
                "ok": False,
                "parsed": {
                    "error": True,
                    "code": "AUTH_REQUIRED",
                    "message": "Auth not found. Run 'notebooklm login' first.",
                    "status": "error",
                    "details": {
                        "error": "Storage file not found: /home/user/.notebooklm/storage_state.json"
                    },
                },
                "raw": {"stderr": ""},
            },
            "case_law": {"searches": []},
        }
    )

    assert "Auth not found" in markdown


def test_notebooklm_provider_maps_answer_and_references(monkeypatch):
    class FakeNotebook:
        id = "nb-gst"
        title = "GST law bank"

    class FakeSource:
        id = "src-1"
        title = "CGST Act section 107"
        url = "https://example.test/cgst-107"

    class FakeReference:
        source_id = "src-1"
        cited_text = "Appeal filing period and pre-deposit source text"
        citation_number = 1

    class FakeAnswer:
        answer = "Section-backed answer [1]"
        references = [FakeReference()]

    class FakeNotebooks:
        async def list(self):
            return [FakeNotebook()]

    class FakeSources:
        async def list(self, notebook_id):
            assert notebook_id == "nb-gst"
            return [FakeSource()]

        async def get_fulltext(self, notebook_id, source_id):
            assert (notebook_id, source_id) == ("nb-gst", "src-1")
            return types.SimpleNamespace(content="Full source text")

    class FakeChat:
        async def ask(self, notebook_id, query):
            assert notebook_id == "nb-gst"
            assert "section 107" in query
            return FakeAnswer()

    class FakeClient:
        notebooks = FakeNotebooks()
        sources = FakeSources()
        chat = FakeChat()

        @classmethod
        def from_storage(cls):
            return cls()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setitem(sys.modules, "notebooklm", types.SimpleNamespace(NotebookLMClient=FakeClient))

    provider = NotebookLmProvider({})
    docs = provider.search("GST appeal section 107", limit=5)

    assert [type(doc) for doc in docs] == [CaseLawDocument, CaseLawDocument]
    assert docs[0].source == "NotebookLM (Synthesis)"
    assert docs[0].content == "Section-backed answer [1]"
    assert docs[1].title == "CGST Act section 107"
    assert docs[1].metadata["original_url"] == "https://example.test/cgst-107"
    assert provider.get_document("notebooklm://nb-gst/source/src-1") == "Full source text"
