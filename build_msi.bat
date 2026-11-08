@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo       PL Downloader - Windows MSI Installer Builder      
echo ========================================================
echo.

:: 1. Ensure dist executable exists
if not exist "dist\PL_Downloader.exe" (
    echo [Info] dist\PL_Downloader.exe not found. Compiling first...
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
"%WIX_DIR%\candle.exe" -arch x64 -out "build\installer\PLDownloader.wixobj" "installer\PLDownloader.wxs"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Candle compilation failed!
    pause
    exit /b %ERRORLEVEL%
)

echo [2/2] Linking MSI Package (light)...
"%WIX_DIR%\light.exe" -ext WixUIExtension -ext WixUtilExtension -out "dist\PLDownloader.msi" "build\installer\PLDownloader.wixobj"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Light linking failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo SUCCESS! Single Windows Installer created at:
echo          dist\PLDownloader.msi
echo ========================================================
echo.
pause
