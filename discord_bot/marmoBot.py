import os

import discord
from discord.ext import commands
from halloween_bot.halloween_cog import HalloweenCog
from music_bot.music_cog import MusicCog

if os.getenv("DJANGO_ENV") == "PROD":
    from discord_bot.settings.production import BOT_NAME
elif os.getenv("DJANGO_ENV") == "DEV":
    from discord_bot.settings.dev import BOT_NAME

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="", intents=intents)


async def main():
    await bot.add_cog(MusicCog(bot))
    await bot.add_cog(HalloweenCog(bot))

    try:
        async with bot:
            await bot.start(os.getenv("TOKEN"))
    except Exception as e:
        print("Bot Error: " + str(e))


@bot.event
async def on_ready():
    message = BOT_NAME + " ha despertado!"
    print(message)

    music_channel = os.getenv("MUSIC_CHANNEL")

    if not isinstance(music_channel, int):
        music_channel = int(music_channel)

    channel = bot.get_channel(music_channel)
    if channel:
        await channel.send(message)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
