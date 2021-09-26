import discord
import os
import asyncio
import numpy as np
from discord.ext import commands
from youtube_dl import YoutubeDL
from settings import BOT_NAME, COOKIE_FILE
from .music_commands import (
    PLAY_COMMAND_ALIASES, QUEUE_COMMAND_ALIASES, 
    SKIP_COMMAND_ALIASES, SHUFFLE_COMMAND_ALIASES, 
    NOW_PLAYING_COMMAND_ALIASES)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.is_playing = False # To know when the bot is playing music
        self.is_queue_shuffled = False # To know when the queue has been shuffled.

        self.music_queue = [] # [song, channel] The main music queue of songs to play
        self.shuffled_music_queue = [] # [song, channel] used to store temporarily the shuffled queue, this avoids problems when a song is playing it stops.¿
        self.now_playing = [] # [song] To display the info of the current song playing
        self.embeded_queue = [] # The embed info of the queue embed messages.

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
            "simulate": True,
        }

        self.YDL_OPTIONS_PLAYLIST = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "ignoreerrors": True, # Do not stop on download errors.
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
        Returns:
            * If the command is valid
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
        Returns:
            * If the command is valid
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

    def search_youtube_url(self, item, author):
        """
        Util method that takes care of fetching necessary info from a youtube url or item
        to process on a later stage.
        Params: 
            * item: This is the url from youtube
            * author: The user who added the songs to the queue
        Returns:
            * The all the required info of the youtube url.
        """
        if bool(os.getenv("TEST_MODE")):
            self.YDL_OPTIONS["cookiefile"] = COOKIE_FILE

        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{item}", download=False)['entries'][0]
            except Exception:
                return False
        return {
            "source": info["formats"][0]["url"], 
            "title": info["title"], 
            "duration": info["duration"], 
            "thumbnail": info["thumbnail"],
            "url": info["webpage_url"],
            "author": author
        }

    def search_youtube_playlist(self, url, voice_channel, author):
        """
        Util method that takes care of fetching necessary info from a youtube url or item
        to process on a later stage.
        Params: 
            * url: This is playlist url from youtube (Public or Unlisted)
            * voice_channel: The voice channel the bot will play the song
            * author: The user who added the songs to the queue
        Returns:
            * relevant_data: The array with necessary info of the song along with the 
                            voice channel the audio will play.
        """
        if bool(os.getenv("TEST_MODE")):
            self.YDL_OPTIONS_PLAYLIST["cookiefile"] = COOKIE_FILE

        with YoutubeDL(self.YDL_OPTIONS_PLAYLIST) as ydl:
            try:
                relevant_data = []
                info = ydl.extract_info(url, download=False)["entries"]
                for item in info:
                    relevant_data.append([{
                        "source": item["formats"][0]["url"],
                        "title": item["title"],
                        "duration": item["duration"],
                        "thumbnail": item["thumbnail"],
                        "url": item["webpage_url"],
                        "author": author
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
                print("Algo salio mal al conectar al bot.")
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
                if self.is_queue_shuffled == True:
                    # Check if the queue is shuffled to update the queue.
                    # We do this here before a new song starts!
                    self.music_queue = self.shuffled_music_queue
                    self.is_queue_shuffled = False

                # Get the first url
                next_song_url = self.music_queue[0][0]['source']
                
                # Remove the first element of the queue as we will be playing it
                # Add that element to the now_playing array if this information
                # is needed later.
                if len(self.now_playing) > 0:
                    self.now_playing.pop()
                self.now_playing.append(self.music_queue.pop(0)[0])

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

    def convert_seconds(self, seconds):
        """
        Util method that takes seconds and turns them into string 
        in the format hour, minutes and seconds.
        Params:
            * seconds: the amount of seconds to convert.
        """
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        
        return "%d:%02d:%02d" % (hour, minutes, seconds)

    def add_embed_in_queue(self, list_of_songs):
        """
        Util method that adds the list of songs in currently in
        queue to the embed_queue.
        Params:
            * list_of_songs: string with all the songs that will be
            placed in an individual embed message.
        """
        self.embeded_queue.append(discord.Embed(
            title= "Lista de Canciones en cola 🍆",
            color=discord.Color.blurple())
            .add_field(name="Canciones", value=list_of_songs, inline=False)
        )

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
                # This means it is a playlist
                is_playlist = True

            if is_playlist:
                playlist_info = self.search_youtube_playlist(youtube_query, voice_channel, context.author.nick)
                if not playlist_info: 
                    await context.send("Mae no se pudo poner la playlist.")
                else:
                    self.music_queue.extend(playlist_info)
                    await context.send(f"{len(playlist_info)} canciones añadidas a la colaヾ(•ω•`)o")
            else:    
                song_info = self.search_youtube_url(youtube_query, context.author.nick)
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
                current = 0 # Current embed being displayed
                queue_display_msg = ""  # Message added to field of embed object.
                embed_songs = 0 # Each time a song is added to the embed queue.
                queue_display_list = [] # Local list so when a song leaves the queue doesn't generate an index error.
                self.embeded_queue = [] # We reset the embeded queue if multiple calls of queue command are done.
                queue_duration = 0 # Total duration of all the songs in queue.

                if self.is_queue_shuffled == True:
                    # We want to show the user the queue shuffled if he calls this command
                    # after shuffling the queue.
                    queue_display_list = self.shuffled_music_queue

                else:
                    queue_display_list = self.music_queue


                while embed_songs < len(queue_display_list):
                    title = queue_display_list[embed_songs][0]["title"]
                    url = queue_display_list[embed_songs][0]["url"]
                    duration = queue_display_list[embed_songs][0]["duration"]
                    author = queue_display_list[embed_songs][0]["author"]

                    embed_message = f"`{queue_display_msg}{str(embed_songs+1)} -` [{title}]({url})|`{self.convert_seconds(duration)} ({author})`\n"

                    if len(embed_message) < 1024:
                        # This means we reached the maximun that an embed field can handle.
                        if embed_songs < len(queue_display_list):
                            # If we haven't reached the end of the music_queue
                            queue_display_msg += f"`{str(embed_songs+1)} -` [{title}]({url})|`{self.convert_seconds(duration)} ({author})`\n"
                            queue_duration += duration
                            embed_songs += 1

                        if embed_songs == len(queue_display_list):
                            # This means we add the last embed necessary to the
                            # queue.
                            self.add_embed_in_queue(queue_display_msg)
                    else:
                        # So we add that embed to the queue of usable embeds and reset the message
                        # to fill as many other embeds as needed to show all songs in queue.
                        self.add_embed_in_queue(queue_display_msg)
                        queue_display_msg = ""

                if len(self.embeded_queue) == 1:
                    embeded_queue_item = self.embeded_queue[current]
                    if len(queue_display_list) == 1:
                        embeded_queue_item.add_field(name="\u200b", value=f"**{len(queue_display_list)} song in queue | {self.convert_seconds(queue_duration)} queue duration**", inline=False)
                    else:
                        embeded_queue_item.add_field(name="\u200b", value=f"**{len(queue_display_list)} songs in queue | {self.convert_seconds(queue_duration)} queue duration**", inline=False)

                    embeded_queue_item.set_footer(text=f"Page 1/1", icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384061.png")
                    msg = await context.send(embed=embeded_queue_item, delete_after=60.0)
                    
                elif len(self.embeded_queue) > 1:
                    buttons = [u"\u23EA", u"\u2B05", u"\u27A1", u"\u23E9"] # Skip to start, left, right, skip to end buttons.
                    # We only need the pagination functionality if there are multiple embed queue pages.

                    embeded_queue_item = self.embeded_queue[current]
                    embeded_queue_item.add_field(name="\u200b", value=f"**{len(queue_display_list)} songs in queue | {self.convert_seconds(queue_duration)} queue duration**", inline=False)
                    embeded_queue_item.set_footer(text=f"Page {current+1}/{len(self.embeded_queue)}", icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384061.png")

                    msg = await context.send(embed=self.embeded_queue[current])
                    for button in buttons:
                        await msg.add_reaction(button)
    
                    while True:
                        try:
                            reaction, user = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user == context.author and reaction.emoji in buttons, timeout=60.0)

                        except asyncio.TimeoutError:
                            await msg.delete()
                            return print("QUEUE EMBED NATURAL TIMEOUT")

                        else:
                            previous_page = current
                            if reaction.emoji == u"\u23EA": # Skip to Start
                                current = 0
                                
                            elif reaction.emoji == u"\u2B05": # Previous queue page
                                if current > 0:
                                    current -= 1
                                    
                            elif reaction.emoji == u"\u27A1": # Next queue page
                                if current < len(self.embeded_queue)-1:
                                    current += 1

                            elif reaction.emoji == u"\u23E9": # Last queue page
                                current = len(self.embeded_queue)-1

                            for button in buttons:
                                await msg.remove_reaction(button, context.author)

                            if current != previous_page:
                                embeded_queue_item = self.embeded_queue[current]

                                if len(embeded_queue_item.fields) > 1: # If the info field was already added just modify it instead of re adding it.
                                    embeded_queue_item.set_field_at(index=1 ,name="\u200b", value=f"**{len(queue_display_list)} songs in queue | {self.convert_seconds(queue_duration)} queue duration**", inline=False)
                                else:
                                    embeded_queue_item.add_field(name="\u200b", value=f"**{len(queue_display_list)} songs in queue | {self.convert_seconds(queue_duration)} queue duration**", inline=False)
                                
                                embeded_queue_item.set_footer(text=f"Page {current+1}/{len(self.embeded_queue)}", icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384061.png")
                                await msg.edit(embed=embeded_queue_item)

            else: 
                await context.send("Actualmente no hay música en la cola 💔")


    @commands.command(aliases=SKIP_COMMAND_ALIASES)
    @commands.check(check_if_valid)
    async def skip(self, context):
        """
        Command that skip the current song playing on the bot.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if await self.check_self_bot(context):
            if self.vc != "": 
                if self.vc.is_playing():
                    # This will trigger the lambda e function from play_next method to jump to the next song in queue
                    self.vc.stop()
                else:
                    await context.send(f"{os.getenv('BOT_NAME', BOT_NAME)} no esta tocando ninguna canción")  
            else:
                await context.send(f"Actualmente {os.getenv('BOT_NAME', BOT_NAME)} no está en un canal de voz.")

    
    @commands.command(aliases=SHUFFLE_COMMAND_ALIASES)
    @commands.check(check_if_valid)
    async def shuffle(self, context):
        """
        Command that shuffles the order of the current songs on the music queue.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if await self.check_self_bot(context):
            if len(self.music_queue) > 0:
                numpy_array = np.array(self.music_queue)
                np.random.shuffle(numpy_array)
                self.shuffled_music_queue = numpy_array.tolist()
                self.is_queue_shuffled = True
                await context.send("La cola hizo brrr c:")
            else:
               await context.send("La cola no tiene canciones actualmente :c")


    @commands.command(aliases=NOW_PLAYING_COMMAND_ALIASES)
    @commands.check(check_if_valid)
    async def now_playing(self, context):
        """
        Command that shows the info of the current song playing.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if await self.check_self_bot(context):
            if self.is_playing:
                title = self.now_playing[0]["title"]
                url = self.now_playing[0]["url"]
                author = self.now_playing[0]["author"]
                duration = self.now_playing[0]["duration"]

                # [{title}]({url})
                await context.send(
                    embed= discord.Embed(
                        color=discord.Color.blurple())
                        .add_field(name="Canción Actual", value=f"[{title}]({url})")
                        .add_field(name="Duración", value=self.convert_seconds(duration))
                        .add_field(name="Added by", value=author)
                        .set_thumbnail(url=self.now_playing[0]["thumbnail"])
                        , delete_after=60.0
                )
            else:
               await context.send("Actualmente no se está tocando ninguna canción.") 
    
    
    # @commands.command()
    # @commands.check(check_if_music_channel)
    # async def disconnect(self, context):
        #if not ctx.voice_state.voice:
        #     return await ctx.send('Not connected to any voice channel.')

        # await ctx.voice_state.stop()
        # del self.voice_states[ctx.guild.id]








        
