"""Load the project settings from ``config.toml``."""

import re
import tomllib
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit
lazy from pathlib import Path

from .description import Template

_PLAYLIST_ID_RE = re.compile(r"[A-Za-z0-9_-]{10,}")


def parse_playlist_id(value: str) -> str:
    """Return the playlist ID from a bare ID or any YouTube URL with a ``list=`` parameter.

    Raises ``ValueError`` when no valid-looking playlist ID can be found.
    """
    value = value.strip()
    if "youtube.com" in value or "youtu.be" in value or "://" in value:
        url = value if "://" in value else f"https://{value}"
        ids = parse_qs(urlsplit(url).query).get("list")
        if not ids:
            msg = f"no playlist ID ('list=...') in URL: {value}"
            raise ValueError(msg)
        value = ids[0]
    if not _PLAYLIST_ID_RE.fullmatch(value):
        msg = f"not a YouTube playlist ID: {value!r}"
        raise ValueError(msg)
    return value


@dataclass(frozen=True, slots=True)
class Config:
    """Settings for one run on one named playlist, with every path already resolved."""

    name: str
    playlist_id: str
    template: Template
    tags: list[str] | None
    client_secret_file: Path
    token_file: Path
    backup_dir: Path


def _read_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def load_config(path: Path, name: str) -> Config:
    """Read the settings for the playlist called ``name`` from ``path``, plus its shared-block file.

    Top-level settings apply to every playlist; a playlist's own table can override
    ``start_heading`` and ``end_heading``. Relative paths are resolved against the directory that
    holds ``path``. Raises ``ValueError`` for an unknown name or invalid settings.
    """
    root = path.parent
    data = _read_toml(path)
    playlists = data.get("playlists", {})
    if name not in playlists:
        known = ", ".join(playlists) or "none"
        msg = f"no playlist called {name!r} in {path} (set up: {known})"
        raise ValueError(msg)
    entry = playlists[name]
    for key in ("playlist", "shared_file"):
        if key not in entry:
            msg = f"{path}: playlist {name!r} is missing {key!r}"
            raise ValueError(msg)

    tags = entry.get("tags")
    if tags is not None and not (isinstance(tags, list) and all(isinstance(t, str) for t in tags)):
        msg = f"{path}: 'tags' of playlist {name!r} must be a list of strings"
        raise ValueError(msg)

    return Config(
        name=name,
        playlist_id=parse_playlist_id(entry["playlist"]),
        template=Template(
            start_heading=entry.get("start_heading", data["start_heading"]),
            end_heading=entry.get("end_heading", data["end_heading"]),
            shared_block=(root / entry["shared_file"]).read_text(encoding="utf-8"),
            hashtags=entry.get("hashtags", ""),
        ),
        tags=tags,
        client_secret_file=root / data.get("client_secret_file", "client_secret.json"),
        token_file=root / data.get("token_file", "token.json"),
        backup_dir=root / data.get("backup_dir", "backups"),
    )
