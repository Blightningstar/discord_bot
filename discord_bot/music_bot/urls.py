from .views import music_commands_views, play_view, now_playing_view
from django.urls import path

urlpatterns = [
    path("commands_help/", music_commands_views, name="commands-help"),
    path("commands_help/play", play_view, name="commands-play"),
    path("commands_help/now_playing", now_playing_view, name="commands-now-playing")
]
