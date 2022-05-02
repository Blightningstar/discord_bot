from .views import (
    music_commands_views, play_view, 
    now_playing_view, move_view, 
    queue_view, join_view
)
from django.urls import path

urlpatterns = [
    path("commands_help/", music_commands_views, name="commands-help"),
    path("commands_help/play", play_view, name="commands-play"),
    path("commands_help/now_playing", now_playing_view, name="commands-now-playing"),
    path("commands_help/move", move_view, name="commands-move"),
    path("commands_help/queue", queue_view, name="commands-queue"),
    path("commands_help/join", join_view, name="commands-join"),
]
