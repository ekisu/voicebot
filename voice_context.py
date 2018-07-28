import asyncio
import discord
from discord.ext import commands

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

class VoiceContext:
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

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

    @commands.command(pass_context=True, no_pm=True, name="summon")
    async def obtainVoiceState(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return None

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return state
