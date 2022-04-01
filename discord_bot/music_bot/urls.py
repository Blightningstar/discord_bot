from .views import music_commands_views
from django.urls import path

urlpatterns = [
    path("commands_help/", music_commands_views)
]
