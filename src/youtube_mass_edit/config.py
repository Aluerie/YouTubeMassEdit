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
    """Settings for one mass-edit run, with every path already resolved."""

    playlist_id: str
    template: Template
    tags: list[str] | None
    client_secret_file: Path
    token_file: Path
    backup_dir: Path


def load_config(path: Path) -> Config:
    """Read ``path`` and the shared-block file it points to.

    Relative paths inside the file are resolved against the directory that holds it.
    """
    root = path.parent
    with path.open("rb") as f:
        data = tomllib.load(f)

    shared_block = (root / data.get("shared_file", "for_editing/shared.md")).read_text(encoding="utf-8")
    tags = data.get("tags")
    if tags is not None and not (isinstance(tags, list) and all(isinstance(t, str) for t in tags)):
        msg = f"{path}: 'tags' must be a list of strings"
        raise ValueError(msg)

    return Config(
        playlist_id=parse_playlist_id(data["playlist_id"]),
        template=Template(
            start_heading=data["start_heading"],
            end_heading=data["end_heading"],
            shared_block=shared_block,
            hashtags=data.get("hashtags", ""),
        ),
        tags=tags,
        client_secret_file=root / data.get("client_secret_file", "client_secret.json"),
        token_file=root / data.get("token_file", "token.json"),
        backup_dir=root / data.get("backup_dir", "backups"),
    )
