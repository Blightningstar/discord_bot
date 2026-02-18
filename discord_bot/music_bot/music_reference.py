import discord
import youtube_dl
from discord.ext import commands


class music(commands.cog):
    def __init__(self, client):
        self.client = client

    def setup(client):
        client.add_cog(music(client))

    @commands.command()
    async def join(self, ctx):
        # If the person is not in a voice channel
        if ctx.author.voice is None:
            await ctx.send("You're not in a voice channel")
        voice_channel = ctx.author.voice.channel

        # If the bot is not on a voice channel
        if ctx.voice_client is None:
            await voice_channel.connect()
        else:
            await ctx.voice_client.move_to(voice_channel)

    @commands.command()
    async def disconnect(self, ctx):
        await ctx.voice_client.disconnect()

    @commands.command()
    async def play(self, ctx, url):
        ctx.voice_client.stop()
        FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }

        YDL_OPTIONS = {"format": "bestaudio"}
        vc = ctx.voice_client

        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            source = await discord.FFmpegOpusAudio.from_probe(
                info["formats"][0]["url"], **FFMPEG_OPTIONS
            )
            vc.play(source)

    @commands.command()
    async def pause(self, ctx):
        await ctx.voice_client.pause()
        await ctx.send("Pausado ⏸")

    @commands.command()
    async def resume(self, ctx):
        await ctx.voice_client.resume()
        await ctx.send("Reanudado ⏯")
