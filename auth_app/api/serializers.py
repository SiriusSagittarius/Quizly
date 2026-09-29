from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate the sign-up form and create a new user."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True, 'allow_blank': False},
        }

    def validate_email(self, value):
        """Reject e-mail addresses that are already registered."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'This email address is already in use.'
            )
        return value

    def validate(self, attrs):
        """Make sure both entered passwords are identical."""
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        """Create the user with a hashed password."""
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Check username and password against the database."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Attach the authenticated user or fail with a generic error."""
        user = authenticate(
            username=attrs['username'], password=attrs['password']
        )
        if user is None:
            raise serializers.ValidationError('Invalid credentials.')
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Public user data returned after a successful login."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email']
