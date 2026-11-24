from pathlib import Path

import pytest

from youtube_mass_edit.config import load_config

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG = PROJECT_ROOT / "config.toml"


@pytest.mark.parametrize(("name", "hashtag"), [("sekiro", "#sekiro"), ("elden_ring", "#eldenring")])
def test_project_playlists_load(name: str, hashtag: str) -> None:
    config = load_config(CONFIG, name)
    assert config.name == name
    assert config.playlist_id
    assert config.template.shared_block.startswith("# 😘Chosen Playlist Restrictions")
    assert hashtag in config.template.hashtags
    assert config.client_secret_file == PROJECT_ROOT / "client_secret.json"


def test_playlists_keep_their_own_text() -> None:
    sekiro = load_config(CONFIG, "sekiro")
    elden_ring = load_config(CONFIG, "elden_ring")
    assert "UDB8R" in sekiro.template.shared_block
    assert "108R" in elden_ring.template.shared_block
    assert sekiro.playlist_id != elden_ring.playlist_id


def test_playlist_can_override_headings(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# Rules\n", encoding="utf-8")
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'start_heading = "Rules"\nend_heading = "Timestamps"\n'
        '[playlists.a]\nplaylist = "PL1234567890"\nshared_file = "a.md"\nend_heading = "Chapters"\n',
        encoding="utf-8",
    )
    config = load_config(config_file, "a")
    assert config.template.start_heading == "Rules"
    assert config.template.end_heading == "Chapters"


def test_unknown_playlist_lists_known_names() -> None:
    with pytest.raises(ValueError, match="sekiro, elden_ring"):
        load_config(CONFIG, "dark_souls")
