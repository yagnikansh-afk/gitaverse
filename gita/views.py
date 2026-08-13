from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView

from .models import Chapter, Shloka
from .serializers import ChapterSerializer, ShlokaSerializer


class ChapterListView(ListAPIView):
    queryset = Chapter.objects.all().order_by("number")
    serializer_class = ChapterSerializer


class ChapterDetailView(RetrieveAPIView):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    lookup_field = "number"
    lookup_url_kwarg = "chapter_number"


class ChapterShlokaListView(ListAPIView):
    serializer_class = ShlokaSerializer

    def get_queryset(self):
        chapter_number = self.kwargs["chapter_number"]

        return (
            Shloka.objects
            .filter(chapter__number=chapter_number)
            .select_related("chapter")
            .prefetch_related("translations")
            .order_by("verse_number")
        )


class ShlokaDetailView(RetrieveAPIView):
    serializer_class = ShlokaSerializer

    def get_object(self):
        chapter_number = self.kwargs["chapter_number"]
        verse_number = self.kwargs["verse_number"]

        return (
            Shloka.objects
            .select_related("chapter")
            .prefetch_related("translations")
            .get(
                chapter__number=chapter_number,
                verse_number=verse_number
            )
        )

class GitaSearchView(ListAPIView):
    serializer_class = ShlokaSerializer

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()

        if not query:
            return Shloka.objects.none()

        return (
            Shloka.objects
            .filter(
                Q(sanskrit__icontains=query)
                | Q(transliteration__icontains=query)
                | Q(translations__text__icontains=query)
                | Q(explanation__icontains=query)
            )
            .select_related("chapter")
            .prefetch_related("translations")
            .distinct()
            .order_by(
                "chapter__number",
                "verse_number"
            )
        )