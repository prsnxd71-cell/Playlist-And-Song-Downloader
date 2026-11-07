"""
YouTube and YouTube Music extractor for PL Downloader.
Extracts playlist details and performs smart search for matching audio tracks.
"""
from typing import Dict, List, Optional
import yt_dlp

def fetch_youtube_metadata(url: str) -> Dict:
    """
    Fetches playlist or video metadata using yt-dlp.
    """
    ydl_opts = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch YouTube playlist info: {e}")

    if not info:
        raise RuntimeError("No information returned by YouTube extractor.")

    playlist_title = info.get("title") or "YouTube Playlist"
    entries = info.get("entries") or []

    tracks: List[Dict] = []
    
    # Single video case
    if not entries and "id" in info:
        entries = [info]

    for entry in entries:
        if not entry:
            continue
        
        video_id = entry.get("id") or ""
        title = entry.get("title") or "Unknown Title"
        uploader = entry.get("uploader") or entry.get("channel") or "Unknown Artist"
        duration_sec = entry.get("duration") or 0
        
        # Best thumbnail
        thumbnails = entry.get("thumbnails") or []
        cover_url = thumbnails[-1].get("url") if thumbnails else ""

        # YouTube video URL
        video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

        tracks.append({
            "title": title,
            "artist": uploader,
            "album": playlist_title,
            "duration_ms": duration_sec * 1000,
            "cover_url": cover_url,
            "youtube_id": video_id,
            "youtube_url": video_url,
            "search_query": f"{uploader} - {title}"
        })

    return {
        "title": playlist_title,
        "type": "playlist" if len(tracks) > 1 else "track",
        "cover_url": tracks[0]["cover_url"] if tracks else "",
        "track_count": len(tracks),
        "tracks": tracks
    }

def find_best_youtube_match(search_query: str, expected_duration_ms: int = 0) -> Optional[Dict]:
    """
    Searches YouTube for the best audio stream match for a track.
    Applies duration tolerance check (within 15 seconds) if expected_duration_ms > 0.
    """
    # Prefer official audio / topic tracks
    queries = [
        f"ytsearch3:{search_query} Official Audio",
        f"ytsearch3:{search_query} audio",
        f"ytsearch3:{search_query}"
    ]

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    expected_sec = expected_duration_ms / 1000.0 if expected_duration_ms > 0 else 0

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for q in queries:
            try:
                res = ydl.extract_info(q, download=False)
                entries = res.get("entries") or []
                
                # Check for closest duration match
                best_entry = None
                smallest_diff = float("inf")

                for entry in entries:
                    if not entry:
                        continue
                    v_duration = entry.get("duration") or 0
                    
                    if expected_sec > 0:
                        diff = abs(v_duration - expected_sec)
                        # Tolerance within 15 seconds
                        if diff <= 15:
                            return {
                                "id": entry.get("id"),
                                "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                                "title": entry.get("title"),
                                "duration": v_duration
                            }
                        if diff < smallest_diff:
                            smallest_diff = diff
                            best_entry = entry
                    else:
                        return {
                            "id": entry.get("id"),
                            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                            "title": entry.get("title"),
                            "duration": v_duration
                        }
                
                # If tolerance wasn't strictly met, return the closest non-null entry if diff < 45 seconds
                if best_entry and smallest_diff <= 45:
                    return {
                        "id": best_entry.get("id"),
                        "url": f"https://www.youtube.com/watch?v={best_entry.get('id')}",
                        "title": best_entry.get("title"),
                        "duration": best_entry.get("duration", 0)
                    }

            except Exception:
                continue

    return None
