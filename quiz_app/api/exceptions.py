from rest_framework import status
from rest_framework.exceptions import APIException


class VideoUnavailableError(APIException):
    """The video behind the URL cannot be downloaded."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        'The video could not be loaded. Please check the URL.'
    )
    default_code = 'video_unavailable'


class NoSpeechError(APIException):
    """The video contains no spoken content to build a quiz from."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'No spoken words were detected in the video.'
    default_code = 'no_speech'


class QuizGenerationError(APIException):
    """Transcription or quiz generation failed on the server."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = (
        'The quiz could not be created. Please try again later.'
    )
    default_code = 'quiz_generation_failed'
