from .views import (
    music_commands_views, pause_view, play_view, 
    now_playing_view, move_view, 
    queue_view, join_view, skip_view, 
    resume_view, shuffle_view
)
from django.urls import path

urlpatterns = [
    path("commands_help/", music_commands_views, name="commands-help"),
    path("commands_help/play", play_view, name="commands-play"),
    path("commands_help/now_playing", now_playing_view, name="commands-now-playing"),
    path("commands_help/move", move_view, name="commands-move"),
    path("commands_help/queue", queue_view, name="commands-queue"),
    path("commands_help/join", join_view, name="commands-join"),
    path("commands_help/skip", skip_view, name="commands-skip"),
    path("commands_help/pause", pause_view, name="commands-pause"),
    path("commands_help/resume", resume_view, name="commands-resume"),
    path("commands_help/shuffle", shuffle_view, name="commands-shuffle"),
]
