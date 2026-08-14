from datetime import date

from django.conf import settings
from django.db.models import Q

from google import genai
from google.genai import types

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Chapter, Shloka
from .serializers import ChapterSerializer, ShlokaSerializer


# ============================================================
# CHAPTER LIST
# ============================================================

class ChapterListView(ListAPIView):

    queryset = (
        Chapter.objects
        .all()
        .order_by("number")
    )

    serializer_class = ChapterSerializer


# ============================================================
# CHAPTER DETAIL
# ============================================================

class ChapterDetailView(RetrieveAPIView):

    queryset = Chapter.objects.all()

    serializer_class = ChapterSerializer

    lookup_field = "number"
    lookup_url_kwarg = "chapter_number"


# ============================================================
# CHAPTER SHLOKA LIST
# ============================================================

class ChapterShlokaListView(ListAPIView):

    serializer_class = ShlokaSerializer

    def get_queryset(self):

        chapter_number = self.kwargs[
            "chapter_number"
        ]

        return (
            Shloka.objects
            .filter(
                chapter__number=chapter_number
            )
            .select_related("chapter")
            .prefetch_related("translations")
            .order_by("verse_number")
        )


# ============================================================
# SHLOKA DETAIL
# ============================================================

class ShlokaDetailView(RetrieveAPIView):

    serializer_class = ShlokaSerializer

    def get_object(self):

        chapter_number = self.kwargs[
            "chapter_number"
        ]

        verse_number = self.kwargs[
            "verse_number"
        ]

        return (
            Shloka.objects
            .select_related("chapter")
            .prefetch_related("translations")
            .get(
                chapter__number=chapter_number,
                verse_number=verse_number
            )
        )


# ============================================================
# GITA SEARCH
# ============================================================

class GitaSearchView(ListAPIView):

    serializer_class = ShlokaSerializer

    def get_queryset(self):

        query = (
            self.request
            .query_params
            .get("q", "")
            .strip()
        )

        if not query:

            return Shloka.objects.none()

        return (
            Shloka.objects
            .filter(
                Q(
                    sanskrit__icontains=query
                )
                |
                Q(
                    transliteration__icontains=query
                )
                |
                Q(
                    translations__text__icontains=query
                )
                |
                Q(
                    explanation__icontains=query
                )
            )
            .select_related("chapter")
            .prefetch_related("translations")
            .distinct()
            .order_by(
                "chapter__number",
                "verse_number"
            )
        )


# ============================================================
# ASK ABOUT A SPECIFIC SHLOKA
# ============================================================

class ShlokaAskView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(
        self,
        request,
        chapter_number,
        verse_number
    ):

        # ====================================================
        # GET USER QUESTION
        # ====================================================

        question = (
            request.data
            .get("question", "")
            .strip()
        )

        if not question:

            return Response(
                {
                    "error":
                        "Question is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ====================================================
        # FIND SHLOKA
        # ====================================================

        try:

            shloka = (
                Shloka.objects
                .select_related("chapter")
                .prefetch_related("translations")
                .get(
                    chapter__number=chapter_number,
                    verse_number=verse_number
                )
            )

        except Shloka.DoesNotExist:

            return Response(
                {
                    "error":
                        "Shloka not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ====================================================
        # FIND ENGLISH TRANSLATION
        # ====================================================

        english_translation = ""

        for translation in (
            shloka.translations.all()
        ):

            if (
                translation.language_code
                == "en"
            ):

                english_translation = (
                    translation.text
                )

                break

        # Fallback to old Shloka field
        if not english_translation:

            english_translation = (
                shloka.english_translation
                or ""
            )

        # ====================================================
        # CHECK GEMINI API KEY
        # ====================================================

        if not settings.GEMINI_API_KEY:

            return Response(
                {
                    "error":
                        "GEMINI_API_KEY is not configured."
                },
                status=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                )
            )

        # ====================================================
        # CREATE GEMINI CLIENT
        # ====================================================

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        # ====================================================
        # BUILD PROMPT
        # ====================================================

        prompt = f"""
You are GitaVerse AI.

You are explaining one specific verse from the
Shrimad Bhagavad Gita.

The user has asked a question about this verse.

Your job is to explain the verse accurately,
simply, compassionately, and practically.

IMPORTANT RULES:

1. Do not pretend to be Shri Krishna, God, or a guru.

2. You are an AI guide explaining the teaching of
   the Bhagavad Gita.

3. Use the supplied shloka and its supplied explanation
   as your primary source.

4. Do not invent other Bhagavad Gita verses.

5. Do not invent Sanskrit quotations.

6. Do not change the meaning of the supplied translation.

7. Answer the user's actual question.

8. Use simple modern language.

9. If the user asks how this teaching applies to their
   life, connect it directly to their situation.

10. Give a realistic everyday real-world example.

11. Do not use random examples involving athletes,
    superheroes, movies, or fictional characters.

12. Do not invent a specific person's story and claim
    that it really happened.

13. A realistic/common situation is acceptable, but do
    not present it as a verified real event.

14. Give practical actions the user can actually take.

15. Do not make promises about the user's future.

16. Do not present the Gita as a replacement for
    professional medical, mental-health, legal,
    financial, or emergency assistance when such help
    is appropriate.


============================================================
SHLOKA
============================================================

Bhagavad Gita {chapter_number}.{verse_number}


Sanskrit:

{shloka.sanskrit}


Transliteration:

{shloka.transliteration}


English Translation:

{english_translation}


Explanation / Commentary:

{shloka.explanation}


============================================================
USER QUESTION
============================================================

{question}


============================================================
RESPONSE FORMAT
============================================================

### Meaning

Explain what this specific shloka means in simple
language.

Do not merely copy the translation.


### How It Applies

Explain how the teaching of this particular shloka
relates to the user's question.

Make the explanation practical and personal.


### Real-World Example

Give a realistic everyday situation that directly
relates to the user's question.

For example:

- exams
- studying
- career decisions
- workplace problems
- relationships
- family disagreements
- anger
- failure
- stress
- financial decisions
- dealing with uncertainty

Do not use an unrelated fictional story.

Do not invent a named person and claim their story
is real.


### What You Can Do

Give 3 to 5 practical actions based on the teaching.

Make them realistic and actionable.


### Reflection

End with one short reflection or question that helps
the user think about the teaching.


IMPORTANT:

Complete every section.

Do not stop after the Meaning section.

Do not stop after How It Applies.

Do not stop in the middle of a sentence.

Always finish with the Reflection section.
""".strip()

        # ====================================================
        # GENERATE AI RESPONSE
        # ====================================================

        try:

            response = (
                client.models.generate_content(
                    model="gemini-3.5-flash",

                    contents=prompt,

                    config=(
                        types.GenerateContentConfig(
                            max_output_tokens=3000
                        )
                    )
                )
            )

            answer = (
                response.text or ""
            ).strip()

        except Exception as error:

            return Response(
                {
                    "error":
                        "AI guidance could not be generated.",

                    "details":
                        str(error)
                },
                status=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                )
            )

        # ====================================================
        # CHECK EMPTY RESPONSE
        # ====================================================

        if not answer:

            return Response(
                {
                    "error":
                        "AI returned an empty response."
                },
                status=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                )
            )

        # ====================================================
        # RETURN RESPONSE
        # ====================================================

        return Response(
            {
                "shloka": {
                    "id":
                        shloka.id,

                    "chapter_number":
                        shloka.chapter.number,

                    "verse_number":
                        shloka.verse_number,

                    "sanskrit":
                        shloka.sanskrit,

                    "transliteration":
                        shloka.transliteration,

                    "english_translation":
                        english_translation,
                },

                "question":
                    question,

                "answer":
                    answer,
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# DAILY SHLOKA
# ============================================================

class DailyShlokaView(RetrieveAPIView):

    serializer_class = ShlokaSerializer

    def get_object(self):

        total_shlokas = (
            Shloka.objects.count()
        )

        if total_shlokas == 0:

            raise Shloka.DoesNotExist

        # Day of the year:
        # January 1 = 1
        # January 2 = 2
        # etc.
        day_number = (
            date.today()
            .timetuple()
            .tm_yday
        )

        # Convert the day number into a
        # zero-based database index.
        index = (
            (day_number - 1)
            % total_shlokas
        )

        return (
            Shloka.objects
            .select_related("chapter")
            .prefetch_related("translations")
            .order_by(
                "chapter__number",
                "verse_number"
            )[index]
        )

    def retrieve(
        self,
        request,
        *args,
        **kwargs
    ):

        shloka = self.get_object()

        data = (
            self.get_serializer(
                shloka
            ).data
        )

        return Response(
            {
                "date":
                    date.today().isoformat(),

                "title":
                    "Today's Shloka",

                **data,
            },
            status=status.HTTP_200_OK
        )