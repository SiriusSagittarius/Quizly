from django.conf import settings
from django.db import models


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
