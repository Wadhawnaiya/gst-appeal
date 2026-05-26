import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTO_SCRIPT = REPO_ROOT / ".agents" / "skills" / "gst-appeal-drafting" / "scripts" / "gst_appeal_autodraft.py"


def load_auto_script():
    spec = importlib.util.spec_from_file_location("gst_appeal_autodraft", AUTO_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_autodraft_infers_documents_metadata_and_issues(tmp_path):
    auto = load_auto_script()
    matter = tmp_path / "matter"
    matter.mkdir()
    (matter / "SCN.txt").write_text(
        "Show Cause Notice FORM GST DRC-01 under section 125 for failure to display sign board. "
        "Penalty Rs. 25,000 dated 01/04/2026 GSTIN 27ABCDE1234F1Z5.",
        encoding="utf-8",
    )
    (matter / "order.txt").write_text(
        "Impugned order FORM GST DRC-07 confirms penalty without considering reply and personal hearing.",
        encoding="utf-8",
    )
    docs = [auto.extract_document(path, matter, 5000) for path in sorted(matter.iterdir())]
    combined = "\n".join(doc["text"] for doc in docs)
    metadata = auto.extract_metadata(combined)
    issues = auto.infer_issues(combined)

    assert any("show_cause_notice" in doc["doc_types"] for doc in docs)
    assert any("impugned_order" in doc["doc_types"] for doc in docs)
    assert "section 125" in " ".join(metadata["sections"]).lower()
    assert any("sign board" in issue.lower() for issue in issues)
    assert any("section 107" in issue.lower() for issue in issues)


def test_autodraft_workspace_skip_live_research(tmp_path):
    auto = load_auto_script()
    matter = tmp_path / "matter"
    matter.mkdir()
    (matter / "facts.md").write_text(
        "SCN under section 125 for sign board. Reply filed but impugned order ignored evidence. Demand Rs. 10,000 dated 02/05/2026.",
        encoding="utf-8",
    )
    output = tmp_path / "workspace"
    args = type(
        "Args",
        (),
        {
            "matter_dir": str(matter),
            "output_dir": str(output),
            "issue": None,
            "forum": "first appeal under section 107",
            "jurisdiction": "Gujarat",
            "notebook": None,
            "case_limit": 1,
            "fetch_top": 0,
            "timeout": 10,
            "max_chars_per_document": 5000,
            "max_facts_chars": 5000,
            "include_generated": False,
            "skip_live_research": True,
            "skip_notebooklm": False,
            "skip_caselaws": False,
        },
    )()

    packet = auto.build_workspace(args)

    assert Path(packet["facts_digest_file"]).exists()
    assert (output / "appeal-drafting-brief.md").exists()
    assert (output / "autodraft-summary.json").exists()
    summary = json.loads((output / "autodraft-summary.json").read_text(encoding="utf-8"))
    assert summary["jurisdiction"] == "Gujarat"
    assert summary["notebooklm_runs"][0]["skipped"] is True
    assert summary["caselaw_runs"][0]["skipped"] is True
