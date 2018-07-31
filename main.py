import tempfile
import asyncio
import aiohttp
import os
import discord
from discord.ext import commands
from concurrent import futures
from config import TOKEN, TTS_LANGUAGE, COMMAND
from voice_context import VoiceContext
from modules.audios import AudiosBot
from modules.copypaste import CopypasteBot
from modules.tts import TTSBot, register_tts_mode_handler

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description='A speech-to-text bot.')
voiceCtx = VoiceContext(bot)
voiceBot = TTSBot(bot, voiceCtx)
bot.add_cog(voiceCtx)
bot.add_cog(voiceBot)
bot.add_cog(AudiosBot(bot, voiceCtx))
bot.add_cog(CopypasteBot(bot, voiceCtx))

@bot.event
async def on_ready():
    print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))

register_tts_mode_handler(bot, voiceBot)

bot.run(TOKEN)
