"""
Playlist and Song Downloader - CLI Test Harness.
Use this script during development to test metadata extraction,
audio downloading, ID3 tagging, and ZIP creation directly from PowerShell/Terminal.
"""
import os
import sys
import argparse
from core import (
    parse_url,
    fetch_spotify_metadata,
    fetch_youtube_metadata,
    download_track,
    create_playlist_zip,
    PLATFORM_SPOTIFY,
    PLATFORM_YOUTUBE
)

def format_duration(ms: int) -> str:
    sec = ms // 1000
    mins = sec // 60
    rem_sec = sec % 60
    return f"{mins}:{rem_sec:02d}"

def main():
    parser = argparse.ArgumentParser(description="Playlist and Song Downloader - Fast CLI Testing Tool")
    parser.add_argument("url", nargs="?", help="Spotify or YouTube playlist/track URL")
    parser.add_argument("--preview", action="store_true", help="Only preview metadata, do not download")
    parser.add_argument("--sample", type=int, default=0, help="Download only first N tracks (e.g. --sample 2)")
    parser.add_argument("--bitrate", default="192", choices=["128", "192", "256", "320"], help="MP3 Bitrate (kbps)")
    parser.add_argument("--outdir", default="downloads", help="Output directory for ZIP file")

    args = parser.parse_args()

    if not args.url:
        print("\n=== Playlist and Song Downloader CLI Test Harness ===")
        args.url = input("Enter Spotify or YouTube playlist/track URL: ").strip()

    if not args.url:
        print("Error: No URL provided.")
        sys.exit(1)

    print(f"\n[1/4] Parsing URL: {args.url}")
    parsed = parse_url(args.url)
    platform = parsed.get("platform")
    res_type = parsed.get("type")
    res_id = parsed.get("id")

    print(f" -> Detected Platform: {platform.upper()} | Type: {res_type} | ID: {res_id}")

    if platform not in [PLATFORM_SPOTIFY, PLATFORM_YOUTUBE]:
        print(f"Error: Unsupported or invalid URL. Only Spotify and YouTube URLs are supported.")
        sys.exit(1)

    print(f"\n[2/4] Fetching metadata (Zero-Login)...")
    try:
        if platform == PLATFORM_SPOTIFY:
            meta = fetch_spotify_metadata(res_type, res_id)
        else:
            meta = fetch_youtube_metadata(args.url)
    except Exception as e:
        print(f"Error fetching playlist details: {e}")
        sys.exit(1)

    title = meta.get("title", "Untitled Playlist")
    tracks = meta.get("tracks", [])
    total_tracks = len(tracks)

    print(f" -> Playlist: '{title}'")
    print(f" -> Total Tracks: {total_tracks}")
    print("\n--- Tracklist Preview ---")
    for i, t in enumerate(tracks[:10]):
        dur = format_duration(t.get("duration_ms", 0))
        print(f" {i+1:02d}. {t.get('artist')} - {t.get('title')} [{dur}]")
    if total_tracks > 10:
        print(f" ... and {total_tracks - 10} more songs.")

    if args.preview:
        print("\n[Preview Complete] No tracks downloaded (--preview flag passed).")
        return

    # Determine tracks to download
    to_download = tracks
    if args.sample > 0 and args.sample < total_tracks:
        print(f"\n[Sample Mode Active] Downloading only first {args.sample} songs...")
        to_download = tracks[:args.sample]

    print(f"\n[3/4] Downloading {len(to_download)} audio tracks...")
    temp_dir = os.path.join(args.outdir, "_temp_raw_mp3")
    os.makedirs(temp_dir, exist_ok=True)

    downloaded_files = []
    
    for idx, track in enumerate(to_download, 1):
        artist = track.get("artist")
        track_title = track.get("title")
        print(f"\n[{idx}/{len(to_download)}] Processing: {artist} - {track_title}")
        
        def cli_progress(p):
            msg = p.get("message", "")
            if msg:
                print(f"    -> {msg}")

        try:
            mp3_path = download_track(
                track_info=track,
                output_dir=temp_dir,
                track_num=idx,
                total_tracks=len(to_download),
                bitrate=args.bitrate,
                progress_callback=cli_progress
            )
            downloaded_files.append(mp3_path)
            print(f"    [OK] Saved: {os.path.basename(mp3_path)}")
        except Exception as e:
            print(f"    [FAILED] Skipped song due to error: {e}")

    if not downloaded_files:
        print("\nError: No tracks were successfully downloaded.")
        sys.exit(1)

    print(f"\n[4/4] Creating ZIP package from {len(downloaded_files)} files...")
    
    def zip_progress(p):
        print(f"    -> {p.get('message')}")

    zip_path = create_playlist_zip(
        mp3_files=downloaded_files,
        playlist_title=title,
        output_dir=args.outdir,
        cleanup_temp_dir=temp_dir,
        progress_callback=zip_progress
    )

    print("\n" + "=" * 50)
    print(f" SUCCESS! Playlist downloaded and zipped:")
    print(f" Path: {os.path.abspath(zip_path)}")
    print(f" Size: {os.path.getsize(zip_path) / (1024 * 1024):.2f} MB")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
