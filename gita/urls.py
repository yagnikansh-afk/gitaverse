from django.urls import path

from .views import (
    ChapterListView,
    ChapterDetailView,
    ChapterShlokaListView,
    ShlokaDetailView,
    GitaSearchView,
)


urlpatterns = [

    # Get all 18 chapters
    # /api/gita/chapters/
    path(
        "chapters/",
        ChapterListView.as_view(),
        name="chapter-list"
    ),

    # Get information about one chapter
    # Example: /api/gita/chapters/2/
    path(
        "chapters/<int:chapter_number>/",
        ChapterDetailView.as_view(),
        name="chapter-detail"
    ),

    # Get all shlokas from a chapter
    # Example: /api/gita/chapters/2/shlokas/
    path(
        "chapters/<int:chapter_number>/shlokas/",
        ChapterShlokaListView.as_view(),
        name="chapter-shloka-list"
    ),

    # Get one specific shloka
    # Example: /api/gita/shlokas/2/47/
    path(
        "shlokas/<int:chapter_number>/<int:verse_number>/",
        ShlokaDetailView.as_view(),
        name="shloka-detail"
    ),

    # Search Bhagavad Gita
    # Example: /api/gita/search/?q=action
    path(
        "search/",
        GitaSearchView.as_view(),
        name="gita-search"
    ),

]