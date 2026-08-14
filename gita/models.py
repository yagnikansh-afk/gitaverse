from django.db import models


class Chapter(models.Model):
    number = models.PositiveIntegerField(
        unique=True
    )

    name_sanskrit = models.CharField(
        max_length=200
    )

    name_english = models.CharField(
        max_length=200
    )

    name_hindi = models.CharField(
        max_length=200,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    total_verses = models.PositiveIntegerField(
        default=0
    )

    def __str__(self):
        return (
            f"Chapter {self.number}: "
            f"{self.name_english}"
        )


class Shloka(models.Model):
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="shlokas"
    )

    verse_number = models.PositiveIntegerField()

    sanskrit = models.TextField()

    transliteration = models.TextField(
        blank=True
    )

    # Temporary translation fields.
    # These can eventually be fully migrated
    # into the Translation model.
    english_translation = models.TextField(
        blank=True
    )

    hindi_translation = models.TextField(
        blank=True
    )

    gujarati_translation = models.TextField(
        blank=True
    )

    explanation = models.TextField(
        blank=True
    )

    # ==================================================
    # SEMANTIC SEARCH EMBEDDING
    # ==================================================
    #
    # Stores the numerical embedding generated for
    # this shloka.
    #
    # Example:
    # [
    #     0.0123,
    #     -0.0456,
    #     0.0789,
    #     ...
    # ]
    #
    # We use JSONField because the project currently
    # uses SQLite.
    #
    # Later, when moving to PostgreSQL, this can be
    # replaced with pgvector for faster vector search.
    # ==================================================

    embedding = models.JSONField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = [
            "chapter__number",
            "verse_number"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "chapter",
                    "verse_number"
                ],
                name="unique_chapter_verse"
            )
        ]

    def __str__(self):
        return (
            f"BG {self.chapter.number}."
            f"{self.verse_number}"
        )


class Translation(models.Model):
    shloka = models.ForeignKey(
        Shloka,
        on_delete=models.CASCADE,
        related_name="translations"
    )

    language = models.CharField(
        max_length=50
    )

    language_code = models.CharField(
        max_length=10
    )

    text = models.TextField()

    translator = models.CharField(
        max_length=200,
        blank=True
    )

    source = models.CharField(
        max_length=500,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "shloka",
                    "language_code",
                    "translator"
                ],
                name="unique_shloka_translation"
            )
        ]

    def __str__(self):
        return (
            f"BG {self.shloka.chapter.number}."
            f"{self.shloka.verse_number} - "
            f"{self.language}"
        )

class DailyInsight(models.Model):
    shloka = models.ForeignKey(
        Shloka,
        on_delete=models.CASCADE,
        related_name="daily_insights"
    )

    date = models.DateField(
        unique=True
    )

    content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"Daily Insight - "
            f"{self.date} - "
            f"BG {self.shloka.chapter.number}."
            f"{self.shloka.verse_number}"
        )