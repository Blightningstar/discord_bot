import asyncio

import discord
from discord.ext import commands
from django.conf import settings
from environs import Env
from halloween_bot.halloween_cog import HalloweenCog
from music_bot.music_cog import MusicCog

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="", intents=intents)

env = Env()
env.read_env()


async def main():
    await bot.add_cog(MusicCog(bot, settings.BOT_NAME))
    await bot.add_cog(HalloweenCog(bot))
    try:
        async with bot:
            await bot.start(env.str("TOKEN"))
    except Exception as e:
        print("Bot Error: " + str(e))


@bot.event
async def on_ready():
    message = settings.BOT_NAME + " ha despertado!"
    print(message)
    music_channel = env.str("MUSIC_CHANNEL")
    if not isinstance(music_channel, int):
        music_channel = int(music_channel)
    channel = bot.get_channel(music_channel)
    if channel:
        await channel.send(message)


if __name__ == "__main__":
    asyncio.run(main())
