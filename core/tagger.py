"""
ID3 Tagger module for PL Downloader.
Embeds metadata and album artwork into MP3 files using Mutagen.
"""
import os
import urllib.request
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, APIC, ID3NoHeaderError

def set_mp3_tags(
    file_path: str,
    title: str,
    artist: str,
    album: str = "",
    track_num: int = 1,
    total_tracks: int = 1,
    cover_url: str = ""
):
    """
    Applies ID3v2.3 tags and embeds album artwork into an MP3 file.
    """
    if not os.path.exists(file_path):
        return

    try:
        audio = MP3(file_path, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(file_path)
        audio.add_tags()

    tags = audio.tags

    # Set metadata tags
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    if album:
        tags.add(TALB(encoding=3, text=album))
    if total_tracks > 1:
        tags.add(TRCK(encoding=3, text=f"{track_num}/{total_tracks}"))
    else:
        tags.add(TRCK(encoding=3, text=str(track_num)))

    # Fetch and attach album cover if available
    if cover_url:
        try:
            req = urllib.request.Request(
                cover_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                image_data = resp.read()
                mime = "image/jpeg"
                if cover_url.lower().endswith(".png"):
                    mime = "image/png"
                
                tags.add(APIC(
                    encoding=3,
                    mime=mime,
                    type=3,  # Front cover
                    desc="Cover",
                    data=image_data
                ))
        except Exception:
            # Non-fatal if cover fetch fails
            pass

    audio.save(v2_version=3)
