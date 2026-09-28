from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

ACCESS_COOKIE_NAME = 'access_token'
REFRESH_COOKIE_NAME = 'refresh_token'


def set_token_cookie(response, cookie_name, token_value, lifetime):
    """Store a token in an HttpOnly cookie that expires with the token."""
    response.set_cookie(
        key=cookie_name,
        value=token_value,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


def set_access_cookie(response, access_token):
    """Store the access token in its HttpOnly cookie."""
    set_token_cookie(
        response, ACCESS_COOKIE_NAME, access_token,
        api_settings.ACCESS_TOKEN_LIFETIME,
    )


def set_auth_cookies(response, user):
    """Create a new token pair for the user and store both as cookies."""
    refresh_token = RefreshToken.for_user(user)
    set_access_cookie(response, str(refresh_token.access_token))
    set_token_cookie(
        response, REFRESH_COOKIE_NAME, str(refresh_token),
        api_settings.REFRESH_TOKEN_LIFETIME,
    )


def create_access_token(raw_refresh_token):
    """Return a new access token for a valid refresh token."""
    if not raw_refresh_token:
        raise TokenError('Refresh-Token fehlt.')
    return str(RefreshToken(raw_refresh_token).access_token)
