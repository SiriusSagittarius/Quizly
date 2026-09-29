from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from quiz_app.api.permissions import IsQuizOwner
from quiz_app.api.serializers import (
    QuizCreatedSerializer,
    QuizCreateSerializer,
    QuizSerializer,
)
from quiz_app.models import Quiz
from quiz_app.utils import create_quiz_from_video


class QuizListCreateView(generics.ListCreateAPIView):
    """List the user's quizzes or generate a new one from a YouTube URL."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the quizzes of the logged in user."""
        return Quiz.objects.filter(
            owner=self.request.user
        ).prefetch_related('questions')

    def create(self, request, *args, **kwargs):
        """Generate, store and return a quiz for the given YouTube URL."""
        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quiz = create_quiz_from_video(
            serializer.validated_data['url'], request.user
        )
        return Response(
            QuizCreatedSerializer(quiz).data, status=status.HTTP_201_CREATED
        )


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Read, rename or delete a single quiz of the logged in user.

    The queryset is not filtered by owner on purpose: a foreign quiz must
    answer with 403 and only a missing quiz with 404.
    """

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
