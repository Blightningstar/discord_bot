from discord.ext import commands
import os
import settings

from music.music_cog import MusicCog
from halloween.halloween_cog import HalloweenCog

bot = commands.Bot(command_prefix="")

bot.add_cog(MusicCog(bot))
bot.add_cog(HalloweenCog(bot))

@bot.event
async def on_ready():
    print(os.getenv("BOT_NAME", settings.BOT_NAME) + " ha despertado!")

bot.run(os.getenv("TOKEN"))