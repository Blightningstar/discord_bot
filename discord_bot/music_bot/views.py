from django.shortcuts import render
from .music_commands import (
    PLAY_COMMAND_ALIASES, NOW_PLAYING_COMMAND_ALIASES, 
    MOVE_COMMAND_ALIASES, QUEUE_COMMAND_ALIASES, 
    JOIN_COMMAND_ALIASES, SKIP_COMMAND_ALIASES,
    PAUSE_COMMAND_ALIASES, RESUME_COMMAND_ALIASES,
    SHUFFLE_COMMAND_ALIASES
)

def music_commands_views(request):
    return render(request, "music_bot/music_commands_help.html")

def play_view(request):
    context = {"command_aliases": PLAY_COMMAND_ALIASES, "base_command":"play"}
    return render(request, "music_bot/play.html", context=context)

def now_playing_view(request):
    context = {"command_aliases": NOW_PLAYING_COMMAND_ALIASES, "base_command":"now_playing"}
    return render(request, "music_bot/now_playing.html", context=context)

def move_view(request):
    context = {"command_aliases": MOVE_COMMAND_ALIASES, "base_command":"move"}
    return render(request, "music_bot/move.html", context=context)

def queue_view(request):
    context = {"command_aliases": QUEUE_COMMAND_ALIASES, "base_command":"queue"}
    return render(request, "music_bot/queue.html", context=context)

def join_view(request):
    context = {"command_aliases": JOIN_COMMAND_ALIASES, "base_command":"join"}
    return render(request, "music_bot/join.html", context=context)

def skip_view(request):
    context = {"command_aliases": SKIP_COMMAND_ALIASES, "base_command":"skip"}
    return render(request, "music_bot/skip.html", context=context)

def pause_view(request):
    context = {"command_aliases": PAUSE_COMMAND_ALIASES, "base_command":"pause"}
    return render(request, "music_bot/pause.html", context=context)

def resume_view(request):
    context = {"command_aliases": RESUME_COMMAND_ALIASES, "base_command":"resume"}
    return render(request, "music_bot/resume.html", context=context)

def shuffle_view(request):
    context = {"command_aliases": SHUFFLE_COMMAND_ALIASES, "base_command":"shuffle"}
    return render(request, "music_bot/shuffle.html", context=context)