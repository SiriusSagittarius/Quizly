from django import forms

from quiz_app.models import Question
from quiz_app.validators import is_valid_question


class QuestionAdminForm(forms.ModelForm):
    """Admin form that checks the answer options of a question."""

    class Meta:
        model = Question
        fields = ['quiz', 'question_title', 'question_options', 'answer']

    def clean(self):
        """Require four distinct options that contain the answer."""
        cleaned_data = super().clean()
        options = cleaned_data.get('question_options')
        if not is_valid_question(options, cleaned_data.get('answer')):
            raise forms.ValidationError(
                'Exactly 4 different answer options are required '
                'and the answer must be one of them.'
            )
        return cleaned_data
