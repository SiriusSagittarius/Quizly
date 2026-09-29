import re
from urllib.parse import parse_qs, urlparse

VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')
SHORT_LINK_HOSTS = {'youtu.be', 'www.youtu.be'}
YOUTUBE_HOSTS = {
    'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
}
PATH_ID_PREFIXES = {'shorts', 'embed', 'live'}


def normalize_youtube_url(url):
    """Return the canonical watch URL of a YouTube link, else None."""
    try:
        video_id = extract_video_id(url.strip())
    except ValueError:
        return None
    if video_id is None:
        return None
    return f'https://www.youtube.com/watch?v={video_id}'


def extract_video_id(url):
    """Return the 11 character video id contained in a YouTube URL."""
    if '://' not in url:
        url = f'https://{url}'
    candidate = find_video_id_candidate(urlparse(url))
    if candidate and VIDEO_ID_PATTERN.match(candidate):
        return candidate
    return None


def find_video_id_candidate(parsed_url):
    """Pick the part of a parsed URL that should contain the video id."""
    host = (parsed_url.hostname or '').lower()
    path_parts = [part for part in parsed_url.path.split('/') if part]
    if host in SHORT_LINK_HOSTS:
        return path_parts[0] if path_parts else None
    if host not in YOUTUBE_HOSTS:
        return None
    if parsed_url.path == '/watch':
        return parse_qs(parsed_url.query).get('v', [None])[0]
    if len(path_parts) >= 2 and path_parts[0] in PATH_ID_PREFIXES:
        return path_parts[1]
    return None
