from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access only to the user who created the quiz."""

    message = 'Zugriff verweigert - Quiz gehört nicht dem Benutzer.'

    def has_object_permission(self, request, view, obj):
        """Compare the quiz owner with the requesting user."""
        return obj.owner == request.user
