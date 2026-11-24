"""Command-line entry point: preview, apply and undo description changes across a playlist."""

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from . import youtube
from .config import Config, load_config
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
        return self.video["snippet"].get("title", self.video["id"])


def _print_diff(change: Change) -> None:
    old = change.video["snippet"]
    print(f"\n=== {change.title} (https://youtu.be/{change.video['id']}) ===")
    diff = difflib.unified_diff(
        old.get("description", "").splitlines(), change.description.splitlines(), lineterm="", n=0
    )
    for line in diff:
        if not line.startswith(("---", "+++")):
            print(line)
    if change.tags is not None and change.tags != old.get("tags", []):
        print(f"tags: {old.get('tags', [])} -> {change.tags}")


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
        print("\nNothing to change: every video is already up to date.")
        return 0

    valid: list[Change] = []
    for change in changes:
        _print_diff(change)
        if errors := validation_errors(change.description):
            for error in errors:
                print(f"!! not saving: {error}")
        else:
            valid.append(change)

    invalid = len(changes) - len(valid)
    if not apply:
        print(f"\nDry run: {len(valid)} video(s) would be updated, {invalid} rejected.")
        print("Run again with --apply to save.")
        return 1 if invalid else 0

    backup = _write_backup([c.video for c in valid], backup_dir)
    print(f"\nBacked up {len(valid)} original snippet(s) to {backup}")

    for done, change in enumerate(valid):
        try:
            youtube.update_video(yt, change.video, description=change.description, tags=change.tags)
        except HttpError as e:
            if youtube.is_quota_exceeded(e):
                print(f"\nDaily API quota used up after {done} update(s); {len(valid) - done} left.")
                print("Run the same command again tomorrow: finished videos are skipped.")
                return 2
            raise
        print(f"saved: {change.title}")

    print(f"\nUpdated {len(valid)} video(s), {invalid} rejected.")
    return 1 if invalid else 0


def _update(config: Config, *, apply: bool) -> int:
    yt = youtube.connect(config.client_secret_file, config.token_file)
    videos = youtube.fetch_videos(yt, youtube.playlist_video_ids(yt, config.playlist_id))
    print(f"Found {len(videos)} video(s) in the playlist.")

    changes: list[Change] = []
    for video in videos:
        new_description = config.template.rewrite(video["snippet"].get("description", ""))
        if new_description is None:
            print(f"skipped (headings not found): {video['snippet'].get('title', video['id'])}")
            continue
        changes.append(Change(video, new_description, config.tags))

    return _run(yt, changes, apply=apply, backup_dir=config.backup_dir)


def _restore(config: Config, backup_file: Path, *, apply: bool) -> int:
    saved = json.loads(backup_file.read_text(encoding="utf-8"))
    yt = youtube.connect(config.client_secret_file, config.token_file)
    videos = youtube.fetch_videos(yt, list(saved))

    changes = [
        Change(v, saved[v["id"]].get("description", ""), saved[v["id"]].get("tags", [])) for v in videos
    ]
    return _run(yt, changes, apply=apply, backup_dir=config.backup_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="youtube-mass-edit",
        description="Replace the shared sections of every video description in a playlist.",
    )
    parser.add_argument(
        "--config", type=Path, default=Path("config.toml"), help="settings file (default: config.toml)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    update = commands.add_parser("update", help="put for_editing/shared.md and the hashtags into every video")
    update.add_argument("--apply", action="store_true", help="save the changes (default: dry run)")

    restore = commands.add_parser("restore", help="put descriptions and tags back from a backup")
    restore.add_argument("backup", type=Path, help="a JSON file from the backups folder")
    restore.add_argument("--apply", action="store_true", help="save the changes (default: dry run)")

    args = parser.parse_args(argv)
    config = load_config(args.config)

    if not config.token_file.exists() and not config.client_secret_file.exists():
        print(
            f"{config.client_secret_file} not found. Create an OAuth 'Desktop app' client in Google "
            "Cloud Console, download its JSON and save it there (see README.md)."
        )
        return 2

    if args.command == "restore":
        return _restore(config, args.backup, apply=args.apply)
    return _update(config, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
