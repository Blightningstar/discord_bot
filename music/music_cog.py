from math import e
import discord
import os
from discord.ext import commands
from youtube_dl import YoutubeDL
from .music_commands import PLAY_COMMAND_ALIASES, QUEUE_COMMAND_ALIASES, SKIP_COMMAND_ALIASES
from settings import BOT_NAME, COOKIE_FILE
# from .fetch_yt_playlist import Page, exact_link

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = False
        self.music_queue = [] # [song, channel]
        self.now_playing = [] # [song]
        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn"
        }
        self.YDL_OPTIONS = {
            "format": "bestaudio",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "cookiefile": COOKIE_FILE,
        }

        self.YDL_OPTIONS_PLAYLIST = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "cookiefile": COOKIE_FILE,
        }
        self.vc = "" # Stores current channel

    ################################################################### UTIL METHODS #############################################################

    async def check_if_valid(context):
        """
        Util method used as decorator with the @commands.check so it only enables the use of the 
        musicCog commands if:
            - The command was issued in the music text channel.
            - The author that send the command is in a voice channel.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if context.message.channel.name != "music":
            await context.send("Solo se puede usar la funcionalidad de musica en el canal de 'music'.")
            return False
        elif context.author.voice is None:
            await context.send("Mae mamaste! No estás en un canal de voz")
            return False
        return True

    async def check_self_bot(self, context):
        """
        Util method used to only enable the use of the musicCog commands if:
            - The author that send the command is in the same voice channel as the bot.
            - The bot is playing audio in a voice channel.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        # This means that the user is in a voice channel
        if context.author.voice:
            # This means the bot is currently playing a song
            if self.is_playing:
                # This means that the user is not in the same channel as the bot
                if context.author.voice.channel.name != self.vc.channel.name:
                    await context.send(f"Mae no estás en el mismo canal de voz que {os.getenv('BOT_NAME', BOT_NAME)}.")
                    return False

        command = (context.message.clean_content).split(" ")[0] # Get the command the user used.
        # If command is not the play one it is an error. Since play connects the bot.
        if self.vc == "" and command not in PLAY_COMMAND_ALIASES and command != "play":
            await context.send(f"Mae el {os.getenv('BOT_NAME', BOT_NAME)} no esta en ningun canal de voz.")
            return False
        return True

    def search_youtube_url(self, item):
        """
        Util method that takes care of fetching necessary info from a youtube url or item
        to process on a later stage.
        Params: 
            * item: This is the url from youtube
        Returns:
            * The source and title of the youtube url.
        """
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{item}", download=False)['entries'][0]
            except Exception:
                return False
        return {"source": info["formats"][0]["url"], "title": info["title"], "duration": info["duration"]}

    def search_youtube_playlist(self, url, voice_channel):
        """
        Util method that takes care of fetching necessary info from a youtube url or item
        to process on a later stage.
        Params: 
            * url: This is playlist url from youtube (Public or Unlisted)
        Returns:
            * The source and title of the youtube url.
        """
        with YoutubeDL(self.YDL_OPTIONS_PLAYLIST) as ydl:
            try:
                relevant_data = []
                info = ydl.extract_info(url, download=False)["entries"]
                for item in info:
                    relevant_data.append([{
                        "source": item["formats"][0]["url"],
                        "title": item["title"],
                        "duration": item["duration"]
                    }, voice_channel])
            except Exception:
                return False
        return relevant_data
    
    async def try_to_connect(self):
        """
        Util method in charge of connecting for the first time the bot to start playing
        the queue of music.
        """
        # Try to connect to a voice channel if you are not already connected
        if self.vc == "" or not self.vc:
            try:
                self.vc = await self.music_queue[0][1].connect()
            except:
                pass
        elif self.vc.is_connected():
            if self.vc.channel.name != self.music_queue[0][1].name:
                # If the bot is connected but not in the same voice channel as you,
                # move to that channel.
                self.vc = await self.vc.disconnect()
                self.vc = await self.music_queue[0][1].connect()

    def play_next(self):
        """
        Util method that takes care of recursively playing the queue until it's empty.
        """
        if len(self.music_queue) > 0:
            self.is_playing = True
            try:
                # Get the first url
                next_song_url = self.music_queue[0][0]['source']
                
                # Remove the first element of the queue as we will be playing it
                # Add that element to the now_playing array if this information
                # is needed later.
                if len(self.now_playing) > 0:
                    self.now_playing.pop()
                self.now_playing.append(self.music_queue.pop(0))

                # The Voice Channel we are currently on will start playing the next song
                # Once that song is over "after=lambda e: self.play_next()" will play the 
                # next song if it there is another one queued.
                self.is_playing = True
                self.vc.play(discord.FFmpegPCMAudio(next_song_url, **self.FFMPEG_OPTIONS ), after=lambda e: self.play_next())
                self.vc.source = discord.PCMVolumeTransformer(self.vc.source)
                self.vc.source.volume = 0.7

            except Exception:
                self.is_playing = False
        else:
            self.is_playing = False

    ################################################################### COMMANDS METHODS #########################################################

    @commands.command(aliases=PLAY_COMMAND_ALIASES)
    @commands.check(check_if_valid)
    async def play(self, context, *args):
        """
        Command for playing songs, this method will search for the youtube link and 
        add the song to the queue and start playing songs if the bot isn't playing already.
        Params:
            * context: Represents the context in which a command is being invoked under.
            * args: The link of the youtube video
        """
        if await self.check_self_bot(context):
            youtube_query = " ".join(args)
            is_playlist = False

            voice_channel = context.author.voice.channel
            if "list" in youtube_query:
                # This means it is a list
                is_playlist = True

            if is_playlist:
                playlist_info = self.search_youtube_playlist(youtube_query, voice_channel)
                if not playlist_info: 
                    await context.send("Mae no se pudo poner la playlist.")
                else:
                    self.music_queue.extend(playlist_info)
                    await context.send(f"{len(playlist_info)} canciones añadidas a la colaヾ(•ω•`)o")
            else:    
                song_info = self.search_youtube_url(youtube_query)
                if not song_info: 
                    # This was done for the exception that search_youtube_url can throw if you try to
                    # reproduce a playlist or livestream. Search later if this can be avoided.
                    await context.send("Mae no se pudo descargar la cancion. Probablemente por ser un livestream.")
                else:
                    print(song_info)
                    self.music_queue.append([song_info, voice_channel])
                    await context.send("Canción añadida a la colaヾ(•ω•`)o")

            if self.is_playing == False:
                # Try to connect to a voice channel if you are not already connected
                await self.try_to_connect()
                self.play_next()


    @commands.command(aliases=QUEUE_COMMAND_ALIASES)
    @commands.check(check_if_valid)
    async def queue(self, context):
        """
        Command that displays the songs currently on the music queue.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if await self.check_self_bot(context):
            if len(self.music_queue) > 0:
                queue_display = ""

                for item in range(0, len(self.music_queue)):
                    queue_display += str(item) + " - " + self.music_queue[item][0]["title"] + "\n"
                
                await context.send(embed=
                    discord.Embed(
                        title= "Lista de Canciones en cola", 
                        color=discord.Color.blurple())
                        .add_field(name="Canciones",value=queue_display)
                )
            else: 
                await context.send("Actualmente no hay música en la cola 💔")


    @commands.command(aliases=SKIP_COMMAND_ALIASES)
    @commands.check(check_if_valid)
    async def skip(self, context):
        if await self.check_self_bot(context):
            if self.vc != "": 
                if self.vc.is_playing():
                    self.vc.stop()
                    # Try to play the next song in the queue if it exists
                    self.play_next()
                else:
                    await context.send(f"{os.getenv('BOT_NAME', BOT_NAME)} no esta tocando ninguna canción")  
            else:
                await context.send(f"Actualmente {os.getenv('BOT_NAME', BOT_NAME)} no está en un canal de voz.")
    
    # @commands.command()
    # @commands.check(check_if_music_channel)
    # async def disconnect(self, context):
        #if not ctx.voice_state.voice:
        #     return await ctx.send('Not connected to any voice channel.')

        # await ctx.voice_state.stop()
        # del self.voice_states[ctx.guild.id]








        
