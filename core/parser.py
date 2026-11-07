"""
URL Parser module for PL Downloader.
Identifies streaming platforms and extracts resource IDs and types.
"""
import re
from urllib.parse import urlparse, parse_qs

PLATFORM_SPOTIFY = "spotify"
PLATFORM_YOUTUBE = "youtube"
PLATFORM_UNKNOWN = "unknown"

TYPE_PLAYLIST = "playlist"
TYPE_ALBUM = "album"
TYPE_TRACK = "track"

def parse_url(url: str) -> dict:
    """
    Parses a music URL and returns platform, type, and ID.
    
    Returns:
        {
            "platform": "spotify" | "youtube" | "unknown",
            "type": "playlist" | "album" | "track",
            "id": str,
            "original_url": str
        }
    """
    url = url.strip()
    if not url:
        return {"platform": PLATFORM_UNKNOWN, "type": None, "id": None, "original_url": url}

    # 1. Spotify URI or URL
    if "spotify.com" in url or url.startswith("spotify:"):
        # URI format: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
        uri_match = re.match(r"spotify:(playlist|album|track):([a-zA-Z0-9]+)", url)
        if uri_match:
            return {
                "platform": PLATFORM_SPOTIFY,
                "type": uri_match.group(1),
                "id": uri_match.group(2),
                "original_url": url
            }
        
        # Web URL format: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=...
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) >= 2:
            res_type = path_parts[0]  # playlist, album, track
            res_id = path_parts[1]
            if res_type in ["playlist", "album", "track"]:
                return {
                    "platform": PLATFORM_SPOTIFY,
                    "type": res_type,
                    "id": res_id,
                    "original_url": url
                }

    # 2. YouTube / YouTube Music
    if any(domain in url for domain in ["youtube.com", "youtu.be", "music.youtube.com"]):
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)

        # Check for playlist ID
        if "list" in qs and qs["list"][0]:
            return {
                "platform": PLATFORM_YOUTUBE,
                "type": TYPE_PLAYLIST,
                "id": qs["list"][0],
                "original_url": url
            }
        
        # Check for single video
        if "v" in qs and qs["v"][0]:
            return {
                "platform": PLATFORM_YOUTUBE,
                "type": TYPE_TRACK,
                "id": qs["v"][0],
                "original_url": url
            }
        
        # youtu.be/VIDEO_ID
        if "youtu.be" in parsed.netloc:
            video_id = parsed.path.strip("/")
            if video_id:
                return {
                    "platform": PLATFORM_YOUTUBE,
                    "type": TYPE_TRACK,
                    "id": video_id,
                    "original_url": url
                }

    return {
        "platform": PLATFORM_UNKNOWN,
        "type": None,
        "id": None,
        "original_url": url
    }
