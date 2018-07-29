import os
import discord
import aiohttp
from discord.ext import commands
import sys
sys.path.append("..")
from voice_context import VoiceEntry

class AudiosBot:
    def __init__(self, bot, voiceCtx):
        self.bot = bot
        self.voiceCtx = voiceCtx

    @commands.group(pass_context=True, no_pm=True)
    async def r(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        audioName = ctx.message.content[3:]
        if audioName == "":
            return

        state = await ctx.invoke(self.voiceCtx.obtainVoiceState)
        if not state or not state.voice:
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
