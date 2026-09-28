from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from auth_app.api.serializers import (
    LoginSerializer,
    RegistrationSerializer,
    UserSerializer,
)
from auth_app.utils import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    blacklist_access_token,
    blacklist_refresh_token,
    create_access_token,
    delete_auth_cookies,
    set_access_cookie,
    set_auth_cookies,
)

LOGIN_FAILED = {'detail': 'Ungültige Anmeldedaten.'}

LOGOUT_MESSAGE = (
    'Abmeldung erfolgreich! Alle Tokens werden gelöscht. '
    'Das Aktualisierungstoken ist jetzt ungültig.'
)


class RegistrationView(APIView):
    """Create a new user account without requiring a login."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the sign-up data and store the new user."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Benutzer erfolgreich erstellt!'},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Log a user in and set the access and refresh cookie.

    Authentication is switched off here, so an expired access cookie
    in the browser can never block a new login.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Check the credentials and answer with user data and cookies."""
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(LOGIN_FAILED, status=status.HTTP_401_UNAUTHORIZED)
        user = serializer.validated_data['user']
        user_data = UserSerializer(user).data
        response = Response(
            {'detail': 'Erfolgreich angemeldet!', 'user': user_data}
        )
        set_auth_cookies(response, user)
        return response


class LogoutView(APIView):
    """Log the user out and make all of their tokens unusable.

    The user is identified by the refresh cookie, so logging out still
    works when the short-lived access token has already expired.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Blacklist both tokens and delete the auth cookies."""
        try:
            blacklist_refresh_token(request.COOKIES.get(REFRESH_COOKIE_NAME))
        except TokenError:
            return Response(
                {'detail': 'Nicht authentifiziert.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        blacklist_access_token(request.COOKIES.get(ACCESS_COOKIE_NAME))
        response = Response({'detail': LOGOUT_MESSAGE})
        delete_auth_cookies(response)
        return response


class CookieTokenRefreshView(APIView):
    """Issue a new access token based on the refresh cookie.

    Authentication is switched off here, because the access token is
    usually already expired when this endpoint is called.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Set a new access cookie or answer with 401."""
        try:
            access_token = create_access_token(
                request.COOKIES.get(REFRESH_COOKIE_NAME)
            )
        except TokenError:
            return Response(
                {'detail': 'Refresh-Token ungültig oder fehlt.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        response = Response({'detail': 'Token aktualisiert'})
        set_access_cookie(response, access_token)
        return response
