"""
PL Downloader Core Package.
"""
from .parser import parse_url, PLATFORM_SPOTIFY, PLATFORM_YOUTUBE, PLATFORM_UNKNOWN
from .spotify import fetch_spotify_metadata
from .youtube import fetch_youtube_metadata, find_best_youtube_match
from .downloader import download_track, sanitize_filename, get_ffmpeg_dir
from .tagger import set_mp3_tags
from .archiver import create_playlist_zip

__all__ = [
    "parse_url",
    "PLATFORM_SPOTIFY",
    "PLATFORM_YOUTUBE",
    "PLATFORM_UNKNOWN",
    "fetch_spotify_metadata",
    "fetch_youtube_metadata",
    "find_best_youtube_match",
    "download_track",
    "sanitize_filename",
    "get_ffmpeg_dir",
    "set_mp3_tags",
    "create_playlist_zip"
]
