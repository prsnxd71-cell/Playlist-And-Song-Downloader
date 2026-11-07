"""
YouTube and YouTube Music extractor for PL Downloader.
Extracts playlist details and performs smart search with multi-tier video fallback.
"""
import re
from typing import Dict, List, Optional
import yt_dlp

def clean_track_title(title: str) -> str:
    """
    Cleans noisy tags like (feat. ...), [Official Video], (Remastered 2021), etc.
    to maximize YouTube search accuracy.
    """
    if not title:
        return ""
    # Remove parenthesized extras like feat, with, remastered, deluxe, version, etc.
    cleaned = re.sub(
        r"[\(\[](?:feat\.|featuring|with|remaster|remastered|deluxe|version|radio edit|official|bonus).*?[\)\]]",
        "",
        title,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or title

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

def find_best_youtube_matches(
    search_query: str,
    artist: str = "",
    title: str = "",
    expected_duration_ms: int = 0
) -> List[Dict]:
    """
    Searches YouTube for candidate matches.
    Returns an ordered list of candidates:
    1. Highest priority: exact duration match (±15s) with official audio/video.
    2. Medium priority: music video (±60s).
    3. Fallback: Top YouTube video search results to convert video to MP3.
    """
    clean_title = clean_track_title(title)
    clean_art = artist.split(",")[0].strip() if artist else ""

    # Generate tiered search queries
    queries = []
    if clean_art and clean_title:
        queries.append(f"ytsearch5:{clean_art} - {clean_title} Official Audio")
        queries.append(f"ytsearch5:{clean_art} - {clean_title} Official Music Video")
        queries.append(f"ytsearch5:{clean_art} {clean_title}")
    queries.append(f"ytsearch5:{search_query}")

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    expected_sec = expected_duration_ms / 1000.0 if expected_duration_ms > 0 else 0
    all_candidates: List[Dict] = []
    seen_ids = set()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for q in queries:
            try:
                res = ydl.extract_info(q, download=False)
                entries = res.get("entries") or []
                
                for entry in entries:
                    if not entry:
                        continue
                    vid_id = entry.get("id")
                    if not vid_id or vid_id in seen_ids:
                        continue
                    
                    seen_ids.add(vid_id)
                    v_duration = entry.get("duration") or 0
                    diff = abs(v_duration - expected_sec) if expected_sec > 0 else 0

                    candidate = {
                        "id": vid_id,
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "title": entry.get("title") or "",
                        "duration": v_duration,
                        "diff": diff
                    }
                    all_candidates.append(candidate)

                    # If we found an ideal match (diff <= 10s), stop early
                    if expected_sec > 0 and diff <= 10:
                        break
            except Exception:
                continue

            if all_candidates and expected_sec > 0:
                # If we found at least one close match, no need to run lower tier queries
                if any(c["diff"] <= 15 for c in all_candidates):
                    break

    if not all_candidates:
        return []

    # Sort candidates: closest duration diff first, while keeping videos under 20 mins
    valid_length = [c for c in all_candidates if c["duration"] < 1200 or expected_sec >= 1200]
    sorted_candidates = sorted(valid_length or all_candidates, key=lambda x: x["diff"])
    return sorted_candidates

def find_best_youtube_match(
    search_query: str,
    artist: str = "",
    title: str = "",
    expected_duration_ms: int = 0
) -> Optional[Dict]:
    """
    Returns the single best YouTube match for a song.
    Guaranteed to return a video candidate if YouTube has any results.
    """
    candidates = find_best_youtube_matches(
        search_query=search_query,
        artist=artist,
        title=title,
        expected_duration_ms=expected_duration_ms
    )
    return candidates[0] if candidates else None
