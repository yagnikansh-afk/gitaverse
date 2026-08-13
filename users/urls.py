from django.urls import path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    BookmarkDeleteView,
    BookmarkListCreateView,
    ProfileView,
    RegisterView,
)


urlpatterns = [

    # Authentication

    path(
        "register/",
        RegisterView.as_view(),
        name="register"
    ),

    path(
        "login/",
        TokenObtainPairView.as_view(),
        name="login"
    ),

    path(
        "refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh"
    ),

    path(
        "profile/",
        ProfileView.as_view(),
        name="profile"
    ),

    # Bookmarks

    path(
        "bookmarks/",
        BookmarkListCreateView.as_view(),
        name="bookmark-list-create"
    ),

    path(
        "bookmarks/<int:pk>/",
        BookmarkDeleteView.as_view(),
        name="bookmark-delete"
    ),
]