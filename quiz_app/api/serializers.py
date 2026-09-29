from rest_framework import serializers

from quiz_app.models import Question, Quiz


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
