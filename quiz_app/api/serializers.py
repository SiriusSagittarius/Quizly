from rest_framework import serializers

from quiz_app.models import Question, Quiz
from quiz_app.utils import normalize_youtube_url


class QuestionSerializer(serializers.ModelSerializer):
    """Question data used in quiz lists and detail views."""

    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer']
        read_only_fields = fields


class QuizSerializer(serializers.ModelSerializer):
    """Quiz with its questions; only title and description are editable."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'created_at', 'updated_at',
            'video_url', 'questions',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'video_url']


class QuizCreateSerializer(serializers.Serializer):
    """Validate the YouTube URL that a new quiz is generated from."""

    url = serializers.CharField()

    def validate_url(self, value):
        """Accept only YouTube links and return their canonical form."""
        watch_url = normalize_youtube_url(value)
        if watch_url is None:
            raise serializers.ValidationError(
                'Bitte eine gültige YouTube-URL angeben.'
            )
        return watch_url
