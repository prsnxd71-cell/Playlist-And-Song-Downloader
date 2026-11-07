"""
Audio Downloader & Transcoder for PL Downloader.
Downloads streams via yt-dlp, transcodes to MP3 via FFmpeg, and tags the file.
Includes automatic multi-candidate fallback to convert YouTube video of songs to MP3.
"""
import os
import sys
import re
import shutil
from typing import Dict, Callable, Optional, List
import yt_dlp
from .youtube import find_best_youtube_matches
from .tagger import set_mp3_tags

def sanitize_filename(name: str) -> str:
    """Removes invalid characters for Windows filenames."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r'\s+', " ", name).strip()
    return name or "track"

def get_ffmpeg_dir() -> Optional[str]:
    """
    Locates FFmpeg executable directory.
    Checks:
    1. PyInstaller bundled temporary dir (sys._MEIPASS)
    2. Next to the running executable (sys.executable)
    3. Project root directory
    4. System PATH
    """
    # 1. PyInstaller bundled dir
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_ffmpeg = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.isfile(meipass_ffmpeg):
            return sys._MEIPASS

    # 2. Executable directory
    exe_dir = os.path.dirname(sys.executable)
    if os.path.isfile(os.path.join(exe_dir, "ffmpeg.exe")):
        return exe_dir

    # 3. Project directory
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if os.path.isfile(os.path.join(project_dir, "ffmpeg.exe")):
        return project_dir

    # 4. System PATH
    ffmpeg_on_path = shutil.which("ffmpeg")
    if ffmpeg_on_path:
        return os.path.dirname(ffmpeg_on_path)

    return None

def download_track(
    track_info: Dict,
    output_dir: str,
    track_num: int = 1,
    total_tracks: int = 1,
    bitrate: str = "192",
    progress_callback: Optional[Callable[[Dict], None]] = None
) -> str:
    """
    Downloads a single track, converts it to MP3, and applies tags.
    If an audio stream fails (e.g. for Spotify songs), it automatically falls back
    to downloading the YouTube video of that song and converting it to MP3 via FFmpeg.
    
    Returns the absolute path of the generated MP3 file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    title = track_info.get("title", "Unknown Title")
    artist = track_info.get("artist", "Unknown Artist")
    album = track_info.get("album", "")
    cover_url = track_info.get("cover_url", "")
    
    # 1. Format filename
    safe_title = sanitize_filename(title)
    safe_artist = sanitize_filename(artist)
    prefix = f"{track_num:02d}. " if total_tracks > 1 else ""
    base_filename = f"{prefix}{safe_artist} - {safe_title}"
    expected_mp3_path = os.path.join(output_dir, f"{base_filename}.mp3")

    # If already downloaded, skip
    if os.path.isfile(expected_mp3_path) and os.path.getsize(expected_mp3_path) > 1024:
        if progress_callback:
            progress_callback({
                "status": "done",
                "message": f"Already downloaded: {base_filename}.mp3",
                "file_path": expected_mp3_path
            })
        return expected_mp3_path

    outtmpl = os.path.join(output_dir, f"{base_filename}.%(ext)s")
    ffmpeg_dir = get_ffmpeg_dir()

    # Progress hook
    def ytdl_hook(d):
        if not progress_callback:
            return
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes") or 0
            pct = (downloaded / total) * 100
            speed = d.get("_speed_str", "").strip()
            progress_callback({
                "status": "downloading",
                "percentage": pct,
                "speed": speed,
                "message": f"Downloading: {pct:.1f}% ({speed})"
            })
        elif status == "finished":
            progress_callback({
                "status": "converting",
                "message": "Converting to MP3 via FFmpeg..."
            })

    def try_download_stream(source_target: str, format_spec: str) -> bool:
        """Helper to invoke yt-dlp with a given format and convert to MP3."""
        ydl_opts = {
            "format": format_spec,
            "outtmpl": outtmpl,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate,
            }],
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [ytdl_hook],
        }
        if ffmpeg_dir:
            ydl_opts["ffmpeg_location"] = ffmpeg_dir

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([source_target])
            return True
        except Exception:
            return False

    # 2. Collect candidate URLs to try
    candidate_urls: List[str] = []
    
    # Direct YouTube link if provided
    if track_info.get("youtube_url"):
        candidate_urls.append(track_info["youtube_url"])

    # Search candidates on YouTube
    if not candidate_urls:
        if progress_callback:
            progress_callback({
                "status": "searching",
                "message": f"Finding best match for '{artist} - {title}'..."
            })

        matches = find_best_youtube_matches(
            search_query=track_info.get("search_query", f"{artist} - {title}"),
            artist=artist,
            title=title,
            expected_duration_ms=track_info.get("duration_ms", 0)
        )
        for m in matches:
            if m.get("url"):
                candidate_urls.append(m["url"])

    # If still no candidates found, append direct search string
    if not candidate_urls:
        candidate_urls.append(f"ytsearch1:{artist} {title} video")

    # 3. Download attempt with automatic video fallback
    download_success = False
    last_error = None

    for idx, cand_url in enumerate(candidate_urls[:3]):
        # Strategy A: Try audio-first stream
        if try_download_stream(cand_url, "bestaudio/best"):
            download_success = True
            break
        
        # Strategy B: Fallback -> Download video of that song and convert to MP3 with FFmpeg
        if progress_callback:
            progress_callback({
                "status": "fallback",
                "message": f"Converting YouTube video of '{title}' to MP3..."
            })

        if try_download_stream(cand_url, "bestvideo+bestaudio/best"):
            download_success = True
            break

        if try_download_stream(cand_url, "best"):
            download_success = True
            break

    # If all URL candidates failed, try a broad general YouTube search for the song video
    if not download_success:
        if progress_callback:
            progress_callback({
                "status": "fallback",
                "message": f"Final video search fallback for '{artist} - {title}'..."
            })
        broad_search = f"ytsearch1:{artist} {title}"
        if try_download_stream(broad_search, "bestaudio/best") or try_download_stream(broad_search, "best"):
            download_success = True

    # 4. Verify MP3 output
    if not os.path.isfile(expected_mp3_path):
        # Check if yt-dlp generated slightly different filename
        candidates = [f for f in os.listdir(output_dir) if f.startswith(prefix) and f.endswith(".mp3")]
        if candidates:
            expected_mp3_path = os.path.join(output_dir, candidates[0])
        else:
            raise RuntimeError(f"Could not convert song or video to MP3 for '{artist} - {title}'")

    # 5. Inject ID3 tags & Artwork
    if progress_callback:
        progress_callback({
            "status": "tagging",
            "message": "Tagging metadata and cover art..."
        })

    set_mp3_tags(
        file_path=expected_mp3_path,
        title=title,
        artist=artist,
        album=album,
        track_num=track_num,
        total_tracks=total_tracks,
        cover_url=cover_url
    )

    if progress_callback:
        progress_callback({
            "status": "done",
            "message": f"Completed: {base_filename}.mp3",
            "file_path": expected_mp3_path
        })

    return expected_mp3_path
