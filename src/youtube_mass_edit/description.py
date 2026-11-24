"""Rewrite the shared parts of a YouTube video description."""

import re
from dataclasses import dataclass

# YouTube's limit is 5000 bytes of UTF-8, not 5000 characters, so emoji count extra.
MAX_DESCRIPTION_BYTES = 5000

# One or more lines at the very end made only of hashtags, like "#hitless #sekiro".
# "# Heading" lines don't match because a hashtag needs a word character right after "#".
_TRAILING_HASHTAGS_RE = re.compile(r"(?:\s*^[ \t]*#\w+(?:[ \t]+#\w+)*[ \t]*$)+\s*\Z", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class Template:
    """The shared text that every video in the playlist should carry.

    ``start_heading`` and ``end_heading`` are words that appear in the heading lines (lines starting
    with ``#``) around the shared block. Everything from the start heading up to, but not including,
    the end heading is replaced with ``shared_block``. The hashtag line at the very end of the
    description is replaced with ``hashtags``.
    """

    start_heading: str
    end_heading: str
    shared_block: str
    hashtags: str

    def _block_re(self) -> re.Pattern[str]:
        start = re.escape(self.start_heading)
        end = re.escape(self.end_heading)
        return re.compile(rf"^#[^\n]*{start}.*?(?=^#[^\n]*{end})", re.MULTILINE | re.DOTALL)

    def rewrite(self, description: str) -> str | None:
        """Return ``description`` with the shared block and hashtags replaced.

        Returns ``None`` when the description doesn't contain both headings, so the caller can skip
        the video instead of guessing where the shared text should go.
        """
        match = self._block_re().search(description)
        if match is None:
            return None

        head = description[: match.start()]
        tail = description[match.end() :]
        result = f"{head}{self.shared_block.strip()}\n\n{tail}"

        result = _TRAILING_HASHTAGS_RE.sub("", result).rstrip()
        if self.hashtags.strip():
            result = f"{result}\n\n{self.hashtags.strip()}"
        return result


def validation_errors(description: str) -> list[str]:
    """List the reasons YouTube would reject ``description``; empty when it is acceptable."""
    errors: list[str] = []
    size = len(description.encode())
    if size > MAX_DESCRIPTION_BYTES:
        errors.append(f"description is {size} bytes, over YouTube's {MAX_DESCRIPTION_BYTES}-byte limit")
    if "<" in description or ">" in description:
        errors.append("description contains '<' or '>', which YouTube doesn't allow")
    return errors
