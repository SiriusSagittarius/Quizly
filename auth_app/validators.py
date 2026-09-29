import re

from django.core.exceptions import ValidationError

COMPLEXITY_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)')


class PasswordComplexityValidator:
    """Require at least one lowercase letter, uppercase letter and digit."""

    def validate(self, password, user=None):
        """Raise a ValidationError if a character class is missing."""
        if not COMPLEXITY_PATTERN.match(password):
            raise ValidationError(
                self.get_help_text(), code='password_too_simple'
            )

    def get_help_text(self):
        """Describe the rule for forms and error messages."""
        return (
            'The password needs at least one uppercase letter, '
            'one lowercase letter and one digit.'
        )
