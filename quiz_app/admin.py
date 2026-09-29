from django.contrib import admin

from quiz_app.models import Question, Quiz


class QuestionInline(admin.StackedInline):
    """Edit all questions directly on the quiz page."""

    model = Question
    extra = 0
    fields = ('question_title', 'question_options', 'answer')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin view for quizzes including their questions."""

    list_display = ('title', 'owner', 'created_at', 'updated_at')
    list_filter = ('created_at', 'owner')
    search_fields = ('title', 'description', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin view to edit single questions."""

    list_display = ('question_title', 'quiz', 'answer')
    list_filter = ('quiz',)
    search_fields = ('question_title', 'quiz__title')
    readonly_fields = ('created_at', 'updated_at')
