# client = discord.Client()

# @client.event
# async def on_ready():
#     print("We have logged in as {0.user}".format(client))


# @client.event
# async def on_message(message):
#     username = str(message.author).split('#')[0]
#     user_message = str(message.content)
#     channel = str(message.channel.name)
#     print(f"{username}:{user_message} ({channel})")

#     if message.author == client.user:
#         return

#     if user_message.lower() == "holiwis":
#             await message.channel.send(f"Holiwis {username}!")
#     elif user_message.lower() == "chao":
#         await message.channel.send(f"Ya se va {username}? Llevese esta!")
#     elif user_message.lower() == "mas bien":
#         await message.channel.send(f"loquita")
#     elif user_message.lower() == "soy el mejor":
#         await message.channel.send(f"KOM se la come!")
#     elif user_message.lower() == "ronald":
#         await message.channel.send(f"Disculpe quiso decir Edgy?")
#     elif user_message.lower() == "que hora es?":
#         await message.channel.send(f"Es hora d-d-d-d-d-d-d-d-del duelo!!")

#     if message.channel.name == "music":
#         if user_message.split(' ')[0].lower() == "rolela":
#             # If the person is not in a voice channel
#             if message.author.voice is None:
#                 await message.channel.send("Mae no esta en canal de voz, mamaste!")

#             voice_channel = message.author.voice.channel
#             await message.channel.send(voice_channel)

#             await discord.VoiceChannel.connect()

#             # # If the bot is not on a voice channel
#             # if voice_channel is None:
#             #     await discord.VoiceChannel.connect()
#             # else:
#             #     await discord.VoiceClient.move_to(discord.VoiceClient, voice_channel)

#             # client.voice_client.stop()
#             # FFMPEG_OPTIONS = {
#             #     "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
#             #     "options": "-vn"
#             # }
            
#             # YDL_OPTIONS = {"format": "bestaudio"}
#             # vc = message.voice_client

#             # with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
#             #     info = ydl.extract_info(user_message.split(' ')[1], download=False)
#             #     source = await discord.FFmpegOpusAudio.from_probe(info["formats"][0]["url"], **FFMPEG_OPTIONS)
#             #     vc.play(source)


# client.run(TOKEN)