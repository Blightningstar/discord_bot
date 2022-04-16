from django.shortcuts import render
from .music_commands import PLAY_COMMAND_ALIASES

def music_commands_views(request):
    return render(request, "music_bot/music_commands_help.html")

def play_view(request):
    context = {"play_aliases": PLAY_COMMAND_ALIASES}
    return render(request, "music_bot/play.html", context=context)