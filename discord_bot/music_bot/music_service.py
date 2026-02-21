import asyncio
import json
import re
from datetime import timedelta
from typing import Optional

import discord
import requests
import validators
from asgiref.sync import sync_to_async

from .dto import SongInfoDTO
from .models import SongLog


class MusicService:
    def __init__(self, cog):
        self.cog = cog

    def get_song_id(self, url: str) -> str:
        """
        Get the unique Youtube video url id of a song.
        Params:
            * (String) url: The complete url of a Youtube video
        Returns:
            * (String) song_id: The unique identifier of a Youtube video
        """
        song_id = url.split("/")[-1]
        song_id = song_id.split("=")[-1]
        return song_id

    @sync_to_async
    def save_song(self, url: str, title: str, duration: float, thumbnail: str):
        """
        Save an entry with the downloaded song info, this way we don't have to download each new song in the future.
        Params:
            * (String) url: The complete url of a Youtube video
            * (String) title: The Youtube title of a video
            * (Float) duration: The duration of a Youtube video in seconds
            * (String) thumbnail: The miniature thumbnail of a Youtube video
        """
        unique_url = self.get_song_id(url)
        SongLog(
            url=unique_url, title=title, duration=duration, thumbnail=thumbnail
        ).save()

    @sync_to_async
    def retrieve_song(self, url: str) -> "Optional[SongInfoDTO]":
        """
        Return all the data from a song with its unique url.
        Params:
            * (String) url: The complete url of a Youtube video
        Returns:
            * (SongInfoDTO | None): DTO populated from the SongLog DB entry, or None if not found
        """
        unique_url = self.get_song_id(url)
        queryset = SongLog.objects.filter(url=unique_url)
        if queryset:
            song_log = list(queryset)[0]
            return SongInfoDTO(
                author="",
                url=url,
                title=song_log.title or "",
                duration=float(song_log.duration or 0.0),
                thumbnail=str(song_log.thumbnail) if song_log.thumbnail else None,
            )
        return None

    def find_best_song_format(self, format_list: list) -> str:
        """
        Util Method that selects the best audio quality for a song based on audio_channels available,
        quality of audio & codification of the video.
        Params:
            * (List) format_list: A list of the different quality of videos a Youtube video has available
        Returns:
            * (String): The url of the best quality audio based on different parameters
        """
        for f in format_list:
            if f.get("url") and f.get("acodec") and f.get("acodec") != "none":
                return f["url"]
        for f in format_list:
            if f.get("url"):
                return f["url"]
        return None

    async def search_youtube_url(self, url: str, author: str) -> dict:
        """
        Util method that takes care of fetching necessary info from a Youtube url or video name
        to process on a later stage.
        Params:
            * (String) url: The complete url of a Youtube video or the name of a video to search on Youtube
            * (String) author: The name of the discord user that issued the command to search the song, used to save the author of the song in the music queue
        Returns:
            * (Dictionary) A dictionary with all the relevant info of a song, such as title, duration, thumbnail and url, this info is used to save the song in the music queue and to display the song info in the now playing embed.
        """
        return await self.cog.youtube_extractor.search(url=url, author=author)

    def format_youtube_duration(self, video_duration: str) -> float:
        """
        Takes the duration of a video in Youtube's format and converts it
        to seconds.
        Params:
            * (String) video_duration: Youtube's video duration in its original format, ex: PT2M14S
        Returns:
            * (Float) duration_in_seconds: Video's duration converted in seconds, ex: 134.0
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

        return timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds()

    async def search_youtube_playlist(self, url: str, context) -> list:
        """
        Search a Youtube playlist and return a list of dictionaries with the relevant data of each song in the playlist.
        Params:
            * (String) url: The complete url of a Youtube playlist
            * (Object) context: The context of the command that triggered the search, used to send messages to the channel if the playlist is empty or private.
        Returns:
            * (List) relevant_data: A list of dictionaries with the relevant data of each song in the playlist, such as title, duration, thumbnail and url.
        """
        relevant_data = []
        playlist_id = url.split("list=")[1]
        URL1 = "https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&fields=items/contentDetails/videoId,nextPageToken&key={}&playlistId={}&pageToken=".format(
            self.cog.youtube_api_key, playlist_id
        )
        next_page = ""
        video_list = []

        while True:
            videos_in_page = []
            results = json.loads(requests.get(URL1 + next_page).text)

            if results.get("items", None):
                for item in results["items"]:
                    videos_in_page.append(item["contentDetails"]["videoId"])

                video_list.extend(videos_in_page)

                if "nextPageToken" in results:
                    next_page = results["nextPageToken"]
                else:
                    break
            elif results.get("error"):
                error_reason = results["error"].get("errors")[0].get("reason")
                if error_reason == "playlistNotFound":
                    await context.send(
                        "Mae la playlist de Youtube está como privada. Pruebe cambiandola a Unlisted o Public."
                    )
                    break
            else:
                await context.send("Mae la playlist de Youtube está vacia.")
                break

        for video_id in video_list:
            video_url = f"https://youtu.be/{video_id}"
            song_log_data = await self.retrieve_song(url=video_url)

            if song_log_data:
                video_info = SongInfoDTO(
                    author=context.author.nick or "",
                    url=video_url,
                    title=song_log_data.title or "",
                    duration=float(song_log_data.duration or 0.0),
                    thumbnail=(
                        str(song_log_data.thumbnail)
                        if song_log_data.thumbnail
                        else None
                    ),
                )
            else:
                videos_request = self.cog.youtube.videos().list(
                    part="contentDetails, snippet", id=video_id
                )
                loop = asyncio.get_running_loop()

                def fetch_video():
                    return videos_request.execute()

                try:
                    video_response = await loop.run_in_executor(None, fetch_video)
                except Exception as e:
                    print(f"Error fetching video info from YouTube Data API: {e}")
                    continue

                items = video_response.get("items", None)
                if not items:
                    continue

                content_details = items[0].get("contentDetails")
                snippet = items[0].get("snippet")
                duration = self.format_youtube_duration(content_details.get("duration"))
                title = snippet.get("title")
                thumbnail = snippet.get("thumbnails").get("default").get("url")

                await self.save_song(
                    url=video_url, title=title, duration=duration, thumbnail=thumbnail
                )

                video_info = SongInfoDTO(
                    author=context.author.nick or "",
                    url=video_url,
                    title=title or "",
                    duration=float(duration or 0.0),
                    thumbnail=thumbnail,
                )

            relevant_data.append(video_info)

        return relevant_data

    async def try_to_connect(self, voice_channel_to_connect=None):
        """
        Util method in charge of connecting for the bot to a voice channel.
        Params:
            * (Class) voice_channel_to_connect: The discord voice channel from which a user issued a join command.
            It is used to determine if the bot is joining the voice channel via the join or play command
        """
        if voice_channel_to_connect is None and not self.cog.current_voice_channel:
            if not self.cog.music_queue:
                return

            connected = False
            while connected is False:
                try:
                    if not self.cog.music_queue:
                        break
                    self.cog.current_voice_channel = await asyncio.shield(
                        self.cog.music_queue[0][1].connect()
                    )
                    if (
                        self.cog.current_voice_channel.is_connected()
                        and self.cog.music_queue[0][1]
                    ):
                        if (
                            self.cog.current_voice_channel.channel.name
                            != self.cog.music_queue[0][1].name
                        ):
                            await self.cog.current_voice_channel.disconnect()
                            self.cog.current_voice_channel = await self.cog.music_queue[
                                0
                            ][1].connect()
                        connected = True
                except Exception as e:
                    print(f"Algo salio mal al conectar al bot: {str(e)}.")
                    break
        else:
            try:
                if not self.cog.current_voice_channel:
                    self.cog.current_voice_channel = await asyncio.shield(
                        voice_channel_to_connect.connect()
                    )
                elif self.cog.current_voice_channel.is_connected():
                    if (
                        self.cog.current_voice_channel.channel.name
                        != voice_channel_to_connect.name
                    ):
                        await self.cog.current_voice_channel.disconnect()
                        self.cog.current_voice_channel = (
                            await voice_channel_to_connect.connect()
                        )
            except Exception as e:
                print(
                    f"Algo salio mal al usar el comando 'join' para conectar al bot: {str(e)}."
                )

    async def reproduce_next_song_in_queue(self):
        """
        Util method that takes care of recursively playing the music queue until it's empty.
        """
        if len(self.cog.music_queue) > 0:
            self.cog.is_playing = True
            next_song_info = ""
            try:
                if self.cog.is_queue_shuffled is True:
                    self.cog.music_queue = self.cog.shuffled_music_queue
                    self.cog.is_queue_shuffled = False

                if self.cog.music_queue[0][0].source == "":
                    next_song_source_player = ""
                    next_song_info = await self.search_youtube_url(
                        url=self.cog.music_queue[0][0].url,
                        author=self.cog.music_queue[0][0].author,
                    )
                    if next_song_info:
                        next_song_source_player = next_song_info.source
                else:
                    next_song_source_player = self.cog.music_queue[0][0].source

                if len(self.cog.now_playing) > 0:
                    self.cog.now_playing.pop()

                if next_song_info:
                    self.cog.now_playing.append(next_song_info)
                    self.cog.music_queue.pop(0)[0]
                else:
                    self.cog.now_playing.append(self.cog.music_queue.pop(0)[0])

                if next_song_source_player:
                    try:
                        play_source = discord.FFmpegPCMAudio(
                            source=next_song_source_player, **self.cog.FFMPEG_OPTIONS
                        )
                        self.cog.current_voice_channel.play(
                            source=play_source,
                            after=lambda e: asyncio.run_coroutine_threadsafe(
                                self.reproduce_next_song_in_queue(), self.cog.bot.loop
                            ),
                        )
                        self.cog.current_voice_channel.source.volume = 3.0
                    except Exception as e:
                        print("Error with FFmpeg: " + str(e))
                        await self.reproduce_next_song_in_queue()
                else:
                    await self.reproduce_next_song_in_queue()

            except Exception as e:
                print(str(e))
                self.cog.is_playing = False
        else:
            self.cog.is_playing = False

    def convert_seconds(self, seconds: int) -> str:
        """
        Util method that takes seconds and turns them into string in the format hour, minutes and seconds.
        Params:
            * (Integer) seconds: The amount of seconds to convert
        Returns:
            * (String): An amount of time comprised of Hours, Minutes and Seconds
        """
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%d:%02d:%02d" % (hour, minutes, seconds)

    def add_embed_in_queue(self, list_of_songs: str):
        """
        Util method that adds a list of songs currently in queue to the embed_queue.
        Params:
            * (String) list_of_songs: All the songs that will be placed in an individual embed message.
        """
        self.cog.embeded_queue.append(
            discord.Embed(
                title="Lista de Canciones en cola 🍆", color=discord.Color.blurple()
            ).add_field(name="Canciones", value=list_of_songs, inline=False)
        )

    def sanitize_youtube_query(self, youtube_query: str) -> str:
        """
        Sanitize the Youtube query to avoid problems, like from timestamps.
        Params:
            * (String) youtube_query: A Youtube url received by the bot
        Returns:
            * (String) youtube_query: A Youtube url without timestamps
        """
        if validators.url(youtube_query) and "&t=" in youtube_query:
            return youtube_query.split("&t=")[0]
        return youtube_query

    def is_youtube_playlist(self, youtube_query: str) -> bool:
        """
        Checks if a Youtube query is a Youtube playlist.
        Params:
            * (String) youtube_query: A Youtube url received by the bot
        Returns:
            * (Boolean)
        """
        return validators.url(youtube_query) and "list" in youtube_query
