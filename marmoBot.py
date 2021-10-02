from discord.ext import commands
import os

from music.music_cog import MusicCog
from halloween.halloween_cog import HalloweenCog

bot = commands.Bot(command_prefix="")

bot.add_cog(MusicCog(bot))
bot.add_cog(HalloweenCog(bot))

bot.run(os.getenv("TOKEN"))