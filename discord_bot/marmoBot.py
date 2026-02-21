import os

import discord
import django
from discord.ext import commands

from discord_bot.settings import BOT_NAME, DISCORD_TOKEN, MUSIC_CHANNEL

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "discord_bot.settings")
django.setup()

from halloween_bot.halloween_cog import HalloweenCog
from music_bot.music_cog import MusicCog

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="", intents=intents)


async def main():
    await bot.add_cog(MusicCog(bot))
    await bot.add_cog(HalloweenCog(bot))

    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    except Exception as e:
        print("Bot Error: " + str(e))


@bot.event
async def on_ready():
    message = BOT_NAME + " ha despertado!"
    print(message)

    music_channel = MUSIC_CHANNEL

    if not isinstance(music_channel, int):
        music_channel = int(music_channel)

    channel = bot.get_channel(music_channel)
    if channel:
        await channel.send(message)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
