from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializes basic public user data."""

    class Meta:
        model = User
        fields = ['id', 'email']


class RegisterSerializer(serializers.ModelSerializer):
    """Validates and creates a new inactive user."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirmed_password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError('Passwords do not match.')
        return data

    def create(self, validated_data):
        validated_data.pop('confirmed_password')
        return User.objects.create_user(**validated_data)
