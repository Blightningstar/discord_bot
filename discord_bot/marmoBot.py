from discord.ext import commands
import os
from music_bot.music_cog import MusicCog
from halloween_bot.halloween_cog import HalloweenCog

if os.getenv("DJANGO_ENV") == "PROD":
    from discord_bot.settings.production import BOT_NAME
elif os.getenv("DJANGO_ENV") == "DEV":
    from discord_bot.settings.dev import BOT_NAME

bot = commands.Bot(command_prefix="")

bot.add_cog(MusicCog(bot))
bot.add_cog(HalloweenCog(bot))

@bot.event
async def on_ready():
    print(BOT_NAME + " ha despertado!")

try:
    bot.run(os.getenv("TOKEN"))
except Exception:
    print(bot.on_error())