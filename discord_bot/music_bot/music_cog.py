import discord
import os
import re
import django
import asyncio
import numpy as np
import json, requests
from discord.ext import commands
from youtube_dl import YoutubeDL
from asgiref.sync import sync_to_async
from googleapiclient.discovery import build
from datetime import timedelta

if os.getenv("DJANGO_ENV") == "PROD":
    from discord_bot.settings.production import BOT_NAME
elif os.getenv("DJANGO_ENV") == "DEV":
    from discord_bot.settings.dev import BOT_NAME

django.setup()    
from .models import SongLog

from .music_commands import (
    PLAY_COMMAND_ALIASES, QUEUE_COMMAND_ALIASES, 
    SKIP_COMMAND_ALIASES, SHUFFLE_COMMAND_ALIASES, 
    NOW_PLAYING_COMMAND_ALIASES, JOIN_COMMAND_ALIASES,
    PAUSE_COMMAND_ALIASES, RESUME_COMMAND_ALIASES,
    MOVE_COMMAND_ALIASES, HELP_COMMAND_ALIASES,
    DISCONNECT_COMMAND_ALIASES
)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot # Bot instance

        self.is_playing = False # To know when the bot is playing music
        self.is_queue_shuffled = False # To know when the queue has been shuffled
        self.is_paused = False # To know when the bot is paused

        self.music_queue = [] # [song, channel] The main music queue of songs to play
        self.shuffled_music_queue = [] # [song, channel] used to store temporarily the shuffled queue, this avoids problems when a song is playing
        self.now_playing = [] # [song] To display the info of the current song playing
        self.embeded_queue = [] # The embed info of the queue embed messages
        
        self.youtube_api_key = os.getenv("YT_API_KEY")
        self.youtube = build("youtube", "v3", developerKey=self.youtube_api_key)

        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn"
        }

        # Based on git documentation https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L141
        self.YDL_OPTIONS = {
            "format": "bestaudio",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "age_limit": 40,
            "simulate": True,
        }

        self.YDL_OPTIONS_PLAYLIST = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "age_limit": 40,
            "simulate": True,
            "extract_flat": "in_playlist",
            "ignoreerrors": True, # Do not stop on download errors.
        }
        self.current_voice_channel = None # Stores current channel the bot is connected to

        if os.getenv("DJANGO_ENV") == "PROD":
            self.test_mode = False
        elif os.getenv("DJANGO_ENV") == "DEV":
            self.test_mode = True

        # The endpoint in which the django web page documentation of music commands is running.
        self.help_commands_url = ""
        if os.getenv("DEPLOYED_ON") == "local":
            self.help_commands_url = "http://localhost:8080/marbotest/commands_help/"
        elif os.getenv("DEPLOYED_ON") == "heroku-1":
            self.help_commands_url = "https://discord-marbot.herokuapp.com/marbot/commands_help/"
        elif os.getenv("DEPLOYED_ON") == "heroku-2":
            self.help_commands_url = "https://discord-marbot-2.herokuapp.com/marbot/commands_help/"

    ################################################################### UTIL METHODS #############################################################

    async def _check_if_valid(context):
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
        if os.getenv("DJANGO_ENV") == "PROD":
            accepted_channel = "music"
        elif os.getenv("DJANGO_ENV") == "DEV":
            accepted_channel = "marbot-test"
   
        if context.message.channel.name != accepted_channel:
            await context.send(f"Solo se puede usar la funcionalidad de música en el canal de '{accepted_channel}'.")
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
            * context: Represents the context in which a command is being invoked under.
        Returns:
            * If the command is valid
        """
        # This means that the user is in a voice channel
        if context.author.voice:
            # This means the bot is currently playing a song
            if self.is_playing:
                # This means that the user is not in the same channel as the bot
                if context.author.voice.channel.name != self.current_voice_channel.channel.name:
                    await context.send(f"Mae no estás en el mismo canal de voz que {BOT_NAME}.")
                    return False

        command = (context.message.clean_content).split(" ")[0] # Get the command the user used.
        # If the command is not the play or disconnect one it is an error. 
        # Since play connects the bot and disconnects makes it leave a voice channel.
        acepted_commands = ["play", "disconnect"]
        acepted_commands.extend(PLAY_COMMAND_ALIASES)
        acepted_commands.extend(DISCONNECT_COMMAND_ALIASES)
        if not self.current_voice_channel and command not in acepted_commands:
            await context.send(f"Mae el {BOT_NAME} no esta en ningun canal de voz.")
            return False
        return True

    @sync_to_async
    def _save_song(self, url, title, duration, thumbnail):
        """
        Save an entry with the downloaded song info, this way we don't have to download
        each new song in the future.
        """
        SongLog(
            url=url,
            title=title,
            duration=duration,
            thumbnail=thumbnail
        ).save()

    @sync_to_async
    def _retrieve_song(self, url):
        """
        Return all the data from a song with its unique url
        """
        data = []
        queryset = SongLog.objects.filter(url=url)
        # print(queryset)
        if queryset:
            data = list(queryset)[0]
        return data

    def _search_youtube_url(self, item, author):
        """
        Util method that takes care of fetching necessary info from a youtube url or item
        to process on a later stage.
        Params: 
            * item: This is the url from youtube
            * author: The user who added the songs to the queue
        Returns:
            * All the required info of the youtube url.
        """
        if self.test_mode:
            self.YDL_OPTIONS["cookiefile"] = os.getenv('COOKIE_FILE', "")

        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{item}", download=False)["entries"][0]
            except Exception:
                return False

        url = info["webpage_url"]
        title = info["title"]
        duration = info["duration"]
        thumbnail = info["thumbnail"]

        return {
            "source": info["formats"][0]["url"], 
            "title": title, 
            "duration": duration, 
            "thumbnail": thumbnail,
            "url": url,
            "author": author
        }

    def _format_youtube_duration(self, video_duration):
        """
        Util method that takes the duration of a video in youtube's format and converts it
        to seconds.
        Params:
            * video_duration: Youtube's video duration in its original format, ex: 
        Returns:
            * duration_in_seconds: Video's duration converted in seconds, ex: 132.0
        """
        hours_pattern = re.compile(r"(\d+)H")
        minutes_pattern = re.compile(r"(\d+)M")
        seconds_pattern = re.compile(r"(\d+)S")

        hours = hours_pattern.search(video_duration)
        minutes = minutes_pattern.search(video_duration)
        seconds = seconds_pattern.search(video_duration)

        hours = int(hours.group(1)) if hours else 0
        minutes = int(minutes.group(1)) if minutes else 0 
        seconds = int(seconds.group(1)) if seconds else 0

        duration_in_seconds = timedelta(
            hours = hours,
            minutes = minutes,
            seconds = seconds
        ).total_seconds()

        return duration_in_seconds

    async def _search_youtube_playlist(self, url, context):
        """
        Util method that takes care of fetching necessary info from a youtube url or item
        to process on a later stage.
        Params: 
            * url: This is playlist url from youtube (Public or Unlisted)
            * context: The information of where the request was sent
        Returns:
            * relevant_data: The array with necessary info of each song along with the 
                            voice channel the audio will play.
        """
        relevant_data = []
        playlist_id = url.split("list=")[1]
        URL1 = "https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&fields=items/contentDetails/videoId,nextPageToken&key={}&playlistId={}&pageToken=".format(self.youtube_api_key, playlist_id)
        next_page = ""
        video_list = []

        while True:
            videos_in_page = []

            results = json.loads(requests.get(URL1 + next_page).text)
            if results.get("items", None):
                for video_count, item in enumerate(results["items"]):
                    videos_in_page.append(item["contentDetails"]["videoId"])

                video_list.extend(videos_in_page)

                if "nextPageToken" in results:
                    next_page = results["nextPageToken"]
                else:
                    # print(f"No. of videos: {video_count}")
                    break
            elif results.get("error"):
                error_reason = results["error"].get("errors")[0].get("reason")
                if error_reason == "playlistNotFound":
                    await context.send("Mae la playlist de Youtube está como privada. Pruebe cambiandola a Unlisted o Public.")
                    break
            else:
                await context.send("Mae la playlist de Youtube está vacia.")
                break


        for video_id in video_list:
            # TODO: Maybe instead of searching each item, now that in this point we have
            # the videos ids we can query the db and fetch the data from there
            url = f"https://youtu.be/{video_id}"
            song_log_data = await self._retrieve_song(url=url)
            if song_log_data:
                # If we have the song in our database
                video_info = {
                    "source": "",
                    "title": song_log_data.title, 
                    "duration": song_log_data.duration, 
                    "thumbnail": song_log_data.thumbnail,
                    "url": url,
                    "author": context.author.nick
                }
            else:
                # We don't have the song in our database so we'll fetch and save the info
                videos_request = self.youtube.videos().list(
                    part="contentDetails, snippet",
                    id=video_id
                )
                video_response = videos_request.execute()
                items = video_response.get("items", None)

                if items:
                    content_details = items[0].get("contentDetails")
                    snippet = items[0].get("snippet")
                    duration = content_details.get("duration")

                    title = snippet.get("title")
                    duration = self._format_youtube_duration(duration)
                    thumbnail = snippet.get("thumbnails").get("default").get("url")

                    await self._save_song(
                        url=url,
                        title=title,
                        duration=duration,
                        thumbnail=thumbnail
                    )
                    
                    video_info = {
                        "source": "",
                        "title": title, 
                        "duration": duration, 
                        "thumbnail": thumbnail,
                        "url": url,
                        "author": context.author.nick
                    }

            relevant_data.append(video_info)

        return relevant_data
        

    async def _try_to_connect(self, voice_channel_to_connect=None):
        """
        Util method in charge of connecting for the bot to a voice channel.
        Params:
            * voice_channel_to_connect: it is used to determine if the bot is joining the bot channel
            by the join command or play command.
        """
        if voice_channel_to_connect is None and not self.current_voice_channel: # The play command will join the bot to the voice_channel
            connected = False
            
            # Try to connect to a voice channel if you are not already connected
            while connected == False:
                try:
                    self.current_voice_channel = await asyncio.shield(self.music_queue[0][1].connect())
                    if self.current_voice_channel.is_connected() and self.music_queue[0][1]:
                        if self.current_voice_channel.channel.name != self.music_queue[0][1].name:
                        # If the bot is connected but not in the same voice channel as you,
                        # move to that channel.
                            self.current_voice_channel = await self.current_voice_channel.disconnect()
                            self.current_voice_channel = await self.music_queue[0][1].connect()
                        connected = True
                except Exception as e:
                    print(f"Algo salio mal al conectar al bot: {str(e)}.")
                    break

        else: # The join command will join the bot to the voice channel
            try:
                if not self.current_voice_channel:
                    self.current_voice_channel = await asyncio.shield(voice_channel_to_connect.connect())

                elif self.current_voice_channel and self.current_voice_channel.is_connected():
                    if self.current_voice_channel.channel.name != voice_channel_to_connect.name:
                        # If the bot is connected but not in the same voice channel as you,
                        # move to that channel.
                        self.current_voice_channel = await self.current_voice_channel.disconnect()
                        self.current_voice_channel = await voice_channel_to_connect.connect()
            except Exception as e:
                print(f"Algo salio mal al usar el comando 'join' para conectar al bot: {str(e)}.")


    def _play_next(self):
        """
        Util method that takes care of recursively playing the queue until it's empty.
        Params:
            * context: The information of where the request was sent
        """
        if len(self.music_queue) > 0:
            self.is_playing = True
            next_song_info = ""
            try:
                if self.is_queue_shuffled == True:
                    # Check if the queue is shuffled to update the queue.
                    # We do this here before a new song starts!
                    self.music_queue = self.shuffled_music_queue
                    self.is_queue_shuffled = False

                # Get the first url
                if self.music_queue[0][0].get("source") == "":
                    next_song_player = ""
                    next_song_info = self._search_youtube_url(
                        item=self.music_queue[0][0]["url"],
                        author=self.music_queue[0][0]["author"]
                    )
                    if next_song_info:
                        next_song_player = next_song_info["source"]

                else:
                    next_song_player = self.music_queue[0][0]["source"]
                
                # Remove the first element of the queue as we will be playing it
                # Add that element to the now_playing array if this information
                # is needed later.
                if len(self.now_playing) > 0:
                    self.now_playing.pop()

                if next_song_info:
                    self.now_playing.append(next_song_info)
                    self.music_queue.pop(0)[0]
                    next_song_info = ""
                else:
                    self.now_playing.append(self.music_queue.pop(0)[0])

                # The Voice Channel we are currently on will start playing the next song
                # Once that song is over "after=lambda e: self._play_next()" will play the 
                # next song if it there is another one queued.
                if next_song_player:
                    try:
                        self.current_voice_channel.play(discord.FFmpegPCMAudio(next_song_player, **self.FFMPEG_OPTIONS ), after=lambda e: self._play_next())
                        self.current_voice_channel.source = discord.PCMVolumeTransformer(self.current_voice_channel.source)
                        self.current_voice_channel.source.volume = 3.0
                    except Exception as e:
                        print("Error with FFmpeg: "+str(e))
                        self._play_next()
                else:
                    self._play_next()

            except Exception as e:
                print(str(e))
                self.is_playing = False
        else:
            self.is_playing = False

    def _convert_seconds(self, seconds):
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

    def _add_embed_in_queue(self, list_of_songs):
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

    def _clean_youtube_query(self, youtube_query):
        """
        Clean the youtube query to avoid known problems.
        params:
            * youtube_query: Youtube url to play.
        """
        # Clean videos with a timestamp, avoids request failing
        if "&t=" in youtube_query:
            return youtube_query.split("&t=")[0]
        return youtube_query

    ################################################################### COMMANDS METHODS #########################################################

    @commands.command(aliases=PLAY_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def play(self, context, *args):
        """
        Command for playing songs, this method will search for the youtube link and 
        add the song to the queue and start playing songs if the bot isn't playing already.
        Params:
            * context: Represents the context in which a command is being invoked under.
            * args: The link of the youtube video or youtube search text
        """
        if await self._check_self_bot(context):
            youtube_query = " ".join(args)
            is_playlist = False
            voice_channel = context.author.voice.channel

            if "list" in youtube_query:
                # This means it is a playlist
                is_playlist = True

            youtube_query = self._clean_youtube_query(youtube_query=youtube_query)

            if is_playlist:
                await context.send("Procesando la playlist...")
                playlist_info = await self._search_youtube_playlist(youtube_query, context)
                if not playlist_info: 
                    await context.send("Mae no se pudo poner la playlist!")
                else:
                    for songs_added, video in enumerate(playlist_info):
                        self.music_queue.append([video, voice_channel])
                        if songs_added == 1:
                            if self.is_playing is False and self.is_paused is False:
                                # Try to connect to a voice channel if you are not already connected
                                await self._try_to_connect()
                                self._play_next()

                    await context.send(f"{songs_added} canciones añadidas a la colaヾ(•ω•`)o")
            else:    
                song_info = self._search_youtube_url(youtube_query, context.author.nick)
                if not song_info: 
                    # This was done for the exception that _search_youtube_url can throw if you try to
                    # reproduce a playlist or livestream. Search later if this can be avoided.
                    await context.send("Mae no se pudo descargar la canción.")
                else:
                    await self._save_song(
                        url=song_info["url"],
                        title=song_info["title"],
                        duration=song_info["duration"],
                        thumbnail=song_info["thumbnail"]
                    )
                    self.music_queue.append([song_info, voice_channel])
                    await context.send("Canción añadida a la colaヾ(•ω•`)o")

            if self.is_playing == False and self.is_paused == False:
                # Try to connect to a voice channel if you are not already connected
                await self._try_to_connect()
                self._play_next()


    @commands.command(aliases=QUEUE_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def queue(self, context):
        """
        Command that displays the songs currently on the music queue.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if await self._check_self_bot(context):
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
                    next_song_info = ""
                    song_info = queue_display_list[embed_songs][0]
                    if song_info["title"] == "" or song_info["duration"] == "":
                        # This means Youtube Data API couldn't or hasn't retrieved the information 
                        # for the song. So we need to fetch it to be able to display it in the queue
                        next_song_info = await self._retrieve_song(url=self.music_queue[embed_songs][0]["url"])
                        if not next_song_info: 
                            # If retriving the info from our db didn't work
                            next_song_info = self._search_youtube_url(
                                item=self.music_queue[embed_songs][0]["url"],
                                author=self.music_queue[embed_songs][0]["author"]
                            )

                        if next_song_info: 
                            # If retriving the info from our db worked
                            self.music_queue[embed_songs][0] = next_song_info
                            queue_display_list[embed_songs][0] = next_song_info
                            title = next_song_info["title"]
                            url = next_song_info["url"]
                            duration = next_song_info["duration"]
                            author = next_song_info["author"]
                        else:
                            # We exhausted our possibilities so we can't play it and
                            # should remove it from the queue
                            self.music_queue.pop(embed_songs)

                    else:
                        # This means we have the information of the song so let's just add it
                        title = queue_display_list[embed_songs][0]["title"]
                        url = queue_display_list[embed_songs][0]["url"]
                        duration = queue_display_list[embed_songs][0]["duration"]
                        author = queue_display_list[embed_songs][0]["author"]

                    embed_message = f"`{queue_display_msg}{str(embed_songs+1)} -` [{title}]({url})|`{self._convert_seconds(duration)} ({author})`\n"

                    if len(embed_message) < 1024: # TODO NEED TO MAKE THIS ONLY LOAD 
                        # This means we reached the maximun that an embed field can handle.
                        if embed_songs < len(queue_display_list):
                            # If we haven't reached the end of the music_queue
                            queue_display_msg += f"`{str(embed_songs+1)} -` [{title}]({url})|`{self._convert_seconds(duration)} ({author})`\n"
                            queue_duration += duration
                            embed_songs += 1

                        if embed_songs == len(queue_display_list):
                            # This means we add the last embed necessary to the
                            # queue.
                            self._add_embed_in_queue(queue_display_msg)
                    else:
                        # So we add that embed to the queue of usable embeds and reset the message
                        # to fill as many other embeds as needed to show all songs in queue.
                        self._add_embed_in_queue(queue_display_msg)
                        queue_display_msg = ""

                if len(self.embeded_queue) == 1:
                    embeded_queue_item = self.embeded_queue[current]
                    if len(queue_display_list) == 1:
                        embeded_queue_item.add_field(name="\u200b", value=f"**{len(queue_display_list)} song in queue | {self._convert_seconds(queue_duration)} queue duration**", inline=False)
                    else:
                        embeded_queue_item.add_field(name="\u200b", value=f"**{len(queue_display_list)} songs in queue | {self._convert_seconds(queue_duration)} queue duration**", inline=False)

                    embeded_queue_item.set_footer(text=f"Page 1/1", icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384061.png")
                    msg = await context.send(embed=embeded_queue_item, delete_after=60.0)
                    
                elif len(self.embeded_queue) > 1:
                    buttons = [u"\u23EA", u"\u2B05", u"\u27A1", u"\u23E9"] # Skip to start, left, right, skip to end buttons.
                    # We only need the pagination functionality if there are multiple embed queue pages.

                    embeded_queue_item = self.embeded_queue[current]
                    embeded_queue_item.add_field(name="\u200b", value=f"**{len(queue_display_list)} songs in queue | {self._convert_seconds(queue_duration)} queue duration**", inline=False)
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
                                    embeded_queue_item.set_field_at(index=1 ,name="\u200b", value=f"**{len(queue_display_list)} songs in queue | {self._convert_seconds(queue_duration)} queue duration**", inline=False)
                                else:
                                    embeded_queue_item.add_field(name="\u200b", value=f"**{len(queue_display_list)} songs in queue | {self._convert_seconds(queue_duration)} queue duration**", inline=False)
                                
                                embeded_queue_item.set_footer(text=f"Page {current+1}/{len(self.embeded_queue)}", icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384061.png")
                                await msg.edit(embed=embeded_queue_item)

            else: 
                await context.send("Actualmente no hay música en la cola 💔")


    @commands.command(aliases=SKIP_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def skip(self, context):
        """
        Command that skips the current song playing on the bot.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if await self._check_self_bot(context):
            if self.current_voice_channel: 
                if self.current_voice_channel.is_playing():
                    # This will trigger the lambda e function from _play_next method to jump to the next song in queue
                    self.current_voice_channel.stop()
                else:
                    await context.send(f"{BOT_NAME} no esta tocando ninguna canción.")  
            else:
                await context.send(f"Actualmente {BOT_NAME} no está en un canal de voz.")

    
    @commands.command(aliases=SHUFFLE_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def shuffle(self, context):
        """
        Command that shuffles the order of the current songs on the music queue.
        Params:
            * context: Represents the context in which a command is being invoked under.
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
        Command that shows the info of the current song playing.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if await self._check_self_bot(context):
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
                        .add_field(name="Duración", value=self._convert_seconds(duration))
                        .add_field(name="Added by", value=author)
                        .set_thumbnail(url=self.now_playing[0]["thumbnail"])
                        , delete_after=60.0
                )
            else:
               await context.send("Actualmente no se está tocando ninguna canción.") 
    

    @commands.command(aliases=JOIN_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def join(self, context):
        """
        Command that joins the bot to a voice channel.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        await self._try_to_connect(context.author.voice.channel)


    @commands.command(aliases=PAUSE_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def pause(self, context):
        """
        Command that pauses the music bot in the voice channel.
        Params:
            * context: Represents the context in which a command is being invoked under.
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
        Command that resumes the pauses music bot in the voice channel.
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if await self._check_self_bot(context):
            if self.is_paused == True and self.current_voice_channel:
                self.current_voice_channel.resume()
                self.is_paused = False
                self.is_playing = True
                await context.send(f"El {BOT_NAME} te seguirá tocando... la canción ♪(´▽｀)") 


    @commands.command(aliases=MOVE_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def move(self, context, *args):
        """
        Command for moving a song from position X to position Y
        Params:
            * context: Represents the context in which a command is being invoked under.
            * args: The numerical position to move in the queue.
        """
        if await self._check_self_bot(context):
            if len(self.music_queue) > 0:
                positions =  " ".join(args).split(" ")
                if len(positions) < 3 and positions[0] != "":
                    # This command only works for 1 or 2 parameters.
                    if len(positions) == 2: # Logic when 2 paramaters move X Y = move X -> Y
                        position_one = int(positions[0])-1
                        position_two = int(positions[1])-1

                        if position_one >= 0 or position_two >= 0:
                            insert_this_item = self.music_queue.pop(position_one)
                            self.music_queue.insert(position_two, insert_this_item)
                            await context.send(f"{insert_this_item[0]['title']} reprogramada a la posición {position_two+1}! ✪ ω ✪")
                        else:
                            await context.send("Los parámetros deben ser mayores a 0!")  
                    else: # Logic when only 1 paramater move X = move X -> 1
                        position_one = int(positions[0])-1
                        if position_one >= 0:
                            insert_this_item = self.music_queue.pop(position_one)
                            self.music_queue.insert(0, insert_this_item)
                            await context.send(f"{insert_this_item[0]['title']} reprogramada a la posición 1! ✪ ω ✪")
                else:
                    await context.send("Woa woa alto ahí, este comando solo permite a lo más 1 o 2 parámetros.")  
            else:
                await context.send("Actualmente no hay música en la cola 💔")


    @commands.command(aliases=HELP_COMMAND_ALIASES)
    async def help_alias(self, context):
        """
        Command for displaying the available help_commands
        Params:
            * context: Represents the context in which a command is being invoked under.
        """
        if self.test_mode:
            accepted_channel = "marbot-test"
        else:
            accepted_channel = "music"

        if context.message.channel.name != accepted_channel:
            await context.send(f"Solo se puede usar la funcionalidad de música en el canal de '{accepted_channel}'.")
        else:
            await context.send(
                embed=discord.Embed(
                    title= "Click aquí para ver la documentación de Comandos del bot de música 🍆", 
                    color=discord.Color.blurple(),
                    url=self.help_commands_url)
                    , delete_after=60.0
            )


    @commands.command(aliases=DISCONNECT_COMMAND_ALIASES)
    @commands.check(_check_if_valid)
    async def disconnect(self, context):
        """
        Command for disconnecting the music bot
        Params:
            * context: Represents the context in which a command is being invoked under.
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
                await context.send(f"El {BOT_NAME} no está conectado a un canal de voz.")
