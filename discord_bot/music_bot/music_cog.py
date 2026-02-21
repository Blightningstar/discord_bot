import asyncio

import discord
import numpy as np
from discord.ext import commands
from googleapiclient.discovery import build

from discord_bot.settings import BOT_NAME, DEBUG, MUSIC_CHANNEL, YT_API_KEY

from .music_commands import (
    DISCONNECT_COMMAND_ALIASES,
    HELP_COMMAND_ALIASES,
    JOIN_COMMAND_ALIASES,
    MOVE_COMMAND_ALIASES,
    NOW_PLAYING_COMMAND_ALIASES,
    PAUSE_COMMAND_ALIASES,
    PLAY_COMMAND_ALIASES,
    PLAY_NEXT_COMMAND_ALIASES,
    QUEUE_COMMAND_ALIASES,
    RESUME_COMMAND_ALIASES,
    SHUFFLE_COMMAND_ALIASES,
    SKIP_COMMAND_ALIASES,
)
from .music_service import MusicService
from .youtube_extractor import YouTubeExtractorService


class MusicCog(commands.Cog, name="Music Cog"):
    def __init__(self, bot):
        self.bot = bot  # Bot instance

        self.is_playing = False  # To know when the bot is playing music
        self.is_queue_shuffled = False  # To know when the queue has been shuffled
        self.is_paused = False  # To know when the bot is paused

        self.music_queue = []  # [song, channel] The main music queue of songs to play
        self.shuffled_music_queue = (
            []
        )  # [song, channel] used to store temporarily the shuffled queue, this avoids problems when a song is playing
        self.now_playing = []  # [song] To display the info of the current song playing
        self.embeded_queue = []  # The embed info of the queue embed messages

        self.youtube_api_key = YT_API_KEY
        self.youtube = build("youtube", "v3", developerKey=self.youtube_api_key)

        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }

        # Based on git documentation https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L173
        self.YDL_OPTIONS = {}
        self.test_mode = DEBUG

        self.youtube_extractor = YouTubeExtractorService(
            ydl_options=self.YDL_OPTIONS,
            test_mode=self.test_mode,
        )
        self.music_service = MusicService(self)

        self.current_voice_channel = (
            None  # Stores current channel the bot is connected to
        )

        # The endpoint in which the django web page documentation of music commands is running.
        self.help_commands_url = ""
        if self.test_mode is True:
            self.help_commands_url = "http://127.0.0.1:8000/marbotest/commands_help/"

    # UTIL METHODS

    async def _check_if_valid(context):
        """
        Util method used with the @commands.check so it only enables the use of the musicCog commands if:
            - The command was issued in the correct music text channel.
            - The author that sent the command is present in a voice channel.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        Returns:
            * (Boolean)
        """
        accepted_channel = MUSIC_CHANNEL
        if context.message.channel.id != accepted_channel:
            await context.send("Este canal no está aceptando comandos.")
            return False
        elif context.author.voice is None:
            await context.send("Mae mamaste! No estás en un canal de voz")
            return False
        return True

    async def _check_self_bot(self, context):
        """
        Util method used to only enable the use of the musicCog commands if:
            - The author that send the command is in the same voice channel as the bot.
            - The bot is playing audio in a voice channel.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        Returns:
            * (Boolean)
        """
        # This means that the user is in a voice channel
        if context.author.voice:
            # This means the bot is currently playing a song
            if self.is_playing:
                # This means that the user is not in the same channel as the bot
                if (
                    context.author.voice.channel.name
                    != self.current_voice_channel.channel.name
                ):
                    await context.send(
                        f"Mae no estás en el mismo canal de voz que {BOT_NAME}."
                    )
                    return False

        command = (context.message.clean_content).split(" ")[
            0
        ]  # Get the command the user used.
        # If the command is not the play or disconnect one it is an error.
        # Since play connects the bot and disconnects makes it leave a voice channel.
        acepted_commands = ["play", "disconnect"]
        acepted_commands.extend(PLAY_COMMAND_ALIASES)
        acepted_commands.extend(DISCONNECT_COMMAND_ALIASES)
        acepted_commands.extend(PLAY_NEXT_COMMAND_ALIASES)
        if not self.current_voice_channel and command not in acepted_commands:
            await context.send(f"Mae el {BOT_NAME} no esta en ningun canal de voz.")
            return False
        return True

    # COMMANDS METHODS

    @commands.command(aliases=PLAY_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def play(self, context, *args):
        """
        Main Command for playing songs, this method can:
            - Search for a Youtube video based on just text related to a video just like Youtube's search bar
            - Take a Youtube's url
            - Take a Youtube's playlist url
        and then adds the songs to the queue to start playing songs if the bot isn't playing already.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
            * args: The link of the Youtube video or Youtube search text
        """
        if await self._check_self_bot(context):
            youtube_query = " ".join(args)
            voice_channel = context.author.voice.channel
            author_of_command = context.author.name

            youtube_query = self.music_service.sanitize_youtube_query(
                youtube_query=youtube_query
            )
            is_playlist = self.music_service.is_youtube_playlist(
                youtube_query=youtube_query
            )

            if is_playlist:
                await context.send("Procesando la playlist...")
                playlist_info = await self.music_service.search_youtube_playlist(
                    url=youtube_query, context=context
                )
                if not playlist_info:
                    await context.send("Mae no se pudo poner la playlist!")
                else:
                    for songs_added, video in enumerate(playlist_info):
                        self.music_queue.append([video, voice_channel])
                        if songs_added == 1:
                            if self.is_playing is False and self.is_paused is False:
                                # Try to connect to a voice channel if you are not already connected
                                await self.music_service.try_to_connect(
                                    voice_channel_to_connect=voice_channel
                                )
                                await self.music_service.reproduce_next_song_in_queue()

                    await context.send(
                        f"{songs_added} canciones añadidas a la colaヾ(•ω•`)o"
                    )
            else:
                song_info = await self.music_service.search_youtube_url(
                    url=youtube_query, author=author_of_command
                )
                if not song_info:
                    # This was done for the exception that MusicService.search_youtube_url can throw if you try to
                    # reproduce a playlist or livestream. Search later if this can be avoided.
                    await context.send("Mae no se pudo descargar la canción.")
                else:
                    await self.music_service.save_song(
                        url=song_info.url,
                        title=song_info.title,
                        duration=song_info.duration,
                        thumbnail=song_info.thumbnail,
                    )
                    self.music_queue.append([song_info, voice_channel])
                    await context.send("Canción añadida a la colaヾ(•ω•`)o")

            if self.is_playing is False and self.is_paused is False:
                # Try to connect to a voice channel if you are not already connected
                await self.music_service.try_to_connect(
                    voice_channel_to_connect=voice_channel
                )
                await self.music_service.reproduce_next_song_in_queue()

    @commands.command(aliases=QUEUE_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def queue(self, context):
        """
        Command that displays the songs currently on the music queue.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        if await self._check_self_bot(context):
            if len(self.music_queue) > 0:
                current = 0  # Current embed being displayed
                queue_display_msg = ""  # Message added to field of embed object.
                embed_songs = 0  # Each time a song is added to the embed queue.
                queue_display_list = (
                    []
                )  # Local list so when a song leaves the queue doesn't generate an index error.
                self.embeded_queue = (
                    []
                )  # We reset the embeded queue if multiple calls of queue command are done.
                queue_duration = 0  # Total duration of all the songs in queue.

                if self.is_queue_shuffled is True:
                    # We want to show the user the queue shuffled if he calls this command
                    # after shuffling the queue.
                    queue_display_list = self.shuffled_music_queue

                else:
                    queue_display_list = self.music_queue

                while embed_songs < len(queue_display_list):
                    next_song_info = ""
                    song_info = queue_display_list[embed_songs][0]
                    if song_info.title == "" or song_info.duration == 0.0:
                        # This means Youtube Data API couldn't or hasn't retrieved the information
                        # for the song. So we need to fetch it to be able to display it in the queue
                        next_song_info = await self.music_service.retrieve_song(
                            url=self.music_queue[embed_songs][0].url
                        )
                        if not next_song_info:
                            # If retriving the info from our db didn't work
                            next_song_info = (
                                await self.music_service.search_youtube_url(
                                    url=self.music_queue[embed_songs][0].url,
                                    author=self.music_queue[embed_songs][0].author,
                                )
                            )

                        if next_song_info:
                            # If retriving the info from our db worked
                            self.music_queue[embed_songs][0] = next_song_info
                            queue_display_list[embed_songs][0] = next_song_info
                            title = next_song_info.title
                            url = next_song_info.url
                            duration = next_song_info.duration
                            author = next_song_info.author
                        else:
                            # We exhausted our possibilities so we can't play it and
                            # should remove it from the queue
                            self.music_queue.pop(embed_songs)

                    else:
                        # This means we have the information of the song so let's just add it
                        title = queue_display_list[embed_songs][0].title
                        url = queue_display_list[embed_songs][0].url
                        duration = queue_display_list[embed_songs][0].duration
                        author = queue_display_list[embed_songs][0].author

                    embed_message = f"`{queue_display_msg}{str(embed_songs + 1)} -` [{title}]({url})|`{self.music_service.convert_seconds(duration)} ({author})`\n"

                    if len(embed_message) < 1024:
                        # This means we reached the maximun that an embed field can handle.
                        if embed_songs < len(queue_display_list):
                            # If we haven't reached the end of the music_queue
                            queue_display_msg += f"`{str(embed_songs + 1)} -` [{title}]({url})|`{self.music_service.convert_seconds(duration)} ({author})`\n"
                            queue_duration += duration
                            embed_songs += 1

                        if embed_songs == len(queue_display_list):
                            # This means we add the last embed necessary to the
                            # queue.
                            self.music_service.add_embed_in_queue(queue_display_msg)
                    else:
                        # So we add that embed to the queue of usable embeds and reset the message
                        # to fill as many other embeds as needed to show all songs in queue.
                        self.music_service.add_embed_in_queue(queue_display_msg)
                        queue_display_msg = ""

                if len(self.embeded_queue) == 1:
                    embeded_queue_item = self.embeded_queue[current]
                    if len(queue_display_list) == 1:
                        embeded_queue_item.add_field(
                            name="\u200b",
                            value=f"**{len(queue_display_list)} song in queue | {self.music_service.convert_seconds(queue_duration)} queue duration**",
                            inline=False,
                        )
                    else:
                        embeded_queue_item.add_field(
                            name="\u200b",
                            value=f"**{len(queue_display_list)} songs in queue | {self.music_service.convert_seconds(queue_duration)} queue duration**",
                            inline=False,
                        )

                    embeded_queue_item.set_footer(
                        text="Page 1/1",
                        icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384061.png",
                    )
                    msg = await context.send(
                        embed=embeded_queue_item, delete_after=60.0
                    )

                elif len(self.embeded_queue) > 1:
                    buttons = [
                        "\u23ea",
                        "\u2b05",
                        "\u27a1",
                        "\u23e9",
                    ]  # Skip to start, left, right, skip to end buttons.
                    # We only need the pagination functionality if there are multiple embed queue pages.

                    embeded_queue_item = self.embeded_queue[current]
                    embeded_queue_item.add_field(
                        name="\u200b",
                        value=f"**{len(queue_display_list)} songs in queue | {self.music_service.convert_seconds(queue_duration)} queue duration**",
                        inline=False,
                    )
                    embeded_queue_item.set_footer(
                        text=f"Page {current + 1}/{len(self.embeded_queue)}",
                        icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384061.png",
                    )

                    msg = await context.send(embed=self.embeded_queue[current])
                    for button in buttons:
                        await msg.add_reaction(button)

                    while True:
                        try:
                            reaction, user = await self.bot.wait_for(
                                "reaction_add",
                                check=lambda reaction, user: user == context.author
                                and reaction.emoji in buttons,
                                timeout=60.0,
                            )

                        except asyncio.TimeoutError:
                            await msg.delete()
                            return print("QUEUE EMBED NATURAL TIMEOUT")

                        else:
                            previous_page = current
                            if reaction.emoji == "\u23ea":  # Skip to Start
                                current = 0

                            elif reaction.emoji == "\u2b05":  # Previous queue page
                                if current > 0:
                                    current -= 1

                            elif reaction.emoji == "\u27a1":  # Next queue page
                                if current < len(self.embeded_queue) - 1:
                                    current += 1

                            elif reaction.emoji == "\u23e9":  # Last queue page
                                current = len(self.embeded_queue) - 1

                            for button in buttons:
                                await msg.remove_reaction(button, context.author)

                            if current != previous_page:
                                embeded_queue_item = self.embeded_queue[current]

                                if (
                                    len(embeded_queue_item.fields) > 1
                                ):  # If the info field was already added just modify it instead of re adding it.
                                    embeded_queue_item.set_field_at(
                                        index=1,
                                        name="\u200b",
                                        value=f"**{len(queue_display_list)} songs in queue | {self.music_service.convert_seconds(queue_duration)} queue duration**",
                                        inline=False,
                                    )
                                else:
                                    embeded_queue_item.add_field(
                                        name="\u200b",
                                        value=f"**{len(queue_display_list)} songs in queue | {self.music_service.convert_seconds(queue_duration)} queue duration**",
                                        inline=False,
                                    )

                                embeded_queue_item.set_footer(
                                    text=f"Page {current + 1}/{len(self.embeded_queue)}",
                                    icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384061.png",
                                )
                                await msg.edit(embed=embeded_queue_item)

            else:
                await context.send("Actualmente no hay música en la cola 💔")

    @commands.command(aliases=SKIP_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def skip(self, context):
        """
        Command that skips the current song playing on the bot if any.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        if await self._check_self_bot(context):
            if self.current_voice_channel:
                if self.current_voice_channel.is_playing():
                    # This will trigger the lambda e function from MusicService.reproduce_next_song_in_queue method to jump to the next song in queue
                    self.current_voice_channel.stop()
                else:
                    await context.send(f"{BOT_NAME} no esta tocando ninguna canción.")
            else:
                await context.send(
                    f"Actualmente {BOT_NAME} no está en un canal de voz."
                )

    @commands.command(aliases=SHUFFLE_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def shuffle(self, context):
        """
        Command that shuffles the order of the current songs on the music queue if any.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        if await self._check_self_bot(context):
            if len(self.music_queue) > 0:
                numpy_array = np.array(self.music_queue)
                np.random.shuffle(numpy_array)
                self.shuffled_music_queue = numpy_array.tolist()
                self.is_queue_shuffled = True
                await context.send("Le hiciste brrrr a esa cola c:")
            else:
                await context.send("La cola no tiene canciones actualmente :c")

    @commands.command(aliases=NOW_PLAYING_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def now_playing(self, context):
        """
        Command that shows the info of the current song playing if any.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        if await self._check_self_bot(context):
            if self.is_playing:
                title = self.now_playing[0].title
                url = self.now_playing[0].url
                author = self.now_playing[0].author
                duration = self.now_playing[0].duration

                # [{title}]({url})
                await context.send(
                    embed=discord.Embed(color=discord.Color.blurple())
                    .add_field(name="Canción Actual", value=f"[{title}]({url})")
                    .add_field(
                        name="Duración",
                        value=self.music_service.convert_seconds(duration),
                    )
                    .add_field(name="Added by", value=author)
                    .set_thumbnail(url=self.now_playing[0].thumbnail),
                    delete_after=60.0,
                )
            else:
                await context.send("Actualmente no se está tocando ninguna canción.")

    @commands.command(aliases=JOIN_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def join(self, context):
        """
        Command that joins the bot to the voice channel the user that issued this command is in.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        await self.music_service.try_to_connect(context.author.voice.channel)

    @commands.command(aliases=PAUSE_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def pause(self, context):
        """
        Command that pauses the music bot in the voice channel.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        if await self._check_self_bot(context):
            if self.is_playing and self.current_voice_channel:
                self.current_voice_channel.pause()
                self.is_paused = True
                self.is_playing = False
                await context.send(f"Al {BOT_NAME} se le paró... la canción (╹ڡ╹ )")

    @commands.command(aliases=RESUME_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def resume(self, context):
        """
        Command that resumes the paused music bot in the voice channel.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        if await self._check_self_bot(context):
            if self.is_paused and self.current_voice_channel:
                self.current_voice_channel.resume()
                self.is_paused = False
                self.is_playing = True
                await context.send(
                    f"El {BOT_NAME} te seguirá tocando... la canción ♪(´▽｀)"
                )

    @commands.command(aliases=MOVE_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def move(self, context, *args):
        """
        Command for moving a song from X position to Y position in the queue.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
            * args: The numerical position to move in the queue.
        """
        if await self._check_self_bot(context):
            if len(self.music_queue) > 0:
                positions = " ".join(args).split(" ")
                if len(positions) < 3 and positions[0] != "":
                    # This command only works for 1 or 2 parameters.
                    if (
                        len(positions) == 2
                    ):  # Logic when 2 paramaters move X Y = move X -> Y
                        position_one = int(positions[0]) - 1
                        position_two = int(positions[1]) - 1

                        if position_one >= 0 or position_two >= 0:
                            insert_this_item = self.music_queue.pop(position_one)
                            self.music_queue.insert(position_two, insert_this_item)
                            await context.send(
                                f"{insert_this_item[0].title} reprogramada a la posición {position_two + 1}! ✪ ω ✪"
                            )
                        else:
                            await context.send("Los parámetros deben ser mayores a 0!")
                    else:  # Logic when only 1 paramater move X = move X -> 1
                        position_one = int(positions[0]) - 1
                        if position_one >= 0:
                            insert_this_item = self.music_queue.pop(position_one)
                            self.music_queue.insert(0, insert_this_item)
                            await context.send(
                                f"{insert_this_item[0].title} reprogramada a la posición 1! ✪ ω ✪"
                            )
                else:
                    await context.send(
                        "Woa woa alto ahí, este comando solo permite a lo más 1 o 2 parámetros."
                    )
            else:
                await context.send("Actualmente no hay música en la cola 💔")

    @commands.command(aliases=HELP_COMMAND_ALIASES)
    async def help_alias(self, context):
        """
        Command for displaying the available help_commands page.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        accepted_channel = MUSIC_CHANNEL
        if context.message.channel.id != accepted_channel:
            await context.send("Este canal no está aceptando comandos.")
        else:
            await context.send(
                embed=discord.Embed(
                    title="Click aquí para ver la documentación de Comandos del bot de música 🍆",
                    color=discord.Color.blurple(),
                    url=self.help_commands_url,
                ),
                delete_after=60.0,
            )

    @commands.command(aliases=DISCONNECT_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def disconnect(self, context):
        """
        Command for disconnecting and shutting down the music bot.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
        """
        if await self._check_self_bot(context):
            if self.current_voice_channel:
                if self.current_voice_channel.is_connected():
                    voice_client = context.guild.voice_client
                    await voice_client.disconnect()
                    self.current_voice_channel = None
                    self.is_playing = False
                    self.music_queue = []
                    self.now_playing = []
            else:
                await context.send(
                    f"El {BOT_NAME} no está conectado a un canal de voz."
                )

    @commands.command(aliases=PLAY_NEXT_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def play_next(self, context, *args):
        """
        Command to add a song at the beginning of the music queue.
        Params:
            * context: This class contains a lot of meta data an represents the context in which a command is being invoked under
            * args: The link of the Youtube video or Youtube search text
        """
        if await self._check_self_bot(context):
            if len(self.music_queue) > 0:
                youtube_query = " ".join(args)
                voice_channel = context.author.voice.channel
                author_of_command = context.author.name

                youtube_query = self.music_service.sanitize_youtube_query(
                    youtube_query=youtube_query
                )
                is_playlist = self.music_service.is_youtube_playlist(
                    youtube_query=youtube_query
                )

                if not is_playlist:
                    song_info = await self.music_service.search_youtube_url(
                        url=youtube_query, author=author_of_command
                    )
                    if not song_info:
                        # This was done for the exception that MusicService.search_youtube_url can throw if you try to
                        # reproduce a playlist or livestream. Search later if this can be avoided.
                        await context.send("Mae no se pudo descargar la canción.")
                    else:
                        await self.music_service.save_song(
                            url=song_info.url,
                            title=song_info.title,
                            duration=song_info.duration,
                            thumbnail=song_info.thumbnail,
                        )
                        self.music_queue.insert(0, [song_info, voice_channel])
                        await context.send(
                            "Canción añadida al inicio de la colaヾ(•ω•`)o"
                        )
                else:
                    await context.send(
                        "Este comando no procesa listas, para eso use el comando play."
                    )
            else:
                # If there is no queue, this means we can execute the play command just normal
                await self.play(context, *args)
