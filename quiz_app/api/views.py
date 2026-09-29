from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from quiz_app.api.permissions import IsQuizOwner
from quiz_app.api.serializers import QuizSerializer
from quiz_app.models import Quiz


class QuizListView(generics.ListAPIView):
    """List all quizzes of the logged in user."""

    serializer_class = QuizSerializer

    def get_queryset(self):
        """Return only the quizzes of the logged in user."""
        return Quiz.objects.filter(
            owner=self.request.user
        ).prefetch_related('questions')


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Read, rename or delete a single quiz of the logged in user.

    The queryset is not filtered by owner on purpose: a foreign quiz must
    answer with 403 and only a missing quiz with 404.
    """

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
