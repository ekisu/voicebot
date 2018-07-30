import asyncio
from concurrent import futures
import os
import discord
from discord.ext import commands
import sys
import aiohttp
from gtts import gTTS
sys.path.append("..")
from voice_context import VoiceEntry

EXECUTOR = futures.ThreadPoolExecutor(max_workers=6)

class CopypasteBot:
    def __init__(self, bot, voiceCtx):
        self.bot = bot
        self.voiceCtx = voiceCtx

    @commands.group(pass_context=True, no_pm=True)
    async def c(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        copycolaName = ctx.message.content[3:]
        if copycolaName == "":
            return

        state = await ctx.invoke(self.voiceCtx.obtainVoiceState)
        if not state or not state.voice:
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
