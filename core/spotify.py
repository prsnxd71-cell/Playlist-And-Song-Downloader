"""
Tokenless Spotify scraper for PL Downloader.
Extracts playlist, album, and track metadata without requiring user login or API keys.
"""
import json
import re
import urllib.request
import urllib.parse
from typing import Dict, List, Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def clean_text(text: str) -> str:
    """Cleans up special unicode characters and HTML artifacts."""
    if not text:
        return ""
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    text = text.replace("\u00a0", " ").strip()
    return text

def fetch_spotify_metadata(res_type: str, res_id: str) -> Dict:
    """
    Fetches metadata for a Spotify playlist, album, or track without authentication.
    
    Returns:
        {
            "title": str,
            "owner": str,
            "cover_url": str,
            "track_count": int,
            "tracks": [
                {
                    "title": str,
                    "artist": str,
                    "album": str,
                    "duration_ms": int,
                    "cover_url": str,
                    "spotify_id": str,
                    "search_query": str
                }
            ]
        }
    """
    embed_url = f"https://open.spotify.com/embed/{res_type}/{res_id}"
    req = urllib.request.Request(embed_url, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch Spotify embed page: {e}")

    # Extract JSON from __NEXT_DATA__
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        raise RuntimeError("Could not find Spotify metadata payload in embed page.")

    try:
        data = json.loads(match.group(1))
    except Exception as e:
        raise RuntimeError(f"Failed to parse Spotify JSON payload: {e}")

    entity = (
        data.get("props", {})
        .get("pageProps", {})
        .get("state", {})
        .get("data", {})
        .get("entity", {})
    )

    if not entity:
        raise RuntimeError("Spotify entity data is empty or invalid.")

    playlist_title = clean_text(entity.get("name") or entity.get("title") or "Spotify Playlist")
    
    # Extract cover art
    cover_sources = entity.get("coverArt", {}).get("sources", [])
    cover_url = cover_sources[0].get("url") if cover_sources else ""

    # Extract tracks
    track_list_raw = entity.get("trackList", [])
    tracks: List[Dict] = []

    # If it's a single track
    if res_type == "track" and not track_list_raw:
        track_title = clean_text(entity.get("name") or entity.get("title") or "Unknown Track")
        subtitle = clean_text(entity.get("subtitle") or "Unknown Artist")
        duration = entity.get("duration") or 0
        spotify_uri = entity.get("uri") or f"spotify:track:{res_id}"
        spotify_id = spotify_uri.split(":")[-1] if ":" in spotify_uri else res_id
        
        search_query = f"{subtitle} - {track_title}"
        tracks.append({
            "title": track_title,
            "artist": subtitle,
            "album": playlist_title,
            "duration_ms": duration,
            "cover_url": cover_url,
            "spotify_id": spotify_id,
            "search_query": search_query
        })
    else:
        for t in track_list_raw:
            track_title = clean_text(t.get("title") or "")
            artist = clean_text(t.get("subtitle") or "Unknown Artist")
            duration_ms = t.get("duration") or 0
            
            # Track cover art fallback to playlist cover art
            t_cover_sources = t.get("coverArt", {}).get("sources", [])
            t_cover = t_cover_sources[0].get("url") if t_cover_sources else cover_url

            track_uri = t.get("uri") or ""
            track_id = track_uri.split(":")[-1] if ":" in track_uri else ""

            search_query = f"{artist} - {track_title}"

            tracks.append({
                "title": track_title,
                "artist": artist,
                "album": playlist_title,
                "duration_ms": duration_ms,
                "cover_url": t_cover,
                "spotify_id": track_id,
                "search_query": search_query
            })

    return {
        "title": playlist_title,
        "type": res_type,
        "cover_url": cover_url,
        "track_count": len(tracks),
        "tracks": tracks
    }
