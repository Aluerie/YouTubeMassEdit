import pytest
from click.testing import CliRunner

from youtube_mass_edit.cli import cli
from youtube_mass_edit.config import parse_playlist_id

PLAYLIST_ID = "PL7xvidZnZQmTIOls7jzWSdj2CBu2aiDCT"


@pytest.mark.parametrize(
    "value",
    [
        PLAYLIST_ID,
        f"  {PLAYLIST_ID}  ",
        f"https://www.youtube.com/playlist?list={PLAYLIST_ID}",
        f"https://www.youtube.com/watch?v=dQw4w9WgXcQ&list={PLAYLIST_ID}&index=3",
        f"youtube.com/playlist?list={PLAYLIST_ID}",
        f"https://youtu.be/dQw4w9WgXcQ?list={PLAYLIST_ID}",
    ],
)
def test_parse_playlist_id(value: str) -> None:
    assert parse_playlist_id(value) == PLAYLIST_ID


@pytest.mark.parametrize(
    "value",
    ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "not a playlist", "PL<script>", ""],
)
def test_parse_playlist_id_rejects(value: str) -> None:
    with pytest.raises(ValueError, match="playlist"):
        parse_playlist_id(value)


def test_cli_rejects_unknown_playlist_before_connecting() -> None:
    result = CliRunner().invoke(cli, ["update", "dark_souls"])
    assert result.exit_code == 1
    assert "no playlist called 'dark_souls'" in result.output


def test_cli_help_lists_commands() -> None:
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "update" in result.output
    assert "restore" in result.output
