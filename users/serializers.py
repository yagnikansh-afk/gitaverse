from django.contrib.auth.models import User
from rest_framework import serializers

from gita.models import Shloka
from gita.serializers import ShlokaSerializer
from .models import Bookmark


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
        ]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
        ]


class BookmarkSerializer(serializers.ModelSerializer):

    shloka_id = serializers.PrimaryKeyRelatedField(
        queryset=Shloka.objects.all(),
        source="shloka",
        write_only=True
    )

    shloka = ShlokaSerializer(
        read_only=True
    )

    class Meta:
        model = Bookmark
        fields = [
            "id",
            "shloka_id",
            "shloka",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]

    def validate_shloka_id(self, value):
        user = self.context["request"].user

        if Bookmark.objects.filter(
            user=user,
            shloka=value
        ).exists():
            raise serializers.ValidationError(
                "This shloka is already bookmarked."
            )

        return value

    def create(self, validated_data):
        user = self.context["request"].user

        return Bookmark.objects.create(
            user=user,
            **validated_data
        )