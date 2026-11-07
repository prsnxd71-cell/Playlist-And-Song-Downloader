# ⚡ PL Downloader (Playlist to ZIP)

> **Privacy-First • Zero-Login • Direct MP3 ZIP**  
> Download public playlists from **Spotify**, **YouTube Music**, and **YouTube** as high-quality MP3s packaged into a single `.zip` file—with zero user accounts, zero tracking, and no credentials required.

---

## ✨ Features

- 🔒 **100% Privacy & Zero-Login**: No Spotify login, no Google login, and no user data tracked or saved. All metadata resolution is tokenless.
- 🎵 **Multi-Platform Support**: Works with Spotify playlists/albums, YouTube Music playlists, and standard YouTube playlists.
- 🎯 **Smart Audio Matching**: Automatically resolves Spotify tracks to the highest quality public audio streams with duration tolerance filtering.
- 🏷️ **Automatic ID3 Tagging**: Embeds Song Title, Artist, Album, Track Number, and Cover Art directly into each MP3 file.
- 📦 **Automated ZIP Compression**: Assembles all completed MP3s into `<Playlist_Name>.zip` and purges raw temp files.
- 🖥️ **Modern Desktop UI**: CustomTkinter dark-mode interface with live per-track progress tracking and custom output folder selection.

---

## 🚀 Quick Start (Running Without Compiling)

### 1. Requirements
- Python 3.10+
- FFmpeg (Installed automatically on Windows or placed in `bin/`)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Desktop GUI
```bash
python app.py
```
Paste any playlist link and click **"Fetch Playlist"**, then **"Download All & Create ZIP"**!

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
Look in the `downloads/` folder for the resulting `.zip`!

### Method C: Launch Live GUI
```bash
python app.py
```

---

## 🔨 Building the Windows Standalone Executable (`.exe`)

To compile a portable single-file `PL_Downloader.exe` that runs on any Windows PC without Python installed:

Simply run the build script:
```cmd
build_exe.bat
```

Or manually with PyInstaller:
```bash
python -m PyInstaller --name "PL_Downloader" --onefile --windowed --collect-all customtkinter --collect-all yt_dlp --collect-all mutagen --add-binary "bin/ffmpeg.exe;." app.py
```

The compiled binary will be located at:
```
dist/PL_Downloader.exe
```

---

## 📦 Building the Windows Installer (`.msi`)

To generate a complete, self-contained **Windows Installer (`.msi`)** that installs PL Downloader with desktop and start menu shortcuts:

Simply double-click:
```cmd
build_msi.bat
```

The resulting installer will be created at:
```
dist/PL_Downloader.msi
```

Users can double-click this `.msi` on any Windows PC to install the software into `Program Files\PL Downloader` with desktop shortcuts and clean uninstall support in Windows Settings.

---

## 📱 Android Roadmap (Phase 2)
- Material 3 Mobile UI (Flutter / Kotlin).
- Native Android Share Sheet receiver ("Share to PL Downloader" from Spotify / YouTube app).
- Direct ZIP save to Android Scoped Storage (`Downloads/`).
