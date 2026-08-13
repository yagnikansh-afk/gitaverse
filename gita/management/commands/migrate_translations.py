from django.core.management.base import BaseCommand
from django.db import transaction

from gita.models import Shloka, Translation


class Command(BaseCommand):
    help = "Move existing shloka translations into Translation table"

    @transaction.atomic
    def handle(self, *args, **options):

        english_count = 0
        hindi_count = 0

        for shloka in Shloka.objects.all():

            # English
            if shloka.english_translation.strip():

                _, created = Translation.objects.update_or_create(
                    shloka=shloka,
                    language_code="en",
                    translator="Swami Sivananda",
                    defaults={
                        "language": "English",
                        "text": shloka.english_translation,
                        "source": "Imported Bhagavad Gita dataset",
                    },
                )

                if created:
                    english_count += 1

            # Hindi
            if shloka.hindi_translation.strip():

                _, created = Translation.objects.update_or_create(
                    shloka=shloka,
                    language_code="hi",
                    translator="Dataset translation",
                    defaults={
                        "language": "Hindi",
                        "text": shloka.hindi_translation,
                        "source": "Imported Bhagavad Gita dataset",
                    },
                )

                if created:
                    hindi_count += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Translation migration completed!"
            )
        )

        self.stdout.write(
            f"English translations added: {english_count}"
        )

        self.stdout.write(
            f"Hindi translations added: {hindi_count}"
        )

        self.stdout.write(
            f"Total translations: {Translation.objects.count()}"
        )