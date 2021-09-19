from discord.ext import commands
import os

from music.music_cog import MusicCog

bot = commands.Bot(command_prefix="/")

bot.add_cog(MusicCog(bot))

bot.run(os.getenv("TOKEN"))