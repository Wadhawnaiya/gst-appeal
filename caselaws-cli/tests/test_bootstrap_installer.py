import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap_gst_appeal.py"


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("bootstrap_gst_appeal", BOOTSTRAP)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_layout_is_folder_local_and_agent_skill_targets(tmp_path):
    bootstrap = load_bootstrap()

    layout = bootstrap.InstallLayout.for_target(tmp_path)

    assert layout.target_dir == tmp_path.resolve()
    assert layout.install_root == tmp_path / ".gst-appeal"
    assert layout.repo_dir == tmp_path / ".gst-appeal" / "repo"
    assert layout.bin_dir == tmp_path / ".gst-appeal" / "bin"
    assert layout.caselaws_venv == tmp_path / ".gst-appeal" / "venvs" / "caselaws-cli"
    assert layout.notebooklm_venv == tmp_path / ".gst-appeal" / "venvs" / "notebooklm-cli"
    assert tmp_path / ".agents" / "skills" / "gst-appeal-drafting" in layout.skill_targets
    assert tmp_path / ".codex" / "skills" / "gst-appeal-drafting" in layout.skill_targets


def test_write_wrappers_exports_local_tool_paths(tmp_path):
    bootstrap = load_bootstrap()
    layout = bootstrap.InstallLayout.for_target(tmp_path)
    layout.repo_dir.mkdir(parents=True)
    (layout.repo_dir / ".agents" / "skills" / "gst-appeal-drafting" / "scripts").mkdir(parents=True)

    bootstrap.write_wrappers(layout, dry_run=False)

    env_text = (layout.install_root / "env.sh").read_text(encoding="utf-8")
    autodraft = (layout.bin_dir / "gst-appeal-autodraft").read_text(encoding="utf-8")
    assert f'export GST_APPEAL_HOME="{layout.install_root}"' in env_text
    assert f'export CASELAWS_REPO="{layout.repo_dir / "caselaws-cli"}"' in env_text
    assert f'export NOTEBOOKLM_CLI="{layout.notebooklm_venv / "bin" / "notebooklm"}"' in env_text
    assert "gst_appeal_autodraft.py" in autodraft
    assert "CASELAWS_CLI" in autodraft


def test_copy_skill_installs_universal_and_codex_skill_targets(tmp_path):
    bootstrap = load_bootstrap()
    layout = bootstrap.InstallLayout.for_target(tmp_path)
    source_skill = layout.repo_dir / ".agents" / "skills" / "gst-appeal-drafting"
    source_skill.mkdir(parents=True)
    (source_skill / "SKILL.md").write_text("# GST Skill\n", encoding="utf-8")

    copied = bootstrap.copy_skill(layout, dry_run=False)

    assert set(copied) == set(layout.skill_targets)
    for target in layout.skill_targets:
        assert (target / "SKILL.md").read_text(encoding="utf-8") == "# GST Skill\n"


def test_dry_run_summary_plans_without_writing(tmp_path):
    bootstrap = load_bootstrap()
    args = bootstrap.parse_args([
        "--target",
        str(tmp_path),
        "--skip-notebooklm",
        "--skip-playwright",
        "--dry-run",
    ])

    summary = bootstrap.bootstrap(args)

    assert summary["dry_run"] is True
    assert summary["target_dir"] == str(tmp_path.resolve())
    assert summary["install_root"] == str(tmp_path / ".gst-appeal")
    assert any("git" in " ".join(step.get("cmd", [])) for step in summary["planned_steps"])
    assert not (tmp_path / ".gst-appeal").exists()
