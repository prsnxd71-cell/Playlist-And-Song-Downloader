"""
Script to create a GitHub release and upload PLDownloader.msi using the GitHub REST API.
"""
import os
import sys
import json
import urllib.request
import subprocess

REPO = "prsnxd71-cell/PL-Downloader"
TAG = "v1.0.0"
RELEASE_NAME = "PL Downloader v1.0.0"
RELEASE_BODY = """## ⚡ PL Downloader v1.0.0 (Official Windows Release)

### 📦 Installation
Download and run **`PLDownloader.msi`** below.

### ✨ Features
- **1-Click Windows Setup**: Installs directly to user profile without requiring administrator privileges or throwing UAC errors.
- **Desktop & Start Menu Shortcuts**: Ready to launch from Desktop or Start Menu.
- **Zero-Login Playlist Downloads**: Supports Spotify, YouTube Music, and YouTube playlists without any account verification.
- **Automatic Audio Transcoder Setup**: Automatically configures FFmpeg media engine in the background on first run.
- **Automatic Video-to-MP3 Fallback**: Automatically converts YouTube video of songs to MP3 if audio stream is restricted.
- **Full ZIP Export**: Packages all downloaded tracks into `<Playlist_Name>.zip`.
"""

MSI_PATH = os.path.abspath("dist/PLDownloader.msi")

def get_github_token():
    # 1. Try env vars
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token

    # 2. Try git credential fill
    try:
        proc = subprocess.Popen(
            ["git", "credential", "fill"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, _ = proc.communicate("host=github.com\nprotocol=https\n")
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print("Git credential error:", e)

    return None

def main():
    if not os.path.isfile(MSI_PATH):
        print(f"Error: MSI file not found at {MSI_PATH}")
        sys.exit(1)

    token = get_github_token()
    if not token:
        print("Error: Could not retrieve GitHub authentication token.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PL-Downloader-Release-Bot"
    }

    # 1. Check if release already exists
    release_url = f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}"
    req = urllib.request.Request(release_url, headers=headers)
    release_data = None
    try:
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
            print(f"Release {TAG} already exists (ID: {release_data['id']})")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Release {TAG} not found, creating new release...")
        else:
            print("HTTP error checking release:", e)

    # 2. Create release if not found
    if not release_data:
        create_url = f"https://api.github.com/repos/{REPO}/releases"
        payload = {
            "tag_name": TAG,
            "target_commitish": "main",
            "name": RELEASE_NAME,
            "body": RELEASE_BODY,
            "draft": False,
            "prerelease": False
        }
        req = urllib.request.Request(
            create_url,
            data=json.dumps(payload).encode(),
            headers={**headers, "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
            print(f"Successfully created release {TAG} (ID: {release_data['id']})")

    # 3. Upload PLDownloader.msi asset
    upload_url_template = release_data["upload_url"] # e.g. "https://uploads.github.com/repos/.../assets{?name,label}"
    base_upload_url = upload_url_template.split("{")[0]
    asset_name = "PLDownloader.msi"
    upload_url = f"{base_upload_url}?name={asset_name}"

    # Check existing assets to avoid conflict
    for asset in release_data.get("assets", []):
        if asset["name"] == asset_name:
            print(f"Deleting existing asset {asset_name} (ID: {asset['id']})...")
            del_url = f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}"
            del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
            with urllib.request.urlopen(del_req) as del_resp:
                pass
            break

    print(f"Uploading {asset_name} ({os.path.getsize(MSI_PATH) / (1024*1024):.1f} MB)...")
    with open(MSI_PATH, "rb") as f:
        msi_bytes = f.read()

    upload_req = urllib.request.Request(
        upload_url,
        data=msi_bytes,
        headers={
            **headers,
            "Content-Type": "application/x-msi",
            "Content-Length": str(len(msi_bytes))
        },
        method="POST"
    )

    with urllib.request.urlopen(upload_req) as resp:
        asset_info = json.loads(resp.read().decode())
        print(f"Successfully uploaded {asset_name}!")
        print(f"Asset Download URL: {asset_info.get('browser_download_url')}")
        print(f"Release Page: {release_data.get('html_url')}")

if __name__ == "__main__":
    main()
