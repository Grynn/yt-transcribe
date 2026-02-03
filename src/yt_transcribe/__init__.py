"""yt-transcribe: Transcribe and summarize video/audio content with AI."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("yt-transcribe")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
