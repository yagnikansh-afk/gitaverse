from django.contrib import admin
from django.urls import include, path


urlpatterns = [

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "api/gita/",
        include("gita.urls")
    ),

    path(
        "api/auth/",
        include("users.urls")
    ),

    path(
        "api/chat/",
        include("chat.urls")
    ),

]