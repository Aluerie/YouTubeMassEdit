"""Mass-edit the shared parts of YouTube video descriptions in a playlist."""

import sys

from .cli import main as _main


def main() -> None:
    sys.exit(_main())
