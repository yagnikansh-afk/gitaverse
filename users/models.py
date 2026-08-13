from django.contrib.auth.models import User
from django.db import models

from gita.models import Shloka


class Bookmark(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )

    shloka = models.ForeignKey(
        Shloka,
        on_delete=models.CASCADE,
        related_name="bookmarked_by"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "shloka"],
                name="unique_user_shloka_bookmark"
            )
        ]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"BG {self.shloka.chapter.number}."
            f"{self.shloka.verse_number}"
        )