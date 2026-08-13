from django.core.management.base import BaseCommand

from gita.models import Shloka, Translation


def repair_text(text):
    """
    Attempt to repair UTF-8 text that was incorrectly decoded
    as Latin-1 / Windows-1252.
    """

    if not text:
        return text

    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


class Command(BaseCommand):
    help = "Test Unicode encoding repair on Bhagavad Gita 2.47"

    def handle(self, *args, **options):

        try:
            shloka = Shloka.objects.get(
                chapter__number=2,
                verse_number=47
            )

        except Shloka.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "BG 2.47 was not found."
                )
            )
            return

        self.stdout.write("")
        self.stdout.write("BEFORE:")
        self.stdout.write("-" * 50)

        self.stdout.write(
            f"Sanskrit:\n{shloka.sanskrit}"
        )

        self.stdout.write(
            f"\nTransliteration:\n{shloka.transliteration}"
        )

        # Repair Sanskrit
        repaired_sanskrit = repair_text(
            shloka.sanskrit
        )

        # Repair transliteration
        repaired_transliteration = repair_text(
            shloka.transliteration
        )

        self.stdout.write("")
        self.stdout.write("AFTER:")
        self.stdout.write("-" * 50)

        self.stdout.write(
            f"Sanskrit:\n{repaired_sanskrit}"
        )

        self.stdout.write(
            f"\nTransliteration:\n"
            f"{repaired_transliteration}"
        )

        # Repair translations for this verse
        translations = Translation.objects.filter(
            shloka=shloka
        )

        for translation in translations:

            repaired_translation = repair_text(
                translation.text
            )

            self.stdout.write("")
            self.stdout.write(
                f"{translation.language}:"
            )

            self.stdout.write(
                repaired_translation
            )

        # Repair explanation
        repaired_explanation = repair_text(
            shloka.explanation
        )

        self.stdout.write("")
        self.stdout.write("Explanation:")
        self.stdout.write(
            repaired_explanation
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "TEST ONLY - nothing was changed "
                "in the database."
            )
        )