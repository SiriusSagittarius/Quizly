from django.apps import AppConfig


class QuizAppConfig(AppConfig):
    """Registers the quiz app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quiz_app'
