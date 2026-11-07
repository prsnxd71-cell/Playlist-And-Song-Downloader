@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo       PL Downloader - Windows MSI Installer Builder      
echo ========================================================
echo.

:: 1. Ensure dist files exist
if not exist "dist\PL_Downloader.exe" (
    echo [Info] PL_Downloader.exe not found in dist\. Compiling executable first...
    call build_exe.bat
)

if not exist "dist\ffmpeg.exe" (
    if exist "bin\ffmpeg.exe" (
        copy "bin\ffmpeg.exe" "dist\ffmpeg.exe" >nul
    ) else (
        echo [Warning] ffmpeg.exe not found in bin\.
    )
)

if not exist "dist\ffprobe.exe" (
    if exist "bin\ffprobe.exe" (
        copy "bin\ffprobe.exe" "dist\ffprobe.exe" >nul
    )
)

:: 2. Check WiX toolset
set WIX_DIR=tools\wix
if not exist "%WIX_DIR%\candle.exe" (
    if exist "%LOCALAPPDATA%\Temp\wix311\candle.exe" (
        set WIX_DIR=%LOCALAPPDATA%\Temp\wix311
    ) else (
        echo [ERROR] WiX compiler not found in tools\wix or Temp.
        pause
        exit /b 1
    )
)

:: 3. Create build directory for object files
mkdir "build\installer" 2>nul

echo [1/2] Compiling WiX Source File (candle)...
"%WIX_DIR%\candle.exe" -arch x64 -out "build\installer\PL_Downloader.wixobj" "installer\PL_Downloader.wxs"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Candle compilation failed!
    pause
    exit /b %ERRORLEVEL%
)

echo [2/2] Linking MSI Package (light)...
"%WIX_DIR%\light.exe" -ext WixUIExtension -ext WixUtilExtension -out "dist\PL_Downloader.msi" "build\installer\PL_Downloader.wixobj"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Light linking failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo SUCCESS! Windows Installer (.msi) generated at:
echo          dist\PL_Downloader.msi
echo ========================================================
echo.
pause
