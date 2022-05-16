from discord.ext import commands
import os
from discord_bot.settings.base import BOT_NAME

from music_bot.music_cog import MusicCog
from halloween_bot.halloween_cog import HalloweenCog

bot = commands.Bot(command_prefix="")

bot.add_cog(MusicCog(bot))
bot.add_cog(HalloweenCog(bot))

@bot.event
async def on_ready():
    print(os.getenv("BOT_NAME", BOT_NAME) + " ha despertado!")

try:
    bot.run(os.getenv("TOKEN"))
except Exception:
    print(bot.on_error())