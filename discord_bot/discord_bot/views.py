from django.shortcuts import redirect

from discord_bot.settings import BOT_NAME


def home(request):
    url_bot_name = str(BOT_NAME).lower()
    return redirect(f"/{url_bot_name}/commands_help/")
