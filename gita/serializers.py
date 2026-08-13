from rest_framework import serializers
from .models import Chapter, Shloka, Translation


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = [
            "id",
            "number",
            "name_sanskrit",
            "name_english",
            "name_hindi",
            "description",
            "total_verses",
        ]


class TranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Translation
        fields = [
            "language",
            "language_code",
            "text",
            "translator",
            "source",
        ]


class ShlokaSerializer(serializers.ModelSerializer):
    chapter_number = serializers.IntegerField(
        source="chapter.number",
        read_only=True
    )

    translations = TranslationSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Shloka
        fields = [
            "id",
            "chapter_number",
            "verse_number",
            "sanskrit",
            "transliteration",
            "translations",
            "explanation",
        ]