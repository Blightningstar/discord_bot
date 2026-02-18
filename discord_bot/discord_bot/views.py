import os
from django.shortcuts import redirect

if os.getenv("DJANGO_ENV") == "PROD":
    from discord_bot.settings.production import BOT_NAME
elif os.getenv("DJANGO_ENV") == "DEV":
    from discord_bot.settings.dev import BOT_NAME

def home(request):
    url_bot_name = str(BOT_NAME).lower()
    return redirect(f"/{url_bot_name}/commands_help/")