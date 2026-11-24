"""Load the project settings from ``config.toml``."""

import tomllib
from dataclasses import dataclass
lazy from pathlib import Path

from .description import Template


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
        playlist_id=data["playlist_id"],
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
