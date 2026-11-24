"""Command-line entry point: preview, apply and undo description changes across a playlist."""

import dataclasses
import difflib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import click
from googleapiclient.errors import HttpError

from . import youtube
from .config import Config, load_config, parse_playlist_id
from .description import validation_errors

if TYPE_CHECKING:
    from googleapiclient._apis.youtube.v3 import Video, YouTubeResource


@dataclass(frozen=True, slots=True)
class Change:
    """A planned edit of one video. ``tags=None`` means the tags stay as they are."""

    video: Video
    description: str
    tags: list[str] | None

    @property
    def title(self) -> str:
        return _title(self.video)


def _title(video: Video) -> str:
    return video["snippet"].get("title", video["id"])


def _print_diff(change: Change) -> None:
    old = change.video["snippet"]
    click.secho(f"\n=== {change.title} (https://youtu.be/{change.video['id']}) ===", bold=True)
    diff = difflib.unified_diff(
        old.get("description", "").splitlines(), change.description.splitlines(), lineterm="", n=0
    )
    for line in diff:
        if line.startswith(("---", "+++")):
            continue
        color = {"-": "red", "+": "green", "@": "cyan"}.get(line[:1])
        click.secho(line, fg=color)
    if change.tags is not None and change.tags != old.get("tags", []):
        click.echo(f"tags: {old.get('tags', [])} -> {change.tags}")


def _is_noop(change: Change) -> bool:
    old = change.video["snippet"]
    same_description = change.description == old.get("description", "")
    same_tags = change.tags is None or change.tags == old.get("tags", [])
    return same_description and same_tags


def _write_backup(videos: list[Video], backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"{datetime.now():%Y-%m-%d_%H%M%S}.json"
    data = {v["id"]: v["snippet"] for v in videos}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _run(yt: YouTubeResource, changes: list[Change], *, apply: bool, backup_dir: Path) -> int:
    """Show every change and, with ``apply``, save them. Returns the process exit code."""
    changes = [c for c in changes if not _is_noop(c)]
    if not changes:
        click.echo("\nNothing to change: every video is already up to date.")
        return 0

    valid: list[Change] = []
    for change in changes:
        _print_diff(change)
        if errors := validation_errors(change.description):
            for error in errors:
                click.secho(f"!! not saving: {error}", fg="yellow")
        else:
            valid.append(change)

    invalid = len(changes) - len(valid)
    if not apply:
        click.echo(f"\nDry run: {len(valid)} video(s) would be updated, {invalid} rejected.")
        click.echo("Run again with --apply to save.")
        return 1 if invalid else 0

    backup = _write_backup([c.video for c in valid], backup_dir)
    click.echo(f"\nBacked up {len(valid)} original snippet(s) to {backup}")

    for done, change in enumerate(valid):
        try:
            youtube.update_video(yt, change.video, description=change.description, tags=change.tags)
        except HttpError as e:
            if youtube.is_quota_exceeded(e):
                click.secho(
                    f"\nDaily API quota used up after {done} update(s); {len(valid) - done} left.",
                    fg="yellow",
                )
                click.echo("Run the same command again tomorrow: finished videos are skipped.")
                return 2
            raise
        click.secho(f"saved: {change.title}", fg="green")

    click.echo(f"\nUpdated {len(valid)} video(s), {invalid} rejected.")
    return 1 if invalid else 0


def _connect(config: Config) -> YouTubeResource:
    if not config.token_file.exists() and not config.client_secret_file.exists():
        msg = (
            f"{config.client_secret_file} not found. Create an OAuth 'Desktop app' client in Google "
            "Cloud Console, download its JSON and save it there (see README.md)."
        )
        raise click.ClickException(msg)
    return youtube.connect(config.client_secret_file, config.token_file)


def _playlist_videos(yt: YouTubeResource, config: Config) -> list[Video]:
    videos = youtube.fetch_videos(yt, youtube.playlist_video_ids(yt, config.playlist_id))
    click.echo(f"Found {len(videos)} video(s) in playlist {config.playlist_id}.")
    return videos


def _parse_playlist(_ctx: click.Context, _param: click.Parameter, value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return parse_playlist_id(value)
    except ValueError as e:
        raise click.BadParameter(str(e)) from e


apply_option = click.option("--apply", is_flag=True, help="Save the changes. Without it, only a preview.")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default="config.toml",
    show_default=True,
    help="Settings file.",
)
@click.option(
    "--playlist",
    callback=_parse_playlist,
    help="Playlist ID or URL to work on, instead of the one in the settings file.",
)
@click.pass_context
def cli(ctx: click.Context, config_path: Path, playlist: str | None) -> None:
    """Replace the shared sections of every video description in a YouTube playlist.

    Only videos in the playlist are ever changed.
    """
    try:
        config = load_config(config_path)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    if playlist is not None:
        config = dataclasses.replace(config, playlist_id=playlist)
    ctx.obj = config


@cli.command()
@apply_option
@click.pass_obj
def update(config: Config, *, apply: bool) -> None:
    """Put the shared block and hashtags into every video in the playlist."""
    yt = _connect(config)
    changes: list[Change] = []
    for video in _playlist_videos(yt, config):
        new_description = config.template.rewrite(video["snippet"].get("description", ""))
        if new_description is None:
            click.secho(f"skipped (headings not found): {_title(video)}", fg="yellow")
            continue
        changes.append(Change(video, new_description, config.tags))

    raise SystemExit(_run(yt, changes, apply=apply, backup_dir=config.backup_dir))


@cli.command()
@click.argument("backup", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@apply_option
@click.pass_obj
def restore(config: Config, backup: Path, *, apply: bool) -> None:
    """Put descriptions and tags back from a BACKUP file, for videos in the playlist only."""
    saved = json.loads(backup.read_text(encoding="utf-8"))
    yt = _connect(config)
    videos = [v for v in _playlist_videos(yt, config) if v["id"] in saved]

    outside = set(saved) - {v["id"] for v in videos}
    for video_id in sorted(outside):
        title = saved[video_id].get("title", video_id)
        click.secho(f"skipped (not in playlist {config.playlist_id}): {title}", fg="yellow")

    changes = [
        Change(v, saved[v["id"]].get("description", ""), saved[v["id"]].get("tags", [])) for v in videos
    ]
    raise SystemExit(_run(yt, changes, apply=apply, backup_dir=config.backup_dir))
