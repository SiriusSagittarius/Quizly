from rest_framework_simplejwt.tokens import AccessToken, BlacklistMixin


class BlacklistableAccessToken(BlacklistMixin, AccessToken):
    """Access token that is checked against the blacklist on every request."""
