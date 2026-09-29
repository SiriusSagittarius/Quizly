from rest_framework import status
from rest_framework.exceptions import APIException


class VideoUnavailableError(APIException):
    """The video behind the URL cannot be downloaded."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        'Das Video konnte nicht geladen werden. Bitte die URL prüfen.'
    )
    default_code = 'video_unavailable'


class NotEnoughSpeechError(APIException):
    """The video contains too little spoken content for a quiz."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        'Das Video enthält zu wenig gesprochenen Inhalt für ein Quiz.'
    )
    default_code = 'not_enough_speech'


class QuizGenerationError(APIException):
    """Transcription or quiz generation failed on the server."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = (
        'Das Quiz konnte nicht erstellt werden. Bitte später erneut versuchen.'
    )
    default_code = 'quiz_generation_failed'
