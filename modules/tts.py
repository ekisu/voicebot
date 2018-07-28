from gtts import gTTS
from config import TTS_LANGUAGE
import asyncio
from concurrent import futures
import discord
from discord.ext import commands
import tempfile
import sys
sys.path.append("..")
from voice_context import VoiceEntry

EXECUTOR = futures.ThreadPoolExecutor(max_workers=6)

class TTSBot:
    def __init__(self, bot, voiceCtx):
        self.bot = bot
        self.voiceCtx = voiceCtx
        self.tts_mode = {}

    @commands.group(pass_context=True, no_pm=True)
    async def v(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        state = await ctx.invoke(self.voiceCtx.obtainVoiceState)

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
        state = await ctx.invoke(self.voiceCtx.obtainVoiceState)
        if not state or not state.is_playing():
            await self.bot.say("Not playing anything.")
            return

        state.skip()

    @v.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        state = await ctx.invoke(self.voiceCtx.obtainVoiceState)
        if not state or not state.messages.empty():
            state.messages = asyncio.Queue()
            await self.bot.say("Queue cleared.")

        state.skip()

    @v.command(pass_context=True, no_pm=True)
    async def leave(self, ctx):
        server = ctx.message.server
        state = await ctx.invoke(self.voiceCtx.obtainVoiceState)

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
        state = await ctx.invoke(self.voiceCtx.obtainVoiceState)
        if not state or not state.voice:
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

        state = self.voiceCtx.get_voice_state(message.server)
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

def register_tts_mode_handler(bot, ttsBot):
    @bot.listen()
    async def on_message(message):
        if message.author == bot.user or message.author.bot:
            return

        if message.content.startswith("!"):
            return

        await ttsBot.addToQueueTTSMode(message)
