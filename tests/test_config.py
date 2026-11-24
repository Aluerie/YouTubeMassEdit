from pathlib import Path

from youtube_mass_edit.config import load_config

PROJECT_ROOT = Path(__file__).parent.parent


def test_project_config_loads_and_matches_shared_file() -> None:
    config = load_config(PROJECT_ROOT / "config.toml")
    assert config.playlist_id
    assert config.template.shared_block.startswith("# 😘Chosen Playlist Restrictions")
    assert config.client_secret_file == PROJECT_ROOT / "client_secret.json"
