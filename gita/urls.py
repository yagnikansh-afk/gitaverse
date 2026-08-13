from django.urls import path

from .views import (
    ChapterListView,
    ChapterDetailView,
    ChapterShlokaListView,
    ShlokaDetailView,
    GitaSearchView,
    ShlokaAskView,
)


urlpatterns = [

    # ========================================================
    # CHAPTERS
    # ========================================================

    # Get all 18 chapters
    # GET /api/gita/chapters/
    path(
        "chapters/",
        ChapterListView.as_view(),
        name="chapter-list"
    ),

    # Get information about one chapter
    # Example:
    # GET /api/gita/chapters/2/
    path(
        "chapters/<int:chapter_number>/",
        ChapterDetailView.as_view(),
        name="chapter-detail"
    ),

    # Get all shlokas from a chapter
    # Example:
    # GET /api/gita/chapters/2/shlokas/
    path(
        "chapters/<int:chapter_number>/shlokas/",
        ChapterShlokaListView.as_view(),
        name="chapter-shloka-list"
    ),

    # ========================================================
    # SHLOKAS
    # ========================================================

    # Get one specific shloka
    # Example:
    # GET /api/gita/shlokas/2/47/
    path(
        "shlokas/<int:chapter_number>/<int:verse_number>/",
        ShlokaDetailView.as_view(),
        name="shloka-detail"
    ),

    # Ask AI about one specific shloka
    # Example:
    # POST /api/gita/shlokas/2/47/ask/
    path(
        "shlokas/<int:chapter_number>/<int:verse_number>/ask/",
        ShlokaAskView.as_view(),
        name="shloka-ask"
    ),

    # ========================================================
    # SEARCH
    # ========================================================

    # Search Bhagavad Gita
    # Example:
    # GET /api/gita/search/?q=action
    path(
        "search/",
        GitaSearchView.as_view(),
        name="gita-search"
    ),

]