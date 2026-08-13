import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from gita.models import Chapter, Shloka


CHAPTER_NAMES = {
    1: (
        "अर्जुनविषादयोग",
        "Arjuna Vishada Yoga",
        "अर्जुन विषाद योग",
    ),
    2: (
        "सांख्ययोग",
        "Sankhya Yoga",
        "सांख्य योग",
    ),
    3: (
        "कर्मयोग",
        "Karma Yoga",
        "कर्म योग",
    ),
    4: (
        "ज्ञानकर्मसंन्यासयोग",
        "Jnana Karma Sanyasa Yoga",
        "ज्ञान कर्म संन्यास योग",
    ),
    5: (
        "कर्मसंन्यासयोग",
        "Karma Sanyasa Yoga",
        "कर्म संन्यास योग",
    ),
    6: (
        "आत्मसंयमयोग",
        "Dhyana Yoga",
        "ध्यान योग",
    ),
    7: (
        "ज्ञानविज्ञानयोग",
        "Jnana Vijnana Yoga",
        "ज्ञान विज्ञान योग",
    ),
    8: (
        "अक्षरब्रह्मयोग",
        "Akshara Brahma Yoga",
        "अक्षर ब्रह्म योग",
    ),
    9: (
        "राजविद्याराजगुह्ययोग",
        "Raja Vidya Raja Guhya Yoga",
        "राज विद्या राज गुह्य योग",
    ),
    10: (
        "विभूतियोग",
        "Vibhuti Yoga",
        "विभूति योग",
    ),
    11: (
        "विश्वरूपदर्शनयोग",
        "Vishvarupa Darshana Yoga",
        "विश्वरूप दर्शन योग",
    ),
    12: (
        "भक्तियोग",
        "Bhakti Yoga",
        "भक्ति योग",
    ),
    13: (
        "क्षेत्रक्षेत्रज्ञविभागयोग",
        "Kshetra Kshetrajna Vibhaga Yoga",
        "क्षेत्र क्षेत्रज्ञ विभाग योग",
    ),
    14: (
        "गुणत्रयविभागयोग",
        "Gunatraya Vibhaga Yoga",
        "गुणत्रय विभाग योग",
    ),
    15: (
        "पुरुषोत्तमयोग",
        "Purushottama Yoga",
        "पुरुषोत्तम योग",
    ),
    16: (
        "दैवासुरसम्पद्विभागयोग",
        "Daivasura Sampad Vibhaga Yoga",
        "दैवासुर संपद विभाग योग",
    ),
    17: (
        "श्रद्धात्रयविभागयोग",
        "Shraddhatraya Vibhaga Yoga",
        "श्रद्धात्रय विभाग योग",
    ),
    18: (
        "मोक्षसंन्यासयोग",
        "Moksha Sanyasa Yoga",
        "मोक्ष संन्यास योग",
    ),
}


class Command(BaseCommand):
    help = "Import Bhagavad Gita data from data/gita.jsonl"

    @transaction.atomic
    def handle(self, *args, **options):

        file_path = Path("data/gita.jsonl")

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    "Could not find data/gita.jsonl"
                )
            )
            return

        self.stdout.write(
            "Reading Bhagavad Gita dataset..."
        )

        imported = 0
        updated = 0
        skipped = 0

        with file_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            for line_number, line in enumerate(
                file,
                start=1
            ):

                if not line.strip():
                    continue

                # -----------------------------
                # Read JSON
                # -----------------------------

                try:
                    data = json.loads(line)

                except json.JSONDecodeError:

                    self.stdout.write(
                        self.style.WARNING(
                            f"Invalid JSON on line "
                            f"{line_number}. Skipping."
                        )
                    )

                    skipped += 1
                    continue

                # -----------------------------
                # Chapter / Verse
                # -----------------------------

                chapter_number = data.get("chapter")
                verse_number = data.get("verse")

                if (
                    chapter_number is None
                    or verse_number is None
                ):
                    skipped += 1
                    continue

                try:
                    chapter_number = int(
                        chapter_number
                    )

                    verse_number = int(
                        verse_number
                    )

                except (TypeError, ValueError):

                    skipped += 1
                    continue

                # -----------------------------
                # Chapter names
                # -----------------------------

                chapter_names = CHAPTER_NAMES.get(
                    chapter_number
                )

                if chapter_names is None:
                    skipped += 1
                    continue

                (
                    sanskrit_name,
                    english_name,
                    hindi_name,
                ) = chapter_names

                chapter, _ = (
                    Chapter.objects.update_or_create(
                        number=chapter_number,
                        defaults={
                            "name_sanskrit":
                                sanskrit_name,

                            "name_english":
                                english_name,

                            "name_hindi":
                                hindi_name,
                        },
                    )
                )

                # -----------------------------
                # Sanskrit
                # -----------------------------

                sanskrit = data.get(
                    "slok",
                    ""
                )

                # -----------------------------
                # Transliteration
                # -----------------------------

                transliteration = data.get(
                    "transliteration",
                    ""
                )

                # -----------------------------
                # Swami Sivananda data
                # -----------------------------

                sivananda = (
                    data.get("siva") or {}
                )

                # English translation
                english_translation = (
                    sivananda.get("et", "")
                )

                # English commentary /
                # explanation
                explanation = (
                    sivananda.get("ec", "")
                )

                # -----------------------------
                # Hindi translation
                # -----------------------------

                hindi_translation = ""

                possible_hindi_sources = [
                    "tej",
                    "rams",
                    "adi",
                    "chinmay",
                ]

                for key in possible_hindi_sources:

                    section = data.get(key)

                    if not isinstance(
                        section,
                        dict
                    ):
                        continue

                    candidate = (
                        section.get("ht")
                        or section.get("hindi")
                        or ""
                    )

                    if candidate:
                        hindi_translation = (
                            candidate
                        )
                        break

                # -----------------------------
                # Create / Update Shloka
                # -----------------------------

                shloka, created = (
                    Shloka.objects.update_or_create(
                        chapter=chapter,

                        verse_number=verse_number,

                        defaults={
                            "sanskrit":
                                sanskrit,

                            "transliteration":
                                transliteration,

                            "english_translation":
                                english_translation,

                            "hindi_translation":
                                hindi_translation,

                            "explanation":
                                explanation,
                        },
                    )
                )

                if created:
                    imported += 1
                else:
                    updated += 1

        # -------------------------------------
        # Calculate chapter verse counts
        # -------------------------------------

        for chapter in Chapter.objects.all():

            chapter.total_verses = (
                chapter.shlokas.count()
            )

            chapter.save(
                update_fields=[
                    "total_verses"
                ]
            )

        # -------------------------------------
        # Results
        # -------------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Bhagavad Gita import completed!"
            )
        )

        self.stdout.write(
            f"New shlokas: {imported}"
        )

        self.stdout.write(
            f"Updated shlokas: {updated}"
        )

        self.stdout.write(
            f"Skipped rows: {skipped}"
        )

        self.stdout.write(
            f"Total chapters: "
            f"{Chapter.objects.count()}"
        )

        self.stdout.write(
            f"Total shlokas: "
            f"{Shloka.objects.count()}"
        )