import discord
from discord.ext import commands
from youtube_dl import YoutubeDL
import os

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
        self.YDL_OPTIONS = {"format": "bestaudio"}
        self.vc = "" # Stores current channel

    ################################################################### UTIL METHODS #############################################################

    async def check_if_music_channel(context):
        """
        Util method used as decorator with the @commands.check so it only enables the use of the 
        musicCog commands if the command was issued in the music text channel.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        is_music_channel = False
        if context.message.channel.name == "music":
            is_music_channel = True
        else:
            await context.send("Solo se puede usar la funcionalidad de musica en el canal de 'music'.")
        return is_music_channel

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
    
    async def try_to_connect(self):
        """
        Util method in charge of connecting for the first time the bot to start playing
        the queue of music.
        """
        # Try to connect to a voice channel if you are not already connected
        if self.vc == "" or not self.vc.is_connected():
            self.vc = await self.music_queue[0][1].connect()
        # elif self.vc != self.music_queue[0][1]:
        #     # If the bot is connected but not in the same voice channel as you,
        #     # move to that channel.
        #     self.vc = await self.bot.move_to(self.music_queue[0][1])

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
                self.vc.play(discord.FFmpegPCMAudio(next_song_url, **self.FFMPEG_OPTIONS ), after=lambda e: self.play_next())
                self.vc.source = discord.PCMVolumeTransformer(self.vc.source)
                self.vc.source.volume = 0.7

            except Exception:
                self.is_playing = False
        else:
            self.is_playing = False

    ################################################################### COMMANDS METHODS #########################################################

    @commands.command(name="rolela")
    @commands.check(check_if_music_channel)
    async def play(self, context, *args):
        """
        Command for playing songs, this method will search for the youtube link and 
        add the song to the queue and start playing songs if the bot isn't playing already.
        Params:
            * context: Represents the context in which a command is being invoked under.
            * args: The link of the youtube video
        """
        youtube_query = " ".join(args)

        if context.author.voice is None:
            # The user that perform this command was not in a voice channel
            await context.send("Mae mamaste! No estas en un canal de voz")
        else:
            voice_channel = context.author.voice.channel
            song_info = self.search_youtube_url(youtube_query)
            if not song_info: 
                # This was done for the exception that search_youtube_url can throw if you try to
                # reproduce a playlist or livestream. Search later if this can be avoided.
                await context.send("Mae no se pudo descargar la cancion. Probablemente por ser una playlist o un livestream.")
            else:
                await context.send("Canción añadida a la colaヾ(•ω•`)o")
                self.music_queue.append([song_info, voice_channel])

                if self.is_playing == False:
                    # Try to connect to a voice channel if you are not already connected
                    await self.try_to_connect()
                    self.play_next()


    @commands.command("cola")
    @commands.check(check_if_music_channel)
    async def queue(self, context):
        """
        Command that displays the songs currently on the music queue.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
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


    @commands.command("saltela")
    @commands.check(check_if_music_channel)
    async def skip(self, context):
        if self.vc != "": 
            self.vc.stop()
            # Try to play the next song in the queue if it exists
            self.play_next()
        else:
            await context.send(f"Actualmente {os.getenv('BOT_NAME')} no está en un canal de voz.")
    
    # @commands.command()
    # @commands.check(check_if_music_channel)
    # async def disconnect(self, context):
        #if not ctx.voice_state.voice:
        #     return await ctx.send('Not connected to any voice channel.')

        # await ctx.voice_state.stop()
        # del self.voice_states[ctx.guild.id]








        
