from rest_framework import status
from rest_framework.exceptions import APIException


class VideoUnavailableError(APIException):
    """The video behind the URL cannot be downloaded."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        'Das Video konnte nicht geladen werden. Bitte die URL prüfen.'
    )
    default_code = 'video_unavailable'
