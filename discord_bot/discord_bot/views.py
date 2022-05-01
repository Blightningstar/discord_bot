import os
from django.shortcuts import redirect
from discord_bot.settings.base import BOT_NAME

def home(request):
    url_bot_name = str(os.getenv("BOT_NAME", BOT_NAME)).lower()
    return redirect(f"/{url_bot_name}/commands_help/")