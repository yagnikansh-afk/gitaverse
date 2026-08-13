from django.contrib import admin
from .models import Chapter, Shloka


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "name_english",
        "name_sanskrit",
        "total_verses",
    )

    ordering = ("number",)

    search_fields = (
        "name_english",
        "name_sanskrit",
        "name_hindi",
    )


@admin.register(Shloka)
class ShlokaAdmin(admin.ModelAdmin):
    list_display = (
        "chapter",
        "verse_number",
    )

    list_filter = ("chapter",)

    search_fields = (
        "sanskrit",
        "english_translation",
        "hindi_translation",
        "gujarati_translation",
    )