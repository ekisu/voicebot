import discord
from gtts import gTTS
import tempfile
from config import TOKEN, TTS_LANGUAGE, COMMAND

client = discord.Client()
players = {}

@client.event
async def on_message(message):
    member = message.author
    server = member.server

    if message.content == COMMAND + " stop":
        if server.id in players and players[server.id] is not None:
            players[server.id].stop()
            players[server.id] = None
    elif message.content.startswith(COMMAND + " "):
        if server.id in players and players[server.id] is not None:
            return

        voice_client = client.voice_client_in(server)
        msg = message.content.strip(COMMAND + " ")
        tts = gTTS(msg, lang=TTS_LANGUAGE)
        voice = None
        if voice_client is not None:
            await voice_client.move_to(member.voice.voice_channel)
            voice = voice_client
        else:
            voice = await client.join_voice_channel(member.voice.voice_channel)

        with tempfile.TemporaryFile() as fp:
            tts.write_to_fp(fp)
            fp.seek(0)
            def afterPlaying():
                players[server.id] = None
            players[server.id] = voice.create_ffmpeg_player(fp, pipe=True, after=afterPlaying)
            players[server.id].start()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run(TOKEN)
