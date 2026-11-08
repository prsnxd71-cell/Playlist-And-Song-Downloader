"""
Professional Desktop GUI for Playlist and Song Downloader.
Built with modern design principles: minimalist aesthetics, clear typography,
and refined visual hierarchy without visual clutter or emoji noise.
"""
import os
import sys
import threading
import queue
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

# Design System Colors
COLOR_BG = "#0d1017"              # Deep obsidian background
COLOR_SURFACE = "#151821"         # Elevated container surface
COLOR_SURFACE_ALT = "#1a1e29"     # Slightly lighter row / card surface
COLOR_BORDER = "#252a38"          # Subtle 1px structural borders
COLOR_ACCENT = "#4f46e5"          # Refined Indigo primary
COLOR_ACCENT_HOVER = "#4338ca"    # Darker Indigo hover
COLOR_SUCCESS = "#10b981"         # Emerald success
COLOR_TEXT_PRIMARY = "#f8fafc"    # High contrast text
COLOR_TEXT_SECONDARY = "#94a3b8"  # Slate secondary text
COLOR_TEXT_MUTED = "#64748b"      # Muted hints and labels

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def format_duration(ms: int) -> str:
    """Formats milliseconds into MM:SS."""
    sec = ms // 1000
    mins = sec // 60
    rem = sec % 60
    return f"{mins}:{rem:02d}"

class PlaylistDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Playlist and Song Downloader")
        self.geometry("960, 720")
        self.minsize(860, 600)
        self.configure(fg_color=COLOR_BG)

        # State variables
        self.playlist_metadata: Optional[Dict] = None
        self.is_downloading = False
        self.cancel_requested = False
        self.downloaded_mp3s: List[str] = []
        self.output_zip_path: Optional[str] = None
        self.track_rows: Dict[int, Dict] = {}
        self.event_queue = queue.Queue()
        self.cover_image: Optional[ctk.CTkImage] = None

        # Settings variables
        default_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        self.selected_output_dir = ctk.StringVar(value=default_downloads)
        self.selected_bitrate = ctk.StringVar(value="192 kbps")

        self._build_ui()
        self._start_queue_listener()
        threading.Thread(target=self._check_background_ffmpeg, daemon=True).start()

    def _check_background_ffmpeg(self):
        from core.ffmpeg_setup import locate_ffmpeg, ensure_ffmpeg
        if not locate_ffmpeg():
            self.event_queue.put(("set_status", ("Setting up engine...", "#eab308")))
            def hook(pct, msg):
                self.event_queue.put(("overall_progress", (int(pct * 100), 100, msg)))
            try:
                ensure_ffmpeg(progress_callback=hook)
                self.event_queue.put(("set_status", ("Ready", "#38bdf8")))
                self.event_queue.put(("overall_progress", (0, 100, "System ready.")))
            except Exception:
                pass

    def _build_ui(self):
        # Main container with outer margin
        main_box = ctk.CTkFrame(self, fg_color="transparent")
        main_box.pack(fill="both", expand=True, padx=24, pady=20)

        # -------------------------------------------------------------
        # 1. TOP HEADER / BRAND BAR
        # -------------------------------------------------------------
        header = ctk.CTkFrame(main_box, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        brand_left = ctk.CTkFrame(header, fg_color="transparent")
        brand_left.pack(side="left")

        app_title = ctk.CTkLabel(
            brand_left,
            text="Playlist and Song Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        app_title.pack(anchor="w")

        app_sub = ctk.CTkLabel(
            brand_left,
            text="Universal Audio Extractor • Zero-Login • Standalone MP3 & ZIP Archive",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_SECONDARY
        )
        app_sub.pack(anchor="w", pady=(2, 0))

        # Status badge pill
        self.status_pill = ctk.CTkLabel(
            header,
            text="Ready",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLOR_SURFACE,
            text_color="#818cf8",
            corner_radius=20,
            padx=14,
            pady=4
        )
        self.status_pill.pack(side="right")

        # -------------------------------------------------------------
        # 2. COMMAND / URL INPUT SECTION
        # -------------------------------------------------------------
        input_card = ctk.CTkFrame(
            main_box,
            fg_color=COLOR_SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        input_card.pack(fill="x", pady=(0, 12))

        input_row = ctk.CTkFrame(input_card, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=12)

        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Paste a Spotify or YouTube share link (Playlist, Album, or Track)...",
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self._fetch_media_clicked())

        paste_btn = ctk.CTkButton(
            input_row,
            text="Paste",
            width=70,
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=COLOR_SURFACE_ALT,
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            command=self._paste_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 8))

        self.fetch_btn = ctk.CTkButton(
            input_row,
            text="Fetch Media",
            width=110,
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._fetch_media_clicked
        )
        self.fetch_btn.pack(side="right")

        # -------------------------------------------------------------
        # 3. MEDIA OVERVIEW & CONFIGURATION BAR
        # -------------------------------------------------------------
        self.overview_card = ctk.CTkFrame(
            main_box,
            fg_color=COLOR_SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        self.overview_card.pack(fill="x", pady=(0, 12))

        overview_inner = ctk.CTkFrame(self.overview_card, fg_color="transparent")
        overview_inner.pack(fill="x", padx=16, pady=12)

        # Left side: Cover art & Title
        left_meta = ctk.CTkFrame(overview_inner, fg_color="transparent")
        left_meta.pack(side="left", fill="x", expand=True)

        self.media_title_lbl = ctk.CTkLabel(
            left_meta,
            text="No Media Loaded",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w"
        )
        self.media_title_lbl.pack(anchor="w")

        self.media_sub_lbl = ctk.CTkLabel(
            left_meta,
            text="Paste a link above to preview tracks and start downloading.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        )
        self.media_sub_lbl.pack(anchor="w", pady=(2, 0))

        # Right side: Quality dropdown & Save path
        right_controls = ctk.CTkFrame(overview_inner, fg_color="transparent")
        right_controls.pack(side="right")

        # Bitrate selector
        bitrate_frame = ctk.CTkFrame(right_controls, fg_color="transparent")
        bitrate_frame.pack(side="left", padx=(0, 12))

        bitrate_label = ctk.CTkLabel(
            bitrate_frame,
            text="Quality",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        bitrate_label.pack(anchor="w")

        self.bitrate_menu = ctk.CTkOptionMenu(
            bitrate_frame,
            values=["128 kbps", "192 kbps", "320 kbps"],
            variable=self.selected_bitrate,
            width=100,
            height=30,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=COLOR_SURFACE_ALT,
            button_color=COLOR_BORDER,
            button_hover_color=COLOR_ACCENT
        )
        self.bitrate_menu.pack()

        # Destination Folder button
        dest_frame = ctk.CTkFrame(right_controls, fg_color="transparent")
        dest_frame.pack(side="left")

        dest_label = ctk.CTkLabel(
            dest_frame,
            text="Output Folder",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        dest_label.pack(anchor="w")

        self.dest_btn = ctk.CTkButton(
            dest_frame,
            text="Browse...",
            width=90,
            height=30,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=COLOR_SURFACE_ALT,
            hover_color=COLOR_BORDER,
            command=self._choose_output_dir
        )
        self.dest_btn.pack()

        # -------------------------------------------------------------
        # 4. TRACK TABLE SECTION
        # -------------------------------------------------------------
        table_container = ctk.CTkFrame(
            main_box,
            fg_color=COLOR_SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        table_container.pack(fill="both", expand=True, pady=(0, 12))

        # Table Header
        tbl_hdr = ctk.CTkFrame(table_container, fg_color=COLOR_SURFACE_ALT, corner_radius=0, height=34)
        tbl_hdr.pack(fill="x", padx=1, pady=(1, 0))

        lbl_h_idx = ctk.CTkLabel(tbl_hdr, text="#", width=40, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_MUTED)
        lbl_h_idx.pack(side="left", padx=(8, 0))

        lbl_h_title = ctk.CTkLabel(tbl_hdr, text="TRACK TITLE & ARTIST", anchor="w", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_MUTED)
        lbl_h_title.pack(side="left", fill="x", expand=True, padx=12)

        lbl_h_dur = ctk.CTkLabel(tbl_hdr, text="TIME", width=65, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_MUTED)
        lbl_h_dur.pack(side="left", padx=(0, 16))

        lbl_h_stat = ctk.CTkLabel(tbl_hdr, text="STATUS", width=120, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_MUTED)
        lbl_h_stat.pack(side="right", padx=(0, 16))

        # Scrollable Track Frame
        self.track_scroll_frame = ctk.CTkScrollableFrame(
            table_container,
            fg_color="transparent",
            corner_radius=0
        )
        self.track_scroll_frame.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        # Initial Empty State
        self._show_empty_table_state()

        # -------------------------------------------------------------
        # 5. FOOTER ACTION & PROGRESS BAR
        # -------------------------------------------------------------
        footer_card = ctk.CTkFrame(
            main_box,
            fg_color=COLOR_SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER
        )
        footer_card.pack(fill="x")

        footer_inner = ctk.CTkFrame(footer_card, fg_color="transparent")
        footer_inner.pack(fill="x", padx=16, pady=12)

        # Left side: Progress details
        progress_left = ctk.CTkFrame(footer_inner, fg_color="transparent")
        progress_left.pack(side="left", fill="x", expand=True, padx=(0, 20))

        self.overall_label = ctk.CTkLabel(
            progress_left,
            text="Ready to begin.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.overall_label.pack(anchor="w", pady=(0, 6))

        self.overall_progress = ctk.CTkProgressBar(
            progress_left,
            height=6,
            corner_radius=3,
            fg_color=COLOR_BG,
            progress_color=COLOR_ACCENT
        )
        self.overall_progress.set(0)
        self.overall_progress.pack(fill="x")

        # Right side: Action Buttons
        actions_right = ctk.CTkFrame(footer_inner, fg_color="transparent")
        actions_right.pack(side="right")

        self.open_file_btn = ctk.CTkButton(
            actions_right,
            text="Open Folder",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=COLOR_SURFACE_ALT,
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            height=36,
            width=100,
            state="disabled",
            command=self._open_output_zip
        )
        self.open_file_btn.pack(side="left", padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            actions_right,
            text="Cancel",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            text_color="#fecaca",
            height=36,
            width=80,
            state="disabled",
            command=self._cancel_download
        )
        self.cancel_btn.pack(side="left", padx=(0, 8))

        self.download_btn = ctk.CTkButton(
            actions_right,
            text="Download All",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            height=36,
            width=130,
            state="disabled",
            command=self._start_download_clicked
        )
        self.download_btn.pack(side="left")

    def _show_empty_table_state(self):
        """Displays a clean empty placeholder in the track list."""
        for w in self.track_scroll_frame.winfo_children():
            w.destroy()

        empty_box = ctk.CTkFrame(self.track_scroll_frame, fg_color="transparent")
        empty_box.pack(expand=True, pady=60)

        lbl_empty_title = ctk.CTkLabel(
            empty_box,
            text="No tracks queued",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        lbl_empty_title.pack()

        lbl_empty_sub = ctk.CTkLabel(
            empty_box,
            text="Enter a playlist or song URL above to inspect tracks and start downloading.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_BORDER
        )
        lbl_empty_sub.pack(pady=(4, 0))

    def _paste_clipboard(self):
        try:
            txt = self.clipboard_get().strip()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, txt)
        except Exception:
            pass

    def _choose_output_dir(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.selected_output_dir.get())
        if folder:
            self.selected_output_dir.set(folder)
            display_folder = os.path.basename(folder) or folder
            self.dest_btn.configure(text=f"{display_folder[:12]}...")

    def _set_status(self, text: str, color: str = "#818cf8"):
        self.status_pill.configure(text=text, text_color=color)

    def _fetch_media_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Empty URL", "#f87171")
            return

        parsed = parse_url(url)
        if parsed.get("platform") not in [PLATFORM_SPOTIFY, PLATFORM_YOUTUBE]:
            self._set_status("Invalid URL", "#f87171")
            self.media_sub_lbl.configure(
                text="Please provide a valid Spotify or YouTube playlist/track URL.",
                text_color="#f87171"
            )
            return

        self.fetch_btn.configure(state="disabled")
        self._set_status("Fetching...", "#fbbf24")
        self.media_sub_lbl.configure(text="Extracting track information without authentication...", text_color=COLOR_TEXT_MUTED)

        threading.Thread(target=self._fetch_media_worker, args=(url, parsed), daemon=True).start()

    def _fetch_media_worker(self, url: str, parsed: Dict):
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

        # Calculate total duration estimate
        total_ms = sum(t.get("duration_ms", 0) for t in tracks)
        dur_str = f" • ~{total_ms // 60000} mins" if total_ms > 0 else ""

        self.media_title_lbl.configure(text=title)
        self.media_sub_lbl.configure(
            text=f"{total} {'track' if total == 1 else 'tracks'}{dur_str} • Ready for export",
            text_color=COLOR_TEXT_SECONDARY
        )
        self._set_status("Ready", "#10b981")
        self.download_btn.configure(state="normal")
        self.fetch_btn.configure(state="normal")

        # Clear table
        for widget in self.track_scroll_frame.winfo_children():
            widget.destroy()
        self.track_rows.clear()

        # Render rows
        for i, track in enumerate(tracks, 1):
            row_bg = COLOR_SURFACE if (i % 2 == 1) else COLOR_SURFACE_ALT
            row = ctk.CTkFrame(self.track_scroll_frame, fg_color=row_bg, corner_radius=6, height=36)
            row.pack(fill="x", pady=1, padx=4)

            # Index
            idx_lbl = ctk.CTkLabel(
                row,
                text=f"{i:02d}",
                width=36,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=COLOR_TEXT_MUTED
            )
            idx_lbl.pack(side="left", padx=(8, 4), pady=6)

            # Title & Artist
            t_title = track.get("title", "Unknown Title")
            t_artist = track.get("artist", "Unknown Artist")
            name_box = ctk.CTkFrame(row, fg_color="transparent")
            name_box.pack(side="left", fill="x", expand=True, padx=8, pady=4)

            lbl_title = ctk.CTkLabel(
                name_box,
                text=t_title,
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLOR_TEXT_PRIMARY
            )
            lbl_title.pack(anchor="w")

            lbl_artist = ctk.CTkLabel(
                name_box,
                text=t_artist,
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=COLOR_TEXT_MUTED
            )
            lbl_artist.pack(anchor="w")

            # Duration
            dur_txt = format_duration(track.get("duration_ms", 0))
            dur_lbl = ctk.CTkLabel(
                row,
                text=dur_txt,
                width=65,
                anchor="e",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=COLOR_TEXT_MUTED
            )
            dur_lbl.pack(side="left", padx=(0, 16), pady=6)

            # Status badge
            status_lbl = ctk.CTkLabel(
                row,
                text="Queued",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=COLOR_TEXT_MUTED,
                width=110,
                anchor="e"
            )
            status_lbl.pack(side="right", padx=(4, 16), pady=6)

            self.track_rows[i] = {
                "status_lbl": status_lbl,
                "title_lbl": lbl_title
            }

        self.overall_label.configure(text=f"Loaded {total} {'track' if total == 1 else 'tracks'}. Click 'Download All' to proceed.")
        self.overall_progress.set(0)

    def _start_download_clicked(self):
        if not self.playlist_metadata or not self.playlist_metadata.get("tracks"):
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.configure(state="disabled")
        self.fetch_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.open_file_btn.configure(state="disabled")
        self._set_status("Downloading", "#38bdf8")

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _cancel_download(self):
        self.cancel_requested = True
        self.cancel_btn.configure(state="disabled")
        self._set_status("Stopping...", "#f87171")

    def _download_worker(self):
        tracks = self.playlist_metadata.get("tracks", [])
        total = len(tracks)
        playlist_title = self.playlist_metadata.get("title", "Media")
        out_dir = self.selected_output_dir.get()
        bitrate_val = self.selected_bitrate.get().split()[0]  # '192 kbps' -> '192'

        temp_dir = os.path.join(out_dir, f"_temp_{sanitize_filename(playlist_title)}")
        os.makedirs(temp_dir, exist_ok=True)

        downloaded = []

        for idx, track in enumerate(tracks, 1):
            if self.cancel_requested:
                break

            self.event_queue.put(("track_status", (idx, "Downloading", "#38bdf8")))
            self.event_queue.put(("overall_progress", (idx - 1, total, f"Downloading [{idx}/{total}]: {track.get('title')}")))

            def prog_hook(p):
                status = p.get("status")
                if status == "converting":
                    self.event_queue.put(("track_status", (idx, "Transcoding", "#fbbf24")))
                elif status == "fallback":
                    self.event_queue.put(("track_status", (idx, "Video Fallback", "#c084fc")))
                elif status == "tagging":
                    self.event_queue.put(("track_status", (idx, "Tagging", "#818cf8")))

            try:
                mp3_path = download_track(
                    track_info=track,
                    output_dir=temp_dir,
                    track_num=idx,
                    total_tracks=total,
                    bitrate=bitrate_val,
                    progress_callback=prog_hook
                )
                downloaded.append(mp3_path)
                self.event_queue.put(("track_status", (idx, "Completed", "#10b981")))
            except Exception as e:
                self.event_queue.put(("track_status", (idx, "Skipped", "#f87171")))

        if self.cancel_requested:
            self.event_queue.put(("download_cancelled", (temp_dir, len(downloaded))))
            return

        if not downloaded:
            self.event_queue.put(("download_failed", "No audio tracks could be downloaded."))
            return

        # Zipping phase
        self.event_queue.put(("overall_progress", (total, total, "Packaging MP3 files into ZIP archive...")))
        self.event_queue.put(("set_status", ("Archiving", "#c084fc")))

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
            os.system(f'explorer /select,"{os.path.abspath(self.output_zip_path)}"')
        else:
            out_folder = self.selected_output_dir.get()
            if os.path.exists(out_folder):
                os.startfile(out_folder)

    def _start_queue_listener(self):
        try:
            while not self.event_queue.empty():
                evt, data = self.event_queue.get_nowait()
                if evt == "fetch_success":
                    self._populate_tracks(data)
                elif evt == "fetch_error":
                    self.fetch_btn.configure(state="normal")
                    self._set_status("Error", "#f87171")
                    self.media_sub_lbl.configure(text=f"Failed to load: {data}", text_color="#f87171")
                elif evt == "track_status":
                    idx, text, color = data
                    if idx in self.track_rows:
                        self.track_rows[idx]["status_lbl"].configure(text=text, text_color=color)
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
                    self.open_file_btn.configure(state="normal")
                    self.overall_progress.set(1.0)
                    self._set_status("Completed", "#10b981")
                    file_size_mb = os.path.getsize(data) / (1024 * 1024)
                    self.overall_label.configure(
                        text=f"Saved: {os.path.basename(data)} ({file_size_mb:.1f} MB)"
                    )
                elif evt == "download_cancelled":
                    temp_dir, count = data
                    self.is_downloading = False
                    self.download_btn.configure(state="normal")
                    self.fetch_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self._set_status("Cancelled", "#f87171")
                    self.overall_label.configure(text=f"Download cancelled ({count} tracks downloaded).")
                elif evt == "download_failed":
                    self.is_downloading = False
                    self.download_btn.configure(state="normal")
                    self.fetch_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self._set_status("Failed", "#f87171")
                    self.overall_label.configure(text=f"Error: {data}")
        except Exception:
            pass

        self.after(80, self._start_queue_listener)

def run_app():
    app = PlaylistDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    run_app()
