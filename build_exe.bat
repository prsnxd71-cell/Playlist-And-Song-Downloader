@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   Playlist and Song Downloader - Windows Builder        
echo ========================================================
echo.

:: Check if ffmpeg exists in bin\
if not exist "bin\ffmpeg.exe" (
    echo [Info] Checking for system FFmpeg to bundle...
    for /f "delims=" %%i in ('where ffmpeg.exe 2^>nul') do set FFMPEG_PATH=%%i
    if defined FFMPEG_PATH (
        echo [OK] Found system FFmpeg: !FFMPEG_PATH!
        mkdir bin 2>nul
        copy "!FFMPEG_PATH!" "bin\ffmpeg.exe" >nul
    ) else (
        echo [Warning] ffmpeg.exe not found. App will rely on system PATH at runtime.
    )
)

set BIN_FLAG=
if exist "bin\ffmpeg.exe" (
    set BIN_FLAG=--add-binary "bin/ffmpeg.exe;."
)

echo [1/2] Compiling single-file executable with PyInstaller...
python -m PyInstaller ^
    --name "Playlist_And_Song_Downloader" ^
    --onefile ^
    --windowed ^
    --collect-all customtkinter ^
    --collect-all yt_dlp ^
    --collect-all mutagen ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    !BIN_FLAG! ^
    app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed! Check the log output above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo [2/2] SUCCESS! Executable created at:
echo       dist\Playlist_And_Song_Downloader.exe
echo ========================================================
echo.
pause
