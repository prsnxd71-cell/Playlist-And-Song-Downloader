"""
FFmpeg auto-installer and locator for PL Downloader.
Ensures ffmpeg.exe is present; if missing, automatically downloads and extracts it
without requiring user intervention or throwing errors.
"""
import os
import sys
import shutil
import zipfile
import urllib.request
from typing import Optional, Callable

# Fast, official prebuilt static FFmpeg release URLs
FFMPEG_URLS = [
    "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
]

def get_app_local_dir() -> str:
    """Returns the persistent user data directory for Playlist and Song Downloader."""
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    target = os.path.join(local_app_data, "Programs", "Playlist and Song Downloader", "bin")
    os.makedirs(target, exist_ok=True)
    return target

def locate_ffmpeg() -> Optional[str]:
    """
    Checks if ffmpeg.exe exists in any known directory:
    1. PyInstaller bundled temporary dir (sys._MEIPASS)
    2. Next to the running executable
    3. User local app bin folder
    4. Project root bin folder
    5. System PATH
    """
    # 1. PyInstaller bundled dir
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_ffmpeg = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.isfile(meipass_ffmpeg):
            return sys._MEIPASS

    # 2. Next to executable
    exe_dir = os.path.dirname(sys.executable)
    if os.path.isfile(os.path.join(exe_dir, "ffmpeg.exe")):
        return exe_dir
    if os.path.isfile(os.path.join(exe_dir, "bin", "ffmpeg.exe")):
        return os.path.join(exe_dir, "bin")

    # 3. User local app bin directory
    user_bin = get_app_local_dir()
    if os.path.isfile(os.path.join(user_bin, "ffmpeg.exe")):
        return user_bin

    # 4. Project directory
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if os.path.isfile(os.path.join(project_dir, "ffmpeg.exe")):
        return project_dir
    if os.path.isfile(os.path.join(project_dir, "bin", "ffmpeg.exe")):
        return os.path.join(project_dir, "bin")

    # 5. System PATH
    path_bin = shutil.which("ffmpeg")
    if path_bin:
        return os.path.dirname(path_bin)

    return None

def download_and_extract_ffmpeg(
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> str:
    """
    Downloads portable FFmpeg and extracts ffmpeg.exe to the local user directory.
    Returns the directory path containing ffmpeg.exe.
    """
    target_dir = get_app_local_dir()
    final_ffmpeg = os.path.join(target_dir, "ffmpeg.exe")
    
    if os.path.isfile(final_ffmpeg) and os.path.getsize(final_ffmpeg) > 1024:
        return target_dir

    temp_zip = os.path.join(target_dir, "ffmpeg_download.zip")

    last_error = None
    for url in FFMPEG_URLS:
        try:
            if progress_callback:
                progress_callback(0.05, f"Connecting to {url.split('/')[2]}...")

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0
                block_size = 64 * 1024

                with open(temp_zip, "wb") as f_out:
                    while True:
                        chunk = resp.read(block_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and progress_callback:
                            pct = min(0.90, (downloaded / total_size) * 0.90)
                            mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            progress_callback(pct, f"Downloading FFmpeg: {mb:.1f}/{total_mb:.1f} MB ({int(pct*100)}%)")

            if progress_callback:
                progress_callback(0.92, "Extracting FFmpeg binaries...")

            # Extract only ffmpeg.exe and ffprobe.exe from the archive
            with zipfile.ZipFile(temp_zip, "r") as zf:
                for member in zf.namelist():
                    filename = os.path.basename(member)
                    if filename.lower() in ["ffmpeg.exe", "ffprobe.exe"]:
                        with zf.open(member) as source_file:
                            dest_path = os.path.join(target_dir, filename)
                            with open(dest_path, "wb") as target_file:
                                shutil.copyfileobj(source_file, target_file)

            # Clean up zip
            try:
                os.remove(temp_zip)
            except Exception:
                pass

            if os.path.isfile(final_ffmpeg):
                if progress_callback:
                    progress_callback(1.0, "FFmpeg ready!")
                return target_dir

        except Exception as e:
            last_error = e
            try:
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)
            except Exception:
                pass
            continue

    raise RuntimeError(f"Could not automatically download FFmpeg: {last_error}")

def ensure_ffmpeg(progress_callback: Optional[Callable[[float, str], None]] = None) -> str:
    """
    Ensures FFmpeg is available. If not, downloads it seamlessly.
    """
    existing = locate_ffmpeg()
    if existing:
        return existing
    return download_and_extract_ffmpeg(progress_callback)
