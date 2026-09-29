from rest_framework import generics

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
