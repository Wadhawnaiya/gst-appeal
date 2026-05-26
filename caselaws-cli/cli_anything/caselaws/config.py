import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "caselaws-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "indian_kanoon_token": "",
    "notebooklm_notebook_id": "",  # Set this to prioritize a specific Notebook ID
    "default_provider": "search",  # 'search', 'kanoon', 'cbic', or 'notebooklm'
    "default_limit": 10,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
}

def load_config():
    """Loads the CLI configuration from ~/.config/caselaws-cli/config.json."""
    if not CONFIG_FILE.exists():
        return save_config(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, "r") as f:
            user_config = json.load(f)
            # Ensure all default keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    except Exception:
        return DEFAULT_CONFIG

def save_config(config):
    """Saves the configuration to the config file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass
    return config

def update_config_key(key, value):
    """Updates a single key in the configuration."""
    config = load_config()
    config[key] = value
    save_config(config)
    return config
