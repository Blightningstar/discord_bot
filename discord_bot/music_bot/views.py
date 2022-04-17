from django.shortcuts import render
from .music_commands import PLAY_COMMAND_ALIASES, NOW_PLAYING_COMMAND_ALIASES

def music_commands_views(request):
    return render(request, "music_bot/music_commands_help.html")

def play_view(request):
    context = {"command_aliases": PLAY_COMMAND_ALIASES, "base_command":"play"}
    return render(request, "music_bot/play.html", context=context)

def now_playing_view(request):
    context = {"command_aliases": NOW_PLAYING_COMMAND_ALIASES, "base_command":"now_playing"}
    return render(request, "music_bot/now_playing.html", context=context)