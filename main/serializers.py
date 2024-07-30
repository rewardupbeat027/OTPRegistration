from rest_framework import serializers
from django.contrib.auth.models import User

from .models import RegistrationModel


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = RegistrationModel
        fields = ['phone', 'user']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = User.objects.create(**user_data)
        profile = RegistrationModel.objects.create(user=user, **validated_data)
        return profile