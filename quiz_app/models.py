from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from quiz_app.validators import is_valid_question


class Quiz(models.Model):
    """A quiz generated from a YouTube video for one user."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quizzes',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'quizzes'

    def __str__(self):
        """Show the quiz title in the admin panel."""
        return self.title


class Question(models.Model):
    """A multiple choice question with four options and one answer."""

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    question_title = models.TextField()
    question_options = models.JSONField(default=list)
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        """Show the question text in the admin panel."""
        return self.question_title

    def clean(self):
        """Require four distinct options that contain the answer."""
        if not is_valid_question(self.question_options, self.answer):
            raise ValidationError(
                'Exactly 4 different answer options are required '
                'and the answer must be one of them.'
            )
