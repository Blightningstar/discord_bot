from django.shortcuts import render

def music_commands_views(request):
    return render(request, "music_bot/music_commands_help.html")
