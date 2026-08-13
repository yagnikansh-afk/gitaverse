import time

from django.conf import settings
from django.core.management.base import BaseCommand

from google import genai
from google.genai import types

from gita.models import Shloka


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "gemini-embedding-001"

EMBEDDING_DIMENSIONS = 768


# ============================================================
# GET ENGLISH TRANSLATION
# ============================================================

def get_english_translation(shloka):
    """
    Get the English translation for a shloka
    from the Translation table.
    """

    for translation in shloka.translations.all():

        if translation.language_code == "en":
            return translation.text

    return ""


# ============================================================
# BUILD DOCUMENT
# ============================================================

def build_document(shloka):
    """
    Build the text that Gemini will convert
    into a semantic embedding.

    We include:

    - Chapter and verse number
    - Sanskrit shloka
    - Transliteration
    - English translation
    - Commentary / explanation

    This gives semantic search enough information
    to understand the meaning of the verse.
    """

    english_translation = get_english_translation(
        shloka
    )

    document = f"""
Bhagavad Gita {shloka.chapter.number}.{shloka.verse_number}

Sanskrit:
{shloka.sanskrit}

Transliteration:
{shloka.transliteration}

English Translation:
{english_translation}

Commentary:
{shloka.explanation}
""".strip()

    return document


# ============================================================
# DJANGO COMMAND
# ============================================================

class Command(BaseCommand):

    help = (
        "Generate semantic embeddings "
        "for all Bhagavad Gita shlokas"
    )

    def handle(self, *args, **options):

        # ====================================================
        # CHECK GEMINI API KEY
        # ====================================================

        if not settings.GEMINI_API_KEY:

            self.stdout.write(
                self.style.ERROR(
                    "GEMINI_API_KEY is not configured."
                )
            )

            return

        # ====================================================
        # CREATE GEMINI CLIENT
        # ====================================================

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        # ====================================================
        # GET ALL SHLOKAS
        # ====================================================

        shlokas = (
            Shloka.objects
            .select_related("chapter")
            .prefetch_related("translations")
            .all()
        )

        total = shlokas.count()

        if total == 0:

            self.stdout.write(
                self.style.ERROR(
                    "No shlokas were found in the database."
                )
            )

            return

        # ====================================================
        # START INFORMATION
        # ====================================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Starting Bhagavad Gita embedding generation..."
            )
        )

        self.stdout.write("")

        self.stdout.write(
            f"Total shlokas: {total}"
        )

        self.stdout.write(
            f"Model: {MODEL_NAME}"
        )

        self.stdout.write(
            f"Embedding dimensions: "
            f"{EMBEDDING_DIMENSIONS}"
        )

        self.stdout.write("")

        generated = 0
        skipped = 0
        failed = 0

        # ====================================================
        # PROCESS EVERY SHLOKA
        # ====================================================

        for index, shloka in enumerate(
            shlokas,
            start=1
        ):

            verse_name = (
                f"BG "
                f"{shloka.chapter.number}."
                f"{shloka.verse_number}"
            )

            # =================================================
            # SKIP EXISTING EMBEDDINGS
            # =================================================

            if shloka.embedding:

                skipped += 1

                dimensions = len(
                    shloka.embedding
                )

                self.stdout.write(
                    self.style.WARNING(
                        f"[{index}/{total}] "
                        f"{verse_name} "
                        f"- already embedded "
                        f"({dimensions} dimensions)"
                    )
                )

                continue

            # =================================================
            # BUILD DOCUMENT
            # =================================================

            document = build_document(
                shloka
            )

            try:

                # =============================================
                # REQUEST EMBEDDING FROM GEMINI
                # =============================================

                response = (
                    client.models.embed_content(
                        model=MODEL_NAME,

                        contents=document,

                        config=types.EmbedContentConfig(

                            task_type=(
                                "RETRIEVAL_DOCUMENT"
                            ),

                            title=verse_name,

                            output_dimensionality=(
                                EMBEDDING_DIMENSIONS
                            ),
                        ),
                    )
                )

                # =============================================
                # VALIDATE RESPONSE
                # =============================================

                if not response.embeddings:

                    raise ValueError(
                        "Gemini returned no embeddings."
                    )

                embedding = (
                    response.embeddings[0].values
                )

                if not embedding:

                    raise ValueError(
                        "Gemini returned an empty embedding."
                    )

                # =============================================
                # CHECK VECTOR SIZE
                # =============================================

                if len(embedding) != EMBEDDING_DIMENSIONS:

                    raise ValueError(
                        f"Expected "
                        f"{EMBEDDING_DIMENSIONS} dimensions "
                        f"but Gemini returned "
                        f"{len(embedding)}."
                    )

                # =============================================
                # SAVE EMBEDDING
                # =============================================

                shloka.embedding = list(
                    embedding
                )

                shloka.save(
                    update_fields=[
                        "embedding"
                    ]
                )

                generated += 1

                # =============================================
                # SUCCESS
                # =============================================

                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{index}/{total}] "
                        f"{verse_name} "
                        f"- embedded successfully "
                        f"({len(embedding)} dimensions)"
                    )
                )

                # Small pause between requests.
                time.sleep(0.1)

            except Exception as error:

                failed += 1

                # =============================================
                # ERROR
                # =============================================

                self.stdout.write(
                    self.style.ERROR(
                        f"[{index}/{total}] "
                        f"{verse_name} "
                        f"- FAILED"
                    )
                )

                self.stdout.write(
                    self.style.ERROR(
                        str(error)
                    )
                )

                self.stdout.write("")

        # ====================================================
        # FINAL SUMMARY
        # ====================================================

        self.stdout.write("")
        self.stdout.write(
            "=" * 60
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Embedding generation finished."
            )
        )

        self.stdout.write(
            "=" * 60
        )

        self.stdout.write(
            f"Total shlokas: {total}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated now: {generated}"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"Already existed: {skipped}"
            )
        )

        if failed > 0:

            self.stdout.write(
                self.style.ERROR(
                    f"Failed: {failed}"
                )
            )

        else:

            self.stdout.write(
                self.style.SUCCESS(
                    "Failed: 0"
                )
            )

        # ====================================================
        # DATABASE TOTAL
        # ====================================================

        embedded_total = (
            Shloka.objects
            .exclude(
                embedding__isnull=True
            )
            .count()
        )

        remaining = (
            total - embedded_total
        )

        self.stdout.write("")

        self.stdout.write(
            f"Embedded in database: "
            f"{embedded_total}/{total}"
        )

        self.stdout.write(
            f"Remaining: {remaining}"
        )

        self.stdout.write("")

        if embedded_total == total:

            self.stdout.write(
                self.style.SUCCESS(
                    "All Bhagavad Gita shlokas "
                    "have embeddings!"
                )
            )

        else:

            self.stdout.write(
                self.style.WARNING(
                    "Some shlokas still need embeddings."
                )
            )

            self.stdout.write(
                self.style.WARNING(
                    "You can safely run this command "
                    "again. Existing embeddings will "
                    "be skipped."
                )
            )

        self.stdout.write("")