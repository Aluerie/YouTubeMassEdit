"""Talk to the YouTube Data API: log in, read playlist videos, update video snippets."""

from http import HTTPStatus
from typing import TYPE_CHECKING, cast
lazy from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
lazy from googleapiclient.errors import HttpError

if TYPE_CHECKING:
    from googleapiclient._apis.youtube.v3 import Video, VideoSnippet, YouTubeResource

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Snippet fields copied back on update. videos.update replaces the whole snippet, so any field
# left out (tags especially) would be wiped.
_KEPT_SNIPPET_FIELDS = ("title", "categoryId", "tags", "defaultLanguage", "defaultAudioLanguage")


def connect(client_secret_file: Path, token_file: Path) -> YouTubeResource:
    """Return a YouTube API client, logging in through the browser only when needed.

    The login is saved to ``token_file`` and refreshed from there on later runs. If Google has
    revoked the saved login (it does so after 7 days for apps in "Testing" mode), the browser login
    runs again.
    """
    creds: Credentials | None = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds is not None and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            print("Saved login expired or was revoked; logging in again in the browser.")
            creds = None

    if creds is None or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
        creds = cast("Credentials", flow.run_local_server(port=0))

    token_file.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def playlist_video_ids(yt: YouTubeResource, playlist_id: str) -> list[str]:
    """Return the IDs of every video in the playlist, in playlist order."""
    ids: list[str] = []
    page_token: str | None = None
    while True:
        response = (
            yt.playlistItems()
            .list(part="contentDetails", playlistId=playlist_id, maxResults=50, pageToken=page_token)
            .execute()
        )
        ids.extend(item["contentDetails"]["videoId"] for item in response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return ids


def fetch_videos(yt: YouTubeResource, ids: list[str]) -> list[Video]:
    """Return the full snippet of each video, in the order of ``ids``.

    Videos that are private to someone else or deleted are missing from the result.
    """
    videos: list[Video] = []
    for i in range(0, len(ids), 50):
        response = yt.videos().list(part="snippet", id=",".join(ids[i : i + 50])).execute()
        videos.extend(response.get("items", []))
    return videos


def update_video(yt: YouTubeResource, video: Video, *, description: str, tags: list[str] | None) -> None:
    """Save a new description, and optionally new tags, keeping the rest of the snippet as it is.

    ``tags=None`` keeps the video's current tags. Each call costs 50 of the 10,000 daily quota units.
    """
    old = video["snippet"]
    snippet = cast("VideoSnippet", {k: old[k] for k in _KEPT_SNIPPET_FIELDS if k in old})
    snippet["description"] = description
    if tags is not None:
        snippet["tags"] = tags
    yt.videos().update(part="snippet", body={"id": video["id"], "snippet": snippet}).execute()


def is_quota_exceeded(error: HttpError) -> bool:
    """Tell whether the API refused a request because the daily quota is used up."""
    return error.status_code == HTTPStatus.FORBIDDEN and "quotaExceeded" in str(error.content)
