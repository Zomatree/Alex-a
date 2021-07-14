import discord
from discord.opus import Decoder
from discord.ext import commands

import wave
import io
import audioop
import aiohttp
import toml
import time
import logging
import textwrap

from mttq import AudioPlayer, AudioRecorder, FRAME_RATE

logging.basicConfig(level=logging.INFO)

with open("config.toml") as f:
    config = toml.load(f)

bot = commands.Bot(commands.when_mentioned_or(config["bot"]["prefix"]))

class KichenSink(discord.AudioSink):
    def __init__(self, play_func):
        self.buffer = [b""]

        self.audio_recorder = AudioRecorder(config, self.buffer)
        self.audio_player = AudioPlayer(config, play_func)

    def write(self, data):
        downsampled, _ = audioop.ratecv(data.data, Decoder.SAMPLE_SIZE//Decoder.CHANNELS, Decoder.CHANNELS, Decoder.SAMPLING_RATE, FRAME_RATE, None)
        self.buffer[0] = downsampled

    def start(self):
        self.audio_recorder.start()
        self.audio_player.start()

@bot.command()
async def join(ctx: commands.Context):
    if not (state := ctx.author.voice):  # type: ignore
        return await ctx.send("Not in vc")

    vc: discord.VoiceClient = await state.channel.connect()

    sink = KichenSink(vc.send_audio_packet)

    vc.listen(sink)
    sink.start()

    await ctx.send("listening for voice commands.")

@bot.command()
async def eval(ctx, *, code: str):
    code = f"async def _runner(): {textwrap.indent(code, '    ')}"
    exec_globals = globals().copy()
    exec(code, exec_globals)

    func_return = await exec_globals["_runner"]()

    if func_return:
        await ctx.send(func_return)

@bot.event
async def on_ready():
    print("ready")

bot.run(config["bot"]["token"])
