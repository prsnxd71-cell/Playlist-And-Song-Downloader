@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   Playlist and Song Downloader - Windows MSI Builder    
echo ========================================================
echo.

:: 1. Ensure dist executable exists
if not exist "dist\Playlist_And_Song_Downloader.exe" (
    echo [Info] dist\Playlist_And_Song_Downloader.exe not found. Compiling first...
    call build_exe.bat
)

:: 2. Locate WiX compiler tools
set WIX_DIR=tools\wix
if not exist "%WIX_DIR%\candle.exe" (
    if exist "%LOCALAPPDATA%\Temp\wix311\candle.exe" (
        set WIX_DIR=%LOCALAPPDATA%\Temp\wix311
    ) else (
        echo [ERROR] WiX tools not found in tools\wix or Temp.
        pause
        exit /b 1
    )
)

:: 3. Prepare object directory
mkdir "build\installer" 2>nul

echo [1/2] Compiling WiX configuration (candle)...
"%WIX_DIR%\candle.exe" -arch x64 -out "build\installer\PlaylistAndSongDownloader.wixobj" "installer\PlaylistAndSongDownloader.wxs"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Candle compilation failed!
    pause
    exit /b %ERRORLEVEL%
)

echo [2/2] Linking MSI Package with real EULA (light)...
"%WIX_DIR%\light.exe" -sice:ICE91 -ext WixUIExtension -ext WixUtilExtension -out "dist\PlaylistAndSongDownloader.msi" "build\installer\PlaylistAndSongDownloader.wixobj"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Light linking failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo SUCCESS! Single Windows Installer created at:
echo          dist\PlaylistAndSongDownloader.msi
echo ========================================================
echo.
pause
