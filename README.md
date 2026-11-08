# ⚡ Playlist and Song Downloader

> **Privacy-First • Zero-Login • Direct MP3 & ZIP Downloader**  
> Download public playlists and individual songs from **Spotify**, **YouTube Music**, and **YouTube** as high-quality MP3s or packaged into a single `.zip` file—with zero user accounts, zero tracking, and no credentials required.

---

## ✨ Features

- 🔒 **100% Privacy & Zero-Login**: No Spotify login, no Google login, and no user data tracked or saved. All metadata resolution is tokenless.
- 🎵 **Playlists & Single Songs**: Works with full Spotify playlists/albums, YouTube Music playlists, and individual song share links.
- 🎯 **Smart Audio Matching & Video Fallback**: Automatically resolves tracks to high-quality audio streams and seamlessly falls back to YouTube video transcoding if audio-only streams are restricted.
- 🏷️ **Automatic ID3 Tagging**: Embeds Song Title, Artist, Album, Track Number, and Cover Art directly into each MP3 file.
- 📦 **Automated ZIP Compression**: Assembles completed tracks into a clean `.zip` archive and cleans up temporary cache files.
- 🖥️ **Modern Desktop UI**: CustomTkinter dark-mode interface with live per-track progress tracking and custom output folder selection.
- 🛠️ **Automatic Media Engine Setup**: Self-healing auto-downloader that fetches and configures portable FFmpeg in the background on first run.

---

## 📦 Windows Installer (`.msi`)

Download the official 1-click installer:
👉 **[PlaylistAndSongDownloader.msi Releases](https://github.com/prsnxd71-cell/PL-Downloader/releases)**

- **Zero Permission / UAC Errors**: Installs cleanly per-user to `%LOCALAPPDATA%\Playlist and Song Downloader` without requiring Administrator privileges.
- **Shortcuts**: Automatically places Desktop and Start Menu shortcuts.
- **Includes Real EULA**: Standard consumer software license agreement.

---

## 🚀 Quick Start (Running from Source)

### 1. Requirements
- Python 3.10+
- FFmpeg (Installed automatically by the app or on system PATH)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Desktop GUI
```bash
python app.py
```
Paste any playlist or song link and click **"Fetch Media"**, then **"Download & Export ZIP"**!

---

## 🧪 Testing During Development

### Method A: Instant 2-Second Preview (No Audio Download)
Inspect track titles, artists, and durations extracted without login:
```bash
python test_cli.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M" --preview
```

### Method B: Fast Sample Download (1 or 2 Songs Only)
Test the entire pipeline (search $\rightarrow$ download $\rightarrow$ MP3 transcode $\rightarrow$ ID3 tags $\rightarrow$ ZIP archive) in 20 seconds:
```bash
python test_cli.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M" --sample 2
```

### Method C: Launch Live GUI
```bash
python app.py
```

---

## 🔨 Building the Windows Standalone Executable (`.exe`)

To compile a portable single-file `Playlist_And_Song_Downloader.exe`:
```cmd
build_exe.bat
```

The compiled binary will be located at:
```
dist/Playlist_And_Song_Downloader.exe
```

---

## 📦 Building the Windows Installer (`.msi`)

To generate the complete, self-contained **Windows Installer (`.msi`)**:
```cmd
build_msi.bat
```

The resulting installer will be created at:
```
dist/PlaylistAndSongDownloader.msi
```
