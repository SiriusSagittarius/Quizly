from rest_framework_simplejwt.authentication import JWTAuthentication

from auth_app.utils import ACCESS_COOKIE_NAME


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate requests with the access token stored in a cookie."""

    def authenticate(self, request):
        """Return ``(user, token)`` for a valid access cookie, else None."""
        raw_token = request.COOKIES.get(ACCESS_COOKIE_NAME)
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
