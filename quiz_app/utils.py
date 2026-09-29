import json
import logging
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import groq
import yt_dlp
from django.conf import settings

from quiz_app.api.exceptions import (
    NotEnoughSpeechError,
    QuizGenerationError,
    VideoUnavailableError,
)
from quiz_app.validators import is_valid_question

logger = logging.getLogger(__name__)

QUESTION_COUNT = 10
DOWNLOAD_ATTEMPTS = 2
MIN_TRANSCRIPT_WORDS = 100
MAX_TRANSCRIPT_CHARS = 16_000
MAX_ANSWER_TOKENS = 3_000
AI_TIMEOUT_SECONDS = 120
AI_ERRORS = (groq.APIError, ValueError, TypeError)
VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')
SHORT_LINK_HOSTS = {'youtu.be', 'www.youtu.be'}
YOUTUBE_HOSTS = {
    'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
}
PATH_ID_PREFIXES = {'shorts', 'embed', 'live'}

QUIZ_INSTRUCTIONS = """Du bist ein Quiz-Generator. Der Nutzer schickt dir
das Transkript eines YouTube-Videos. Erstelle daraus ein Multiple-Choice-Quiz.

Regeln:
- Genau 10 Fragen, die sich nur auf Inhalte des Transkripts beziehen.
- Frage nach Aussagen, Fakten und Zusammenhängen aus dem Video, nicht
  nach dem Wortlaut des Transkripts (also keine Fragen wie „Welches Wort
  kommt im Transkript vor?“).
- Jede Frage hat genau 4 unterschiedliche Antwortmöglichkeiten.
- Genau eine Antwortmöglichkeit ist richtig.
- "answer" muss Zeichen für Zeichen einer der 4 Antwortmöglichkeiten
  entsprechen.
- "title" ist ein kurzer, treffender Quiz-Titel (höchstens 60 Zeichen).
- "description" fasst das Thema in einem Satz zusammen
  (höchstens 150 Zeichen).
- Verwende die Sprache des Transkripts.
"""

QUESTION_SCHEMA = {
    'type': 'object',
    'properties': {
        'question_title': {'type': 'string'},
        'question_options': {
            'type': 'array',
            'items': {'type': 'string'},
            'minItems': 4,
            'maxItems': 4,
        },
        'answer': {'type': 'string'},
    },
    'required': ['question_title', 'question_options', 'answer'],
    'additionalProperties': False,
}

QUIZ_SCHEMA = {
    'type': 'object',
    'properties': {
        'title': {'type': 'string'},
        'description': {'type': 'string'},
        'questions': {
            'type': 'array',
            'items': QUESTION_SCHEMA,
            'minItems': QUESTION_COUNT,
            'maxItems': QUESTION_COUNT,
        },
    },
    'required': ['title', 'description', 'questions'],
    'additionalProperties': False,
}

QUIZ_RESPONSE_FORMAT = {
    'type': 'json_schema',
    'json_schema': {'name': 'quiz', 'strict': True, 'schema': QUIZ_SCHEMA},
}


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


def build_download_options(target_dir):
    """Return yt-dlp options that keep only the audio track as mp3.

    A bitrate of 64 kbit/s is enough for speech and keeps videos of about
    50 minutes below the 25 MB upload limit of the Groq free tier.
    """
    return {
        'format': 'bestaudio/best',
        'outtmpl': str(Path(target_dir) / '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'noprogress': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',
        }],
    }


def run_download(video_url, target_dir):
    """Download the audio with yt-dlp and convert it to mp3 via FFmpeg."""
    with yt_dlp.YoutubeDL(build_download_options(target_dir)) as loader:
        video_info = loader.extract_info(video_url, download=True)
    return Path(target_dir) / f"{video_info['id']}.mp3"


def download_audio(video_url, target_dir):
    """Download the audio, retrying because YouTube blocks sporadically."""
    last_error = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            return run_download(video_url, target_dir)
        except yt_dlp.utils.DownloadError as error:
            logger.warning('Download attempt %s failed: %s', attempt, error)
            last_error = error
    raise VideoUnavailableError() from last_error


def transcribe_video(video_url):
    """Download the audio into a temporary folder and transcribe it."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        audio_path = download_audio(video_url, temp_dir)
        return transcribe_audio(audio_path)


def create_ai_client():
    """Create a Groq client that retries on rate limits and overload."""
    return groq.Groq(api_key=settings.GROQ_API_KEY, timeout=AI_TIMEOUT_SECONDS)


def transcribe_audio(audio_path):
    """Transcribe the audio file with Whisper AI hosted on Groq."""
    try:
        with create_ai_client() as client:
            transcription = client.audio.transcriptions.create(
                model=settings.TRANSCRIPTION_MODEL, file=audio_path
            )
    except groq.APIError as error:
        logger.error('Transcription failed: %s', error)
        raise QuizGenerationError() from error
    return transcription.text


def prepare_transcript(transcript):
    """Reject videos with too little speech and shorten long transcripts.

    The Groq free tier allows 8,000 tokens per minute, so the transcript
    is cut after about 16,000 characters (roughly 15 minutes of speech).
    """
    words = transcript.split()
    if len(words) < MIN_TRANSCRIPT_WORDS:
        raise NotEnoughSpeechError()
    return ' '.join(words)[:MAX_TRANSCRIPT_CHARS]


def request_quiz_from_ai(model_name, transcript):
    """Send the transcript to a Groq model and demand a JSON quiz."""
    with create_ai_client() as client:
        return client.chat.completions.create(
            model=model_name,
            messages=[
                {'role': 'system', 'content': QUIZ_INSTRUCTIONS},
                {'role': 'user', 'content': transcript},
            ],
            response_format=QUIZ_RESPONSE_FORMAT,
            reasoning_effort='low',
            max_completion_tokens=MAX_ANSWER_TOKENS,
        )


def request_valid_quiz(model_name, transcript):
    """Return the quiz of one model or raise if it is missing or invalid."""
    completion = request_quiz_from_ai(model_name, transcript)
    quiz_data = json.loads(completion.choices[0].message.content)
    validate_quiz_data(quiz_data)
    return quiz_data


def generate_quiz_data(transcript):
    """Ask the configured AI models in order until one returns a quiz.

    A model that is unavailable, out of quota or answers with an invalid
    quiz is skipped.
    """
    last_error = None
    for model_name in settings.AI_MODELS:
        try:
            return request_valid_quiz(model_name, transcript)
        except (*AI_ERRORS, QuizGenerationError) as error:
            logger.warning('AI model %s failed: %s', model_name, error)
            last_error = error
    raise QuizGenerationError() from last_error


def is_valid_ai_question(question):
    """Check a single question dictionary returned by the AI."""
    return (
        isinstance(question, dict)
        and isinstance(question.get('question_title'), str)
        and is_valid_question(
            question.get('question_options'), question.get('answer')
        )
    )


def validate_quiz_data(quiz_data):
    """Raise QuizGenerationError unless the AI answer is a complete quiz."""
    if not isinstance(quiz_data, dict) or not quiz_data.get('title'):
        raise QuizGenerationError()
    questions = quiz_data.get('questions')
    if not isinstance(questions, list) or len(questions) != QUESTION_COUNT:
        raise QuizGenerationError()
    if not all(is_valid_ai_question(question) for question in questions):
        raise QuizGenerationError()
