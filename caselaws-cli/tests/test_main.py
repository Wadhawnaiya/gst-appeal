import json
import pytest
from click.testing import CliRunner
from cli_anything.caselaws.main import main, CACHE_FILE
from cli_anything.caselaws.config import CONFIG_FILE, load_config

def test_config_commands():
    """Verifies that config show and config set commands behave properly."""
    runner = CliRunner()

    # 1. Test config show
    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 0
    # Current config will be printed to stdout in JSON format
    parsed_config = json.loads(result.output.split("\n", 1)[1])
    assert "default_provider" in parsed_config
    assert "default_limit" in parsed_config

    # 2. Test config set
    result_set = runner.invoke(main, ["config", "set", "default_limit", "5"])
    assert result_set.exit_code == 0
    assert "updated successfully" in result_set.output

    # Reload and assert changed configuration
    config = load_config()
    assert config["default_limit"] == 5

def test_search_and_get_help():
    """Verifies that search and get commands have active help documentation."""
    runner = CliRunner()

    result_search = runner.invoke(main, ["search", "--help"])
    assert result_search.exit_code == 0
    assert "Search for relevant GST case laws" in result_search.output

    result_get = runner.invoke(main, ["get", "--help"])
    assert result_get.exit_code == 0
    assert "Retrieve full text content of a case law" in result_get.output

def test_search_invalid_provider():
    """Verifies search resilience with an invalid provider option."""
    runner = CliRunner()

    result = runner.invoke(main, ["search", "ITC mismatch", "-p", "invalid_prov"])
    # Click option validation should catch this since provider has Choice
    assert result.exit_code != 0
    assert "Invalid value for '--provider'" in result.output
