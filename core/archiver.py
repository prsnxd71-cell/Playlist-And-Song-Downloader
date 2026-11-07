"""
ZIP Archiver module for PL Downloader.
Packages all downloaded MP3s into a single ZIP file and cleans up temporary files.
"""
import os
import shutil
import zipfile
from typing import List, Callable, Optional, Dict
from .downloader import sanitize_filename

def create_playlist_zip(
    mp3_files: List[str],
    playlist_title: str,
    output_dir: str,
    cleanup_temp_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict], None]] = None
) -> str:
    """
    Compresses all downloaded MP3 files into a single <playlist_title>.zip archive.
    
    Returns the absolute path of the generated ZIP file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    safe_title = sanitize_filename(playlist_title) or "Playlist"
    zip_filename = f"{safe_title}.zip"
    zip_path = os.path.join(output_dir, zip_filename)

    # Avoid overwriting by adding index if file exists
    counter = 1
    while os.path.exists(zip_path):
        zip_path = os.path.join(output_dir, f"{safe_title} ({counter}).zip")
        counter += 1

    total_files = len(mp3_files)
    
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, file_path in enumerate(mp3_files):
            if not os.path.isfile(file_path):
                continue
            
            arcname = os.path.basename(file_path)
            zf.write(file_path, arcname=arcname)
            
            if progress_callback:
                pct = ((idx + 1) / total_files) * 100
                progress_callback({
                    "status": "zipping",
                    "percentage": pct,
                    "message": f"Archiving: {idx + 1}/{total_files} ({arcname})"
                })

    # Optional cleanup of raw temp directory
    if cleanup_temp_dir and os.path.isdir(cleanup_temp_dir):
        try:
            shutil.rmtree(cleanup_temp_dir, ignore_errors=True)
        except Exception:
            pass

    return zip_path
