from discord.ext import commands
import os
import discord
from music_bot.music_cog import MusicCog
from halloween_bot.halloween_cog import HalloweenCog

if os.getenv("DJANGO_ENV") == "PROD":
    from discord_bot.settings.production import BOT_NAME, MUSIC_CHANNEL
elif os.getenv("DJANGO_ENV") == "DEV":
    from discord_bot.settings.dev import BOT_NAME, MUSIC_CHANNEL

bot = commands.Bot(command_prefix="")

bot.add_cog(MusicCog(bot))
bot.add_cog(HalloweenCog(bot))

@bot.event
async def on_ready():
    message = BOT_NAME + " ha despertado!"
    print(message)
    channel = bot.get_channel(MUSIC_CHANNEL)
    if channel:
        await channel.send(message)

try:
    bot.run(os.getenv("TOKEN"))
except Exception:
    print("Music Bot Error: "+bot.on_error())