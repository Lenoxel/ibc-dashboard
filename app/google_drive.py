from urllib.parse import parse_qs, urlparse
import re
import urllib.request


def _extract_drive_file_id(url):
    if not url:
        return None

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if "id" in query:
        return query["id"][0]

    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)

    return None


def download_google_drive_image(url):
    if not url:
        return None

    file_id = _extract_drive_file_id(url)

    if not file_id:
        print(f"It was NOT possible to extract the Drive file ID from URL: {url}")
        return None

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )

        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print(f"Error downloading image from Google Drive: {e}")
        return None
