"""
Modern Desktop GUI for PL Downloader using CustomTkinter.
Provides a dark-themed, responsive interface with real-time download tracking.
"""
import os
import sys
import threading
import queue
import webbrowser
from typing import Dict, List, Optional
import customtkinter as ctk
from PIL import Image
import urllib.request
import io

from core import (
    parse_url,
    fetch_spotify_metadata,
    fetch_youtube_metadata,
    download_track,
    create_playlist_zip,
    sanitize_filename,
    PLATFORM_SPOTIFY,
    PLATFORM_YOUTUBE
)

# App Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PLDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Playlist and Song Downloader")
        self.geometry("900, 700")
        self.minsize(800, 600)

        # State variables
        self.playlist_metadata: Optional[Dict] = None
        self.is_downloading = False
        self.cancel_requested = False
        self.downloaded_mp3s: List[str] = []
        self.output_zip_path: Optional[str] = None
        self.track_row_labels: Dict[int, ctk.CTkLabel] = {}
        self.event_queue = queue.Queue()

        # Default output directory: User's Downloads folder
        default_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        self.selected_output_dir = ctk.StringVar(value=default_downloads)
        self.selected_bitrate = ctk.StringVar(value="192")

        self._build_ui()
        self._start_queue_listener()
        threading.Thread(target=self._check_background_ffmpeg, daemon=True).start()

    def _check_background_ffmpeg(self):
        from core.ffmpeg_setup import locate_ffmpeg, ensure_ffmpeg
        if not locate_ffmpeg():
            self.event_queue.put(("set_status", ("Setting up engine...", "#fbbf24")))
            def hook(pct, msg):
                self.event_queue.put(("overall_progress", (int(pct*100), 100, msg)))
            try:
                ensure_ffmpeg(progress_callback=hook)
                self.event_queue.put(("set_status", ("Ready", "#38bdf8")))
                self.event_queue.put(("overall_progress", (0, 100, "Ready!")))
            except Exception:
                pass

    def _build_ui(self):
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#18181b")
        header_frame.pack(fill="x", padx=16, pady=(16, 8))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="⚡ Playlist and Song Downloader",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#f4f4f5"
        )
        title_lbl.pack(side="left", padx=16, pady=12)

        subtitle_lbl = ctk.CTkLabel(
            header_frame,
            text="Privacy-First • No Login • Direct MP3 & ZIP Downloader",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        )
        subtitle_lbl.pack(side="left", padx=(0, 16), pady=12)

        self.status_badge = ctk.CTkLabel(
            header_frame,
            text="Ready",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27272a",
            text_color="#38bdf8",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.status_badge.pack(side="right", padx=16, pady=12)

        # 2. Input & URL Frame
        input_frame = ctk.CTkFrame(self, corner_radius=12)
        input_frame.pack(fill="x", padx=16, pady=8)

        self.url_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Paste Spotify or YouTube playlist or single song share link here...",
            height=42,
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(16, 8), pady=12)

        paste_btn = ctk.CTkButton(
            input_frame,
            text="📋 Paste",
            width=80,
            height=42,
            fg_color="#3f3f46",
            hover_color="#52525b",
            command=self._paste_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 8), pady=12)

        self.fetch_btn = ctk.CTkButton(
            input_frame,
            text="🔍 Fetch Media",
            width=130,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._fetch_playlist_clicked
        )
        self.fetch_btn.pack(side="right", padx=(0, 16), pady=12)

        # 3. Settings & Playlist Info Bar
        info_bar = ctk.CTkFrame(self, corner_radius=12)
        info_bar.pack(fill="x", padx=16, pady=4)

        self.playlist_info_label = ctk.CTkLabel(
            info_bar,
            text="Enter a playlist or song link above and click 'Fetch Media'.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e4e4e7"
        )
        self.playlist_info_label.pack(side="left", padx=16, pady=10)

        # Bitrate selector
        bitrate_lbl = ctk.CTkLabel(info_bar, text="Quality:", font=ctk.CTkFont(size=12))
        bitrate_lbl.pack(side="left", padx=(20, 6))

        bitrate_menu = ctk.CTkOptionMenu(
            info_bar,
            values=["128", "192", "320"],
            variable=self.selected_bitrate,
            width=85,
            height=28
        )
        bitrate_menu.pack(side="left", padx=(0, 16))

        # Save Folder selector
        folder_btn = ctk.CTkButton(
            info_bar,
            text="📁 Save Location...",
            width=120,
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._choose_output_dir
        )
        folder_btn.pack(side="right", padx=16, pady=8)

        # 4. Scrollable Track List Frame
        self.track_scroll_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=12,
            label_text="Playlist Tracks",
            label_font=ctk.CTkFont(size=13, weight="bold")
        )
        self.track_scroll_frame.pack(fill="both", expand=True, padx=16, pady=8)

        # 5. Bottom Progress & Actions Frame
        bottom_frame = ctk.CTkFrame(self, corner_radius=12)
        bottom_frame.pack(fill="x", padx=16, pady=(4, 16))

        # Overall progress
        self.overall_label = ctk.CTkLabel(
            bottom_frame,
            text="Waiting for playlist or song...",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        )
        self.overall_label.pack(anchor="w", padx=16, pady=(10, 2))

        self.overall_progress = ctk.CTkProgressBar(bottom_frame, height=10)
        self.overall_progress.set(0)
        self.overall_progress.pack(fill="x", padx=16, pady=4)

        # Action Buttons row
        btn_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 12))

        self.open_zip_btn = ctk.CTkButton(
            btn_row,
            text="🎉 Open Downloaded File",
            fg_color="#15803d",
            hover_color="#166534",
            height=38,
            state="disabled",
            command=self._open_output_zip
        )
        self.open_zip_btn.pack(side="left")

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=38,
            width=90,
            state="disabled",
            command=self._cancel_download
        )
        self.cancel_btn.pack(side="right", padx=(8, 0))

        self.download_btn = ctk.CTkButton(
            btn_row,
            text="⬇️ Download & Export ZIP",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=38,
            state="disabled",
            command=self._start_download_clicked
        )
        self.download_btn.pack(side="right")

    def _paste_clipboard(self):
        try:
            clipboard_text = self.clipboard_get().strip()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clipboard_text)
        except Exception:
            pass

    def _choose_output_dir(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.selected_output_dir.get())
        if folder:
            self.selected_output_dir.set(folder)

    def _set_status(self, text: str, color: str = "#38bdf8"):
        self.status_badge.configure(text=text, text_color=color)

    def _fetch_playlist_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Please paste a URL", "#f87171")
            return

        parsed = parse_url(url)
        if parsed.get("platform") not in [PLATFORM_SPOTIFY, PLATFORM_YOUTUBE]:
            self._set_status("Unsupported URL", "#f87171")
            self.playlist_info_label.configure(
                text="❌ Please paste a valid Spotify or YouTube playlist or song link."
            )
            return

        self.fetch_btn.configure(state="disabled")
        self._set_status("Fetching...", "#fbbf24")
        self.playlist_info_label.configure(text="🔍 Resolving playlist metadata without login...")

        threading.Thread(target=self._fetch_playlist_worker, args=(url, parsed), daemon=True).start()

    def _fetch_playlist_worker(self, url: str, parsed: Dict):
        try:
            platform = parsed.get("platform")
            res_type = parsed.get("type")
            res_id = parsed.get("id")

            if platform == PLATFORM_SPOTIFY:
                meta = fetch_spotify_metadata(res_type, res_id)
            else:
                meta = fetch_youtube_metadata(url)

            self.event_queue.put(("fetch_success", meta))
        except Exception as e:
            self.event_queue.put(("fetch_error", str(e)))

    def _populate_tracks(self, meta: Dict):
        self.playlist_metadata = meta
        title = meta.get("title", "Untitled Playlist")
        tracks = meta.get("tracks", [])
        total = len(tracks)

        self.playlist_info_label.configure(
            text=f"🎵 {title} ({total} tracks ready)"
        )
        self._set_status("Loaded", "#4ade80")
        self.download_btn.configure(state="normal")
        self.fetch_btn.configure(state="normal")

        # Clear previous rows
        for widget in self.track_scroll_frame.winfo_children():
            widget.destroy()
        self.track_row_labels.clear()

        # Render rows
        for i, track in enumerate(tracks, 1):
            row = ctk.CTkFrame(self.track_scroll_frame, fg_color="#18181b", corner_radius=6)
            row.pack(fill="x", pady=2, padx=4)

            idx_lbl = ctk.CTkLabel(row, text=f"{i:02d}", width=32, text_color="#71717a")
            idx_lbl.pack(side="left", padx=(8, 4), pady=6)

            title_txt = f"{track.get('title')} — {track.get('artist')}"
            name_lbl = ctk.CTkLabel(row, text=title_txt, anchor="w", font=ctk.CTkFont(size=12))
            name_lbl.pack(side="left", fill="x", expand=True, padx=4, pady=6)

            status_lbl = ctk.CTkLabel(
                row,
                text="⏳ Ready",
                font=ctk.CTkFont(size=11),
                text_color="#94a3b8",
                width=110,
                anchor="e"
            )
            status_lbl.pack(side="right", padx=(4, 12), pady=6)
            self.track_row_labels[i] = status_lbl

        self.overall_label.configure(text=f"Ready to download {total} songs as MP3 and compress to ZIP.")
        self.overall_progress.set(0)

    def _start_download_clicked(self):
        if not self.playlist_metadata or not self.playlist_metadata.get("tracks"):
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.configure(state="disabled")
        self.fetch_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.open_zip_btn.configure(state="disabled")
        self._set_status("Downloading", "#38bdf8")

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _cancel_download(self):
        self.cancel_requested = True
        self.cancel_btn.configure(state="disabled")
        self._set_status("Cancelling...", "#f87171")

    def _download_worker(self):
        tracks = self.playlist_metadata.get("tracks", [])
        total = len(tracks)
        playlist_title = self.playlist_metadata.get("title", "Playlist")
        out_dir = self.selected_output_dir.get()
        bitrate = self.selected_bitrate.get()

        temp_dir = os.path.join(out_dir, f"_temp_{sanitize_filename(playlist_title)}")
        os.makedirs(temp_dir, exist_ok=True)

        downloaded = []

        for idx, track in enumerate(tracks, 1):
            if self.cancel_requested:
                break

            self.event_queue.put(("track_status", (idx, "⬇️ Downloading...", "#38bdf8")))
            self.event_queue.put(("overall_progress", (idx - 1, total, f"Downloading track {idx} of {total}: {track.get('title')}")))

            def prog_hook(p):
                msg = p.get("message", "")
                if p.get("status") == "converting":
                    self.event_queue.put(("track_status", (idx, "🔄 Transcoding", "#fbbf24")))
                elif p.get("status") == "fallback":
                    self.event_queue.put(("track_status", (idx, "🎬 Video to MP3", "#c084fc")))

            try:
                mp3_path = download_track(
                    track_info=track,
                    output_dir=temp_dir,
                    track_num=idx,
                    total_tracks=total,
                    bitrate=bitrate,
                    progress_callback=prog_hook
                )
                downloaded.append(mp3_path)
                self.event_queue.put(("track_status", (idx, "✅ Done", "#4ade80")))
            except Exception as e:
                self.event_queue.put(("track_status", (idx, "⚠️ Skipped", "#f87171")))

        if self.cancel_requested:
            self.event_queue.put(("download_cancelled", (temp_dir, len(downloaded))))
            return

        if not downloaded:
            self.event_queue.put(("download_failed", "No tracks were successfully downloaded."))
            return

        # Zipping phase
        self.event_queue.put(("overall_progress", (total, total, "Compressing all MP3 files into final ZIP archive...")))
        self.event_queue.put(("set_status", ("Zipping", "#c084fc")))

        try:
            zip_path = create_playlist_zip(
                mp3_files=downloaded,
                playlist_title=playlist_title,
                output_dir=out_dir,
                cleanup_temp_dir=temp_dir
            )
            self.event_queue.put(("download_complete", zip_path))
        except Exception as e:
            self.event_queue.put(("download_failed", f"Failed to create ZIP: {e}"))

    def _open_output_zip(self):
        if self.output_zip_path and os.path.exists(self.output_zip_path):
            # Select and reveal in Windows Explorer
            os.system(f'explorer /select,"{os.path.abspath(self.output_zip_path)}"')

    def _start_queue_listener(self):
        try:
            while not self.event_queue.empty():
                evt, data = self.event_queue.get_nowait()
                if evt == "fetch_success":
                    self._populate_tracks(data)
                elif evt == "fetch_error":
                    self.fetch_btn.configure(state="normal")
                    self._set_status("Error", "#f87171")
                    self.playlist_info_label.configure(text=f"❌ Error: {data}")
                elif evt == "track_status":
                    idx, text, color = data
                    if idx in self.track_row_labels:
                        self.track_row_labels[idx].configure(text=text, text_color=color)
                elif evt == "overall_progress":
                    curr, total, msg = data
                    pct = (curr / total) if total > 0 else 0
                    self.overall_progress.set(pct)
                    self.overall_label.configure(text=msg)
                elif evt == "set_status":
                    text, color = data
                    self._set_status(text, color)
                elif evt == "download_complete":
                    self.output_zip_path = data
                    self.is_downloading = False
                    self.download_btn.configure(state="normal")
                    self.fetch_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self.open_zip_btn.configure(state="normal")
                    self.overall_progress.set(1.0)
                    self._set_status("Finished", "#4ade80")
                    file_size_mb = os.path.getsize(data) / (1024 * 1024)
                    self.overall_label.configure(
                        text=f"✅ Done! Created '{os.path.basename(data)}' ({file_size_mb:.1f} MB)"
                    )
                elif evt == "download_cancelled":
                    temp_dir, count = data
                    self.is_downloading = False
                    self.download_btn.configure(state="normal")
                    self.fetch_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self._set_status("Cancelled", "#f87171")
                    self.overall_label.configure(text=f"Download cancelled by user ({count} tracks downloaded).")
                elif evt == "download_failed":
                    self.is_downloading = False
                    self.download_btn.configure(state="normal")
                    self.fetch_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self._set_status("Error", "#f87171")
                    self.overall_label.configure(text=f"❌ {data}")
        except Exception:
            pass

        self.after(100, self._start_queue_listener)

def run_app():
    app = PLDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    run_app()
