import discord
from discord.ext import commands
from gtts import gTTS
import tempfile
import asyncio
import aiohttp
import os
from concurrent import futures
from config import TOKEN, TTS_LANGUAGE, COMMAND

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

EXECUTOR = futures.ThreadPoolExecutor(max_workers=6)

class VoiceEntry:
    def __init__(self, msgCtx, player, tempFile, copycolaTexto = None):
        self.requester = msgCtx.author
        self.channel = msgCtx.channel
        self.player = player
        self.tempFile = tempFile
        self.copycolaTexto = copycolaTexto

class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.messages = asyncio.Queue()
        self.play_next_message = asyncio.Event()
        self.play_next_audio = asyncio.Event()
        self.voice_player = self.bot.loop.create_task(self.voice_player_task())
        self.tts_mode = False

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_message.set)

    async def voice_player_task(self):
        while True:
            self.play_next_message.clear()
            self.current = await self.messages.get()
            if self.current.copycolaTexto != None:
                await self.bot.send_message(self.current.channel, self.current.copycolaTexto)
            self.current.player.start()
            await self.play_next_message.wait()

class Voice:
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}
        self.tts_mode = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state
        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.voice_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.group(pass_context=True, no_pm=True)
    async def v(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        tts = gTTS(ctx.message.content[3:], lang=TTS_LANGUAGE)
        try:
            fp = tempfile.TemporaryFile()
            await self.bot.loop.run_in_executor(EXECUTOR, tts.write_to_fp, fp)
            fp.seek(0)
            player = state.voice.create_ffmpeg_player(fp, pipe=True, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            entry = VoiceEntry(ctx.message, player, fp)
            await state.messages.put(entry)

    @v.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say("Not playing anything.")
            return

        state.skip()

    @v.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        state = self.get_voice_state(ctx.message.server)
        if not state.messages.empty():
            state.messages = asyncio.Queue()
            await self.bot.say("Queue cleared.")

        state.skip()

    @v.command(pass_context=True, no_pm=True)
    async def leave(self, ctx):
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.voice_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @v.command(pass_context=True, no_pm=True)
    async def tts(self, ctx):
        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        server = ctx.message.server
        if server.id not in self.tts_mode or not self.tts_mode[server.id]:
            self.tts_mode[server.id] = True
            await self.bot.say("TTS mode is now on.")
        else:
            self.tts_mode[server.id] = False
            await self.bot.say("TTS mode is now off.")

    async def addToQueueTTSMode(self, message):
        if message.server.id not in self.tts_mode or not self.tts_mode[message.server.id]:
            return

        state = self.get_voice_state(message.server)
        if state.voice is None:
            return

        tts = gTTS(message.content, lang=TTS_LANGUAGE)
        try:
            fp = tempfile.TemporaryFile()
            await self.bot.loop.run_in_executor(EXECUTOR, tts.write_to_fp, fp)
            fp.seek(0)
            player = state.voice.create_ffmpeg_player(fp, pipe=True, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(message.channel, fmt.format(type(e).__name__, e))
        else:
            entry = VoiceEntry(message, player, fp)
            await state.messages.put(entry)

    @commands.group(pass_context=True, no_pm=True)
    async def r(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        audioName = ctx.message.content[3:]
        if audioName == "":
            return

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = state.voice.create_ffmpeg_player("audios/{}.mp3".format(audioName), after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            entry = VoiceEntry(ctx.message, player, None)
            await state.messages.put(entry)

    @r.command(pass_context=True, no_pm=True)
    async def list(self, ctx):
        out = "```"
        for audio in sorted(os.listdir("audios")):
            out += "{}\n".format(audio[:-4]) # remove .mp3
        out += "```"
        await self.bot.say(out)

    @r.command(pass_context=True, no_pm=True)
    async def add(self, ctx, audioName : str, link : str):
        try:
            async with aiohttp.ClientSession() as session, session.get(link) as resp:
                with open("audios/{}.mp3".format(audioName), "wb") as f:
                    f.write(await resp.read())
                    await self.bot.say("`{}` added successfully!".format(audioName))
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))

    @commands.group(pass_context=True, no_pm=True)
    async def c(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        copycolaName = ctx.message.content[3:]
        if copycolaName == "":
            return

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            f = open("copycola/{}.txt".format(copycolaName), "r")
            player = state.voice.create_ffmpeg_player("copycola/{}.mp3".format(copycolaName), after=state.toggle_next)
            texto = f.read()
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            entry = VoiceEntry(ctx.message, player, None, texto)
            await state.messages.put(entry)

    @c.command(pass_context=True, no_pm=True, name="add")
    async def addCopycola(self, ctx, name, *, texto: str):
        tts = gTTS(texto, lang=TTS_LANGUAGE)
        try:
            with open("copycola/{}.txt".format(name), "w") as ftext, open("copycola/{}.mp3".format(name), "wb") as fmp3:
                await self.bot.loop.run_in_executor(EXECUTOR, tts.write_to_fp, fmp3)
                ftext.write(texto)

            await self.bot.say("`{}` added successfully!".format(name))
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))

    @c.command(pass_context=True, no_pm=True, name="list")
    async def listCopycola(self, ctx):
        out = "```"
        for cc in sorted(os.listdir("copycola")):
            if cc.endswith(".mp3"):
                out += "{}\n".format(cc[:-4]) # remove .mp3
        out += "```"
        await self.bot.say(out)

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description='A speech-to-text bot.')
voiceBot = Voice(bot)
bot.add_cog(voiceBot)

@bot.event
async def on_ready():
    print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))

@bot.listen()
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    if message.content.startswith("!"):
        return

    await voiceBot.addToQueueTTSMode(message)

bot.run(TOKEN)
