import json
import logging
import random
import re
import tempfile
import threading
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import whisper
import yt_dlp
from django.conf import settings
from django.db import transaction
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from quiz_app.api.exceptions import (
    NoSpeechError,
    QuizGenerationError,
    VideoUnavailableError,
)
from quiz_app.models import Question, Quiz
from quiz_app.validators import is_valid_question

logger = logging.getLogger(__name__)

QUESTION_COUNT = 10
DOWNLOAD_ATTEMPTS = 2
MAX_TRANSCRIPT_CHARS = 100_000
GEMINI_ERRORS = (genai_errors.APIError, httpx.HTTPError, ValueError, TypeError)
VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')
SHORT_LINK_HOSTS = {'youtu.be', 'www.youtu.be'}
YOUTUBE_HOSTS = {
    'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
}
PATH_ID_PREFIXES = {'shorts', 'embed', 'live'}
WHISPER_LOCK = threading.Lock()

QUIZ_INSTRUCTIONS = """You are a quiz generator. The user sends you the
transcript of a YouTube video. Create a multiple choice quiz from it.

Rules:
- Exactly 10 questions that only refer to the content of the transcript.
- Ask about statements, facts and connections from the video, not about
  the wording of the transcript (no questions like "Which word appears in
  the transcript?").
- Every question has exactly 4 different answer options.
- Exactly one answer option is correct.
- "answer" must match one of the 4 answer options character by character.
- "title" is a short, fitting quiz title (at most 60 characters).
- "description" summarizes the topic in one sentence (at most 150
  characters).
- Write the quiz in the same language as the transcript.
"""

QUESTION_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'question_title': {'type': 'STRING'},
        'question_options': {
            'type': 'ARRAY',
            'items': {'type': 'STRING'},
            'min_items': 4,
            'max_items': 4,
        },
        'answer': {'type': 'STRING'},
    },
    'required': ['question_title', 'question_options', 'answer'],
}

QUIZ_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'title': {'type': 'STRING'},
        'description': {'type': 'STRING'},
        'questions': {
            'type': 'ARRAY',
            'items': QUESTION_SCHEMA,
            'min_items': QUESTION_COUNT,
            'max_items': QUESTION_COUNT,
        },
    },
    'required': ['title', 'description', 'questions'],
}

GEMINI_QUIZ_CONFIG = types.GenerateContentConfig(
    system_instruction=QUIZ_INSTRUCTIONS,
    response_mime_type='application/json',
    response_schema=QUIZ_SCHEMA,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(
        disable=True
    ),
)

GEMINI_HTTP_OPTIONS = types.HttpOptions(
    timeout=60_000,
    retry_options=types.HttpRetryOptions(
        attempts=2, http_status_codes=[500, 502, 503, 504]
    ),
)


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
    """Return yt-dlp options that keep only the audio track as mp3."""
    return {
        'format': 'bestaudio/best',
        'outtmpl': str(Path(target_dir) / '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'noprogress': True,
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'},
        ],
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


@lru_cache(maxsize=1)
def load_whisper_model():
    """Load the configured Whisper model once and keep it in memory."""
    return whisper.load_model(settings.WHISPER_MODEL)


def transcribe_audio(audio_path):
    """Transcribe the audio file locally with Whisper AI.

    The lock allows only one transcription at a time to avoid crashes.
    """
    try:
        with WHISPER_LOCK:
            result = load_whisper_model().transcribe(
                str(audio_path), fp16=False
            )
    except RuntimeError as error:
        logger.error('Transcription failed: %s', error)
        raise QuizGenerationError() from error
    return result['text']


def prepare_transcript(transcript):
    """Reject videos without speech and shorten very long transcripts.

    The transcript is cut after 100,000 characters (about 1.5 hours of
    speech) to keep the prompt within the free Gemini limits.
    """
    words = transcript.split()
    if not words:
        raise NoSpeechError()
    return ' '.join(words)[:MAX_TRANSCRIPT_CHARS]


def create_gemini_client():
    """Create a Gemini client with a timeout and retries on overload.

    An exhausted quota (429) is not retried, the next model is used.
    """
    return genai.Client(
        api_key=settings.GEMINI_API_KEY, http_options=GEMINI_HTTP_OPTIONS
    )


def request_quiz_from_gemini(model_name, transcript):
    """Send the transcript to a Gemini Flash model and demand a JSON quiz."""
    with create_gemini_client() as client:
        return client.models.generate_content(
            model=model_name, contents=transcript, config=GEMINI_QUIZ_CONFIG
        )


def request_valid_quiz(model_name, transcript):
    """Return the quiz of one model or raise if it is missing or invalid."""
    response = request_quiz_from_gemini(model_name, transcript)
    quiz_data = json.loads(response.text)
    validate_quiz_data(quiz_data)
    return quiz_data


def generate_quiz_data(transcript):
    """Ask the configured Gemini models in order until one returns a quiz.

    A model that is overloaded, out of quota or answers with an invalid
    quiz is skipped.
    """
    last_error = None
    for model_name in settings.GEMINI_MODELS:
        try:
            return request_valid_quiz(model_name, transcript)
        except (*GEMINI_ERRORS, QuizGenerationError) as error:
            logger.warning('Gemini model %s failed: %s', model_name, error)
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


def build_question(quiz, question_data):
    """Create an unsaved question with the options in random order."""
    options = question_data['question_options']
    return Question(
        quiz=quiz,
        question_title=question_data['question_title'],
        question_options=random.sample(options, len(options)),
        answer=question_data['answer'],
    )


@transaction.atomic
def save_quiz(quiz_data, video_url, owner):
    """Store the quiz and all questions in one database transaction."""
    quiz = Quiz.objects.create(
        owner=owner,
        title=str(quiz_data['title'])[:255],
        description=str(quiz_data.get('description', '')),
        video_url=video_url,
    )
    Question.objects.bulk_create(
        build_question(quiz, question) for question in quiz_data['questions']
    )
    return quiz


def create_quiz_from_video(video_url, owner):
    """Turn a YouTube video into a saved quiz with ten questions."""
    transcript = transcribe_video(video_url)
    quiz_data = generate_quiz_data(prepare_transcript(transcript))
    return save_quiz(quiz_data, video_url, owner)
