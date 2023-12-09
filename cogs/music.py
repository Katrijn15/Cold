import discord
import aiohttp
import yt_dlp as youtube_dl
import asyncio
from typing import Optional
from datetime import datetime
from discord.ext import commands, tasks

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


YTDL_FORMAT_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    # binds to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(YTDL_FORMAT_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if data is not None:
            if 'entries' in data:
                data = data['entries'][0]
        else:
            return None

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return [cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data), data]
    # ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class Music(commands.Cog):

    bad_request_error_message = ''
    bad_request_error_message += (
        ''.join("Bad response while searching for the music\n\n"))
    bad_request_error_message += (''.join("**Possible causes include:**\n"))
    bad_request_error_message += (
        ''.join("*1. bad network on the bot's end;\n"))
    bad_request_error_message += (
        ''.join("2. the given search query couldn't find matching results;*\n"))
    bad_request_error_message += (''.join(
        "***3. too many queuing requests made, without letting the bot to respond to them;***\n"))
    bad_request_error_message += (''.join(
        "\n**To avoid any further unexpected errors, make the bot rejoin the voice channel using `<prefix> leave` and then `<prefix> join`**\n"))
    bad_request_error_message += (''.join("**SORRY FOR THE INCONVENIENCE!**"))

    embed_error_no_vc_dex = discord.Embed(
        title="Error",
        description=''.join(
            "Dex is not in any voice channel\n**Use `<prefix> join` to make it connect to one and then use music commands**"),
        colour=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )

    embed_error_empty_queue = discord.Embed(
        title="Queue",
        description=''.join(
            "Queue is empty, nothing to play\nUse `<prefix> play <query/url>` to add to queue"),
        colour=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )

    MUSIC_ICON = "https://user-images.githubusercontent.com/63065397/156855077-ce6e0896-cc81-4d4d-98b8-3e7b70050afe.png"
    # ----------------------------------------------------------------------------------------------------------------------

    def __init__(self, bot):
        self.bot = bot
        # -------------------------------------
        self.properties = {}
        # FORMAT OF DICT self.properties:
        # [str(guild.id)] -> {
        # "is_playing": False,
        # "currently_playing_player": None,
        # "current": -1,
        # "queued": 0,
        # "vol": 1,
        # "loop_queue": False,
        # "repeat_song": False,
        # "inside_keep_playing": False,
        # "inactive_time": 0,
        # "alone_time": 0,
        # "last_ctx": None
        # }
        # -------------------------------------
        self.music_queue = {}
        # FORMAT OF DICT self.music_queue:
        # [str(guild.id)] -> [0 player | 1 ctx | 2 url(from_user) | 3 stream_or_not(true/false)]
        # -------------------------------------
        self.timeout_check.start()
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @tasks.loop(seconds=1)
    async def timeout_check(self):
        for guild_id in self.properties.keys():
            bot_voice_client = self.bot.get_guild(int(guild_id)).voice_client
            if bot_voice_client is None:
                self.properties[guild_id]["inactive_time"] = -1
                self.properties[guild_id]["alone_time"] = -1
                continue
            if len(self.music_queue[guild_id]) == 0:
                self.properties[guild_id]["inactive_time"] += 1
            else:
                self.properties[guild_id]["inactive_time"] = 0
            if len(bot_voice_client.channel.members) == 1:
                self.properties[guild_id]["alone_time"] += 1
            else:
                self.properties[guild_id]["alone_time"] = 0
            if (self.properties[guild_id]["inactive_time"] == 600) or (self.properties[guild_id]["alone_time"] == 600):
                ctx = self.properties[guild_id]["last_ctx"]
                self.remove_guild(ctx)
                await bot_voice_client.disconnect()
                async with ctx.typing():
                    embed = discord.Embed(
                        title="",
                        description="",
                        color=0xff0000
                    )
                    embed.set_author(
                        name="Left the voice channel due to inactivity")
                await ctx.send(reference=ctx.message, embed=embed)
                self.properties[guild_id]["inactive_time"] = -1
                self.properties[guild_id]["alone_time"] = -1
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member != self.bot.user:
            return
        if before.channel is None:
            return
        if after.channel is None:
            if str(before.channel.guild.id) in self.properties.keys():
                self.properties.pop(str(before.channel.guild.id))
            if str(before.channel.guild.id) in self.music_queue.keys():
                self.music_queue.pop(str(before.channel.guild.id))
            return
        return
    # ----------------------------------------------------------------------------------------------------------------------

    def add_guild(self, ctx):
        if str(ctx.guild.id) not in self.properties:
            # properties dict initialization:
            self.properties[str(ctx.guild.id)] = {
                "is_playing": False,
                "currently_playing_player": None,
                "current": -1,
                "queued": 0,
                "vol": 1,
                "loop_queue": False,
                "repeat_song": False,
                "inside_keep_playing": False,
                "inactive_time": 0,
                "alone_time": 0,
                "last_ctx": None
            }
        self.properties[str(ctx.guild.id)]["last_ctx"] = ctx
        if str(ctx.guild.id) not in self.music_queue.keys():
            self.music_queue[str(ctx.guild.id)] = []
        return
    # ----------------------------------------------------------------------------------------------------------------------

    def remove_guild(self, ctx):
        if str(ctx.guild.id) in self.properties.keys():
            self.properties.pop(str(ctx.guild.id))
        if str(ctx.guild.id) in self.music_queue.keys():
            self.music_queue.pop(str(ctx.guild.id))
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="join", aliases=["connect"], description="joins the voice channel of the author")
    async def join(self, ctx):
        if ctx.author.voice is None:
            async with ctx.typing():
                embed = discord.Embed(
                    title="Error",
                    description=ctx.author.mention + ", you are not connected to a voice channel",
                    colour=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="join request from " + ctx.author.name)
            await ctx.send(reference=ctx.message, embed=embed)
            return False
        self.add_guild(ctx)

        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()
            return True
        else:
            if (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()) and (ctx.voice_client.channel != ctx.author.voice.channel):
                async with ctx.typing():
                    embed = discord.Embed(
                        title="Error",
                        description=''.join(
                            "Can't move b/w channels while playing music!\n**NOTE: **You can still add music to the queue!"),
                        colour=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    embed.set_footer(
                        text="join request from " + ctx.author.name)
                await ctx.send(reference=ctx.message, embed=embed)
                return True
            else:
                await ctx.voice_client.move_to(ctx.author.voice.channel)
                return True
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="leave", aliases=["disconnect", "dc"], description="leaves if connected to any voice channel")
    async def leave(self, ctx):
        if ctx.voice_client is None:
            embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
        else:
            self.remove_guild(ctx)
            await ctx.voice_client.disconnect()
    # ----------------------------------------------------------------------------------------------------------------------

    async def play_music_from_player(self, ctx, *, player, data):
        if player is None:
            return
        self.properties[str(ctx.guild.id)]["currently_playing_player"] = player
        async with ctx.typing():
            # Embed
            embed = discord.Embed(
                title="Now Playing",
                description="- requested by " +
                self.music_queue[str(ctx.guild.id)
                                 ][self.properties[str(ctx.guild.id)]["current"]][1].author.mention,
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=self.MUSIC_ICON)
            embed.set_author(name=player.title, url="https://www.youtube.com/watch?v=" + data['id'],
                             icon_url=ctx.author.avatar.url)
            embed.add_field(name="Title", value=player.title, inline=False)
            embed.add_field(name="Position in queue",
                            value=self.properties[str(ctx.guild.id)]["current"]+1, inline=False)
            embed.add_field(name="Volume", value=str(
                int(self.properties[str(ctx.guild.id)]["vol"] * 100)) + "%", inline=False)
        await ctx.send(reference=ctx.message, embed=embed)
        ctx.voice_client.play(player, after=lambda e: print(
            f'Player error: {e}') if e else None)
        ctx.voice_client.source.volume = self.properties[str(
            ctx.guild.id)]["vol"]
    # ----------------------------------------------------------------------------------------------------------------------

    async def keep_playing(self, ctx):
        self.properties[str(ctx.guild.id)]["inside_keep_playing"] = True
        bool_flag = len(self.music_queue[str(
            ctx.guild.id)]) - self.properties[str(ctx.guild.id)]["current"] > 1
        bool_flag = (bool_flag or (self.properties[str(ctx.guild.id)]["loop_queue"])) and len(
            self.music_queue[str(ctx.guild.id)]) > 0
        if bool_flag and self.properties[str(ctx.guild.id)]["repeat_song"]:
            if self.properties[str(ctx.guild.id)]["current"] == -1:
                self.properties[str(ctx.guild.id)]["current"] = 0
        while bool_flag:
            if ((not ctx.voice_client.is_playing()) and (not ctx.voice_client.is_paused())):
                self.properties[str(ctx.guild.id)]["is_playing"] = True
                if (not self.properties[str(ctx.guild.id)]["repeat_song"]):
                    self.properties[str(ctx.guild.id)]["current"] += 1
                self.properties[str(ctx.guild.id)]["current"] %= len(
                    self.music_queue[str(ctx.guild.id)])
                player_and_data = await YTDLSource.from_url(self.music_queue[str(ctx.guild.id)][self.properties[str(ctx.guild.id)]["current"]][2], loop=self.bot.loop, stream=self.music_queue[str(ctx.guild.id)][self.properties[str(ctx.guild.id)]["current"]][3])
                player = player_and_data[0]
                data = player_and_data[1]
                self.music_queue[str(ctx.guild.id)][self.properties[str(
                    ctx.guild.id)]["current"]][0] = player
                await self.play_music_from_player(self.music_queue[str(ctx.guild.id)][self.properties[str(ctx.guild.id)]["current"]][1], player=player, data=data)
            await asyncio.sleep(1)
            bool_flag = len(self.music_queue[str(
                ctx.guild.id)]) - self.properties[str(ctx.guild.id)]["current"] > 1
            bool_flag = (bool_flag or (self.properties[str(ctx.guild.id)]["loop_queue"])) and len(
                self.music_queue[str(ctx.guild.id)]) > 0
        self.properties[str(ctx.guild.id)]["inside_keep_playing"] = False
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="play", aliases=["stream", "p", "add"], description="streams a song directly from youtube")
    async def play(self, ctx, *, url: Optional[str]):
        self.add_guild(ctx)
        if (url is None) and (ctx.message.content[(len(ctx.message.content)-3):(len(ctx.message.content))] != "add"):
            if ctx.voice_client is None:
                await self.join(ctx)
            if ctx.voice_client is None:
                return
            if ctx.voice_client.is_playing():
                return
            if ctx.voice_client.is_paused():
                ctx.voice_client.resume()
                if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
                    await self.keep_playing(ctx)
            elif len(self.music_queue[str(ctx.guild.id)]) > 0:
                if not ctx.voice_client.is_playing():
                    if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
                        await self.keep_playing(ctx)
            else:
                await ctx.send(reference=ctx.message, embed=self.embed_error_empty_queue)
            return
        elif url is None:
            async with ctx.typing():
                embed = discord.Embed(
                    title="Status",
                    colour=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                n = "Error"
                v = "Missing required arguements"
                embed.add_field(name=n, value=v, inline=False)
            await ctx.send(reference=ctx.message, embed=embed)
            return

        joined = await self.join(ctx)
        if joined == False:
            return
        player_and_data = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        player = player_and_data[0]
        data = player_and_data[1]
        if player is None:
            async with ctx.typing():
                embed = discord.Embed(
                    title="Error",
                    description=''.join(self.bad_request_error_message),
                    colour=discord.Color.blue(),
                    timestamp=datetime.utcnow(),
                )
            await ctx.send(reference=ctx.message, embed=embed)
            return
        self.music_queue[str(ctx.guild.id)].append([player, ctx, url, True])
        self.properties[str(ctx.guild.id)]["queued"] += 1
        async with ctx.typing():
            embed = discord.Embed(
                title="Added to queue",
                description="\"" + url + "\" requested by " + ctx.author.mention,
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow(),
            )
            embed.set_thumbnail(url=self.MUSIC_ICON)
            embed.set_author(name=player.title, url="https://www.youtube.com/watch?v=" + data['id'],
                             icon_url=ctx.author.avatar.url)
            embed.add_field(name="Title", value=player.title, inline=False)
            embed.add_field(name="Queue Position", value=len(
                self.music_queue[str(ctx.guild.id)]), inline=True)
        await ctx.send(reference=ctx.message, embed=embed)
        if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
            await self.keep_playing(ctx)
        return
    # ----------------------------------------------------------------------------------------------------------------------

#   @commands.command(name="playm", aliases=["streamm", "pm", "addm"], description="plays multiple songs (seperated by semicolons ';')")
#   async def playm(self, ctx, *, args):
#       self.add_guild(ctx)
#       urls = args.split(';')
#       joined = await self.join(ctx)
#       if joined == False:
#           return
#       last_url = urls.pop()
#       for url in urls:
#           url = url.strip()
#           player_and_data = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
#           player = player_and_data[0]
#           data = player_and_data[1]
#           if player is None:
#               async with ctx.typing():
#                   embed = discord.Embed(
#                       title="Error",
#                       description=''.join(self.bad_request_error_message),
#                       colour=discord.Color.blue(),
#                       timestamp=datetime.utcnow(),
#                   )
#               await ctx.send(reference=ctx.message, embed=embed)
#               continue
#           self.music_queue[str(ctx.guild.id)].append(
#               [player, ctx, url, True])
#           self.properties[str(ctx.guild.id)]["queued"] += 1
#           async with ctx.typing():
#               embed = discord.Embed(
#                   title="Added to queue",
#                   description="\"" + url + "\" requested by " + ctx.author.mention,
#                   colour=discord.Color.blue(),
#                   timestamp=datetime.utcnow(),
#               )
#               embed.set_thumbnail(url=self.MUSIC_ICON)
#               embed.set_author(name=player.title, url="https://www.youtube.com/watch?v=" + data['id'],
#                                icon_url=ctx.author.avatar.url)
#               embed.add_field(name="Title", value=player.title, inline=False)
#               embed.add_field(name="Queue Position", value=len(
#                   self.music_queue[str(ctx.guild.id)]), inline=True)
#           await ctx.send(reference=ctx.message, embed=embed)
#       await self.play(ctx, url=last_url)
#       return
#   # ----------------------------------------------------------------------------------------------------------------------
#
#   @commands.command(name='dplay', description="downloads a song and then queues it to reduce any possible lags")
#   async def dplay(self, ctx, *, url):
#       self.add_guild(ctx)
#       joined = await self.join(ctx)
#       if joined == False:
#           return
#       player_and_data = await YTDLSource.from_url(url, loop=self.bot.loop)
#       player = player_and_data[0]
#       data = player_and_data[1]
#       if player is None:
#           async with ctx.typing():
#               embed = discord.Embed(
#                   title="Error",
#                   description=''.join(self.bad_request_error_message),
#                   colour=0xff0000,
#                   timestamp=datetime.utcnow()
#               )
#           await ctx.send(reference=ctx.message, embed=embed)
#           return
#       self.music_queue[str(ctx.guild.id)].append([player, ctx, url, False])
#       self.properties[str(ctx.guild.id)]["queued"] += 1
#       async with ctx.typing():
#           embed = discord.Embed(
#               title="Downloaded & Added to queue",
#               description="\"" + url + "\" requested by " + ctx.author.mention,
#               colour=discord.Color.blue(),
#               timestamp=datetime.utcnow(),
#           )
#           embed.set_thumbnail(url=self.MUSIC_ICON)
#           embed.set_author(name=player.title, url="https://www.youtube.com/watch?v=" + data['id'],
#                            icon_url=ctx.author.avatar.url)
#           embed.add_field(name="Title", value=player.title, inline=False)
#           embed.add_field(name="Queue Position", value=len(
#               self.music_queue[str(ctx.guild.id)]), inline=True)
#       await ctx.send(reference=ctx.message, embed=embed)
#       if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
#           await self.keep_playing(ctx)
#       return
#   # ----------------------------------------------------------------------------------------------------------------------
#
#   @commands.command(name='dplaym', description="dplays multiple songs (seperated by semicolons ';')")
#   async def dplaym(self, ctx, *, args):
#       self.add_guild(ctx)
#       urls = args.split(';')
#       joined = await self.join(ctx)
#       if joined == False:
#           return
#       last_url = urls.pop()
#       for url in urls:
#           url = url.strip()
#           player_and_data = await YTDLSource.from_url(url, loop=self.bot.loop)
#           player = player_and_data[0]
#           data = player_and_data[1]
#           if player is None:
#               async with ctx.typing():
#                   embed = discord.Embed(
#                       title="Error",
#                       description=''.join(self.bad_request_error_message),
#                       colour=0xff0000,
#                       timestamp=datetime.utcnow()
#                   )
#               await ctx.send(reference=ctx.message, embed=embed)
#               continue
#           self.music_queue[str(ctx.guild.id)].append(
#               [player, ctx, url, False])
#           self.properties[str(ctx.guild.id)]["queued"] += 1
#           async with ctx.typing():
#               embed = discord.Embed(
#                   title="Downloaded & Added to queue",
#                   description="\"" + url + "\" requested by " + ctx.author.mention,
#                   colour=discord.Color.blue(),
#                   timestamp=datetime.utcnow(),
#               )
#               embed.set_thumbnail(url=self.MUSIC_ICON)
#               embed.set_author(name=player.title, url="https://www.youtube.com/watch?v=" + data['id'],
#                                icon_url=ctx.author.avatar.url)
#               embed.add_field(name="Title", value=player.title, inline=False)
#               embed.add_field(name="Queue Position", value=len(
#                   self.music_queue[str(ctx.guild.id)]), inline=True)
#               # embed.set_image(url="https://img.youtube.com/vi/" + player + "/0.jpg")
#               # embed.set_image(url=data[])
#           await ctx.send(reference=ctx.message, embed=embed)
#       await self.dplay(ctx, url=last_url)
#       return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name='loop', description="toggles looping of the queue")
    async def loop(self, ctx, loop_switch: Optional[str]):

        self.add_guild(ctx)

        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return

        if loop_switch is None:
            self.properties[str(ctx.guild.id)]["loop_queue"] = not self.properties[str(
                ctx.guild.id)]["loop_queue"]
            if self.properties[str(ctx.guild.id)]["loop_queue"]:
                loop_switch = "on"
            else:
                loop_switch = "off"
        elif loop_switch.lower() == "on":
            self.properties[str(ctx.guild.id)]["loop_queue"] = True
        elif loop_switch.lower() == "off":
            self.properties[str(ctx.guild.id)]["loop_queue"] = False
        else:
            async with ctx.typing():
                embed = discord.Embed(
                    title="Status",
                    colour=0xff0000,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(
                    name="Error",
                    value="Invalid value provided",
                    inline=True
                )
            await ctx.send(reference=ctx.message, embed=embed)
            return
        async with ctx.typing():
            embed = discord.Embed(
                title="Status",
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Done",
                value="Queue looping is now " + loop_switch.lower(),
                inline=True
            )
        await ctx.send(reference=ctx.message, embed=embed)
        if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
            await self.keep_playing(ctx)
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name='repeat', description="toggles repeating of the currently playing song")
    async def repeat(self, ctx, repeat_switch: Optional[str]):

        self.add_guild(ctx)

        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return

        if repeat_switch is None:
            self.properties[str(ctx.guild.id)]["repeat_song"] = not self.properties[str(
                ctx.guild.id)]["repeat_song"]
            if self.properties[str(ctx.guild.id)]["repeat_song"]:
                repeat_switch = "on"
            else:
                repeat_switch = "off"
        elif repeat_switch.lower() == "on":
            self.properties[str(ctx.guild.id)]["repeat_song"] = True
        elif repeat_switch.lower() == "off":
            self.properties[str(ctx.guild.id)]["repeat_song"] = False
        else:
            async with ctx.typing():
                embed = discord.Embed(
                    title="Status",
                    colour=0xff0000,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(
                    name="Error",
                    value="Invalid value provided",
                    inline=True
                )
            await ctx.send(reference=ctx.message, embed=embed)
            return
        async with ctx.typing():
            embed = discord.Embed(
                title="Status",
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Done",
                value="Song repeat is now " + repeat_switch.lower(),
                inline=True
            )
        await ctx.send(reference=ctx.message, embed=embed)
        if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
            await self.keep_playing(ctx)
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name='restart', description="restarts the currently playing song")
    async def restart(self, ctx):
        self.add_guild(ctx)
        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return
        self.properties[str(ctx.guild.id)]["current"] -= (
            1 if not self.properties[str(ctx.guild.id)]["repeat_song"] else 0)
        ctx.voice_client.stop()
        if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
            await self.keep_playing(ctx)
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="queue", aliases=["view"], description="displays the current queue")
    async def queue(self, ctx, *, url: Optional[str]):

        self.add_guild(ctx)

        if url is not None:
            if url != "":
                await self.play(ctx, url=url)
                return

        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return

        if len(self.music_queue[str(ctx.guild.id)]) == 0:
            await ctx.send(reference=ctx.message, embed=self.embed_error_empty_queue)
            return
        embed = discord.Embed(
            title="Queue",
            colour=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=self.MUSIC_ICON)
        embed.set_author(name="Dex", icon_url=self.bot.user.avatar.url)
        size = len(self.music_queue[str(ctx.guild.id)])
        for i in range(0, size, 25):
            embed = discord.Embed(
                title="Queue",
                description=str("Page " + str(i // 25 + 1) +
                                " of " + str(size // 25 + 1)),
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=self.MUSIC_ICON)
            embed.set_author(name="Dex", icon_url=self.bot.user.avatar.url)
            for j in range(i, min(size, i + 25)):
                k = "**" if j == self.properties[str(
                    ctx.guild.id)]["current"] else ""
                embed.add_field(
                    name=str(
                        j + 1) + (" ***(Currently Playing)***" if j == self.properties[str(ctx.guild.id)]["current"] else ""),
                    value=k +
                    str(self.music_queue[str(ctx.guild.id)][j][0].title)+k,
                    inline=False
                )
            async with ctx.typing():
                embed.set_footer(
                    text="Page " + str(int(i / 25) + 1) + " of " + str(int(size / 25) + 1))
            await ctx.send(reference=ctx.message, embed=embed)
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="remove", description="removes a song from the queue, takes song position as argument")
    async def remove(self, ctx, pos):
        self.add_guild(ctx)
        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return
        if (pos is None):
            async with ctx.typing():
                embed = discord.Embed(
                    title="Error",
                    description=''.join(
                        "Missing required argument: `<position>`"),
                    colour=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
            await ctx.send(reference=ctx.message, embed=embed)
            return
        if (len(self.music_queue[str(ctx.guild.id)]) == 0):
            await ctx.send(reference=ctx.message, embed=self.embed_error_empty_queue)
            return
        if (1 > int(pos)) or (len(self.music_queue[str(ctx.guild.id)]) < int(pos)):
            async with ctx.typing():
                embed = discord.Embed(
                    title="Error",
                    description=str("Queue Position must be between (1 & " +
                                    str(len(self.music_queue[str(ctx.guild.id)]))+")"),
                    colour=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
            await ctx.send(reference=ctx.message, embed=embed)
            return
        pos = int(pos) - 1
        async with ctx.typing():
            embed = discord.Embed(
                title="Removed from queue",
                description="track requested by " +
                self.music_queue[str(ctx.guild.id)][int(pos)
                                                    ][1].author.mention,
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            player = self.music_queue[str(ctx.guild.id)][int(pos)][0]
            embed.set_thumbnail(url=self.MUSIC_ICON)
            embed.set_author(name=player.title,
                             icon_url=ctx.author.avatar.url)
            embed.add_field(name="Title", value=player.title, inline=False)
            embed.add_field(name="Remove request by",
                            value=ctx.author.mention, inline=True)
        self.music_queue[str(ctx.guild.id)].pop(int(pos))
        if self.properties[str(ctx.guild.id)]["current"] > pos:
            self.properties[str(ctx.guild.id)]["current"] -= 1
        elif self.properties[str(ctx.guild.id)]["current"] == pos:
            self.properties[str(ctx.guild.id)]["repeat_song"] = False
            self.properties[str(ctx.guild.id)]["current"] -= 1
            ctx.voice_client.stop()
        if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
            await self.keep_playing(ctx)
        await ctx.send(reference=ctx.message, embed=embed)
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="jump", aliases=["jumpto"], description="jumps to a song in the queue, takes song position as argument")
    async def jump(self, ctx, pos):
        self.add_guild(ctx)
        pos = int(pos)
        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return
        if (pos is None):
            async with ctx.typing():
                embed = discord.Embed(
                    title="Error",
                    description=''.join(
                        "Missing required argument: `<position>`"),
                    colour=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
            await ctx.send(reference=ctx.message, embed=embed)
            return
        if (len(self.music_queue[str(ctx.guild.id)]) == 0):
            await ctx.send(reference=ctx.message, embed=self.embed_error_empty_queue)
            return
        if (1 > int(pos)) or (len(self.music_queue[str(ctx.guild.id)]) < int(pos)):
            async with ctx.typing():
                embed = discord.Embed(
                    title="Error",
                    description=str(
                        "Queue Position must be between (1 & "+str(len(self.music_queue[str(ctx.guild.id)]))+")"),
                    colour=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
            await ctx.send(reference=ctx.message, embed=embed)
            return
        pos = int(pos) - 1
        async with ctx.typing():
            embed = discord.Embed(
                title="Jumping to " + str(pos + 1),
                description="- requested by " + ctx.author.mention,
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            player = self.music_queue[str(ctx.guild.id)][int(pos)][0]
            embed.set_thumbnail(url=self.MUSIC_ICON)
            embed.set_author(name=player.title,
                             icon_url=ctx.author.avatar.url)
            embed.add_field(name="Title", value=player.title, inline=False)
            embed.add_field(
                name="Queue Looping", value="On" if self.properties[str(ctx.guild.id)]["loop_queue"] else "Off", inline=True)
        await ctx.send(reference=ctx.message, embed=embed)
        self.properties[str(ctx.guild.id)]["repeat_song"] = False
        self.properties[str(ctx.guild.id)]["current"] = pos - 1
        ctx.voice_client.stop()
        if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
            await self.keep_playing(ctx)
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="volume", aliases=["vol"], description="changes the volume of the music player")
    async def volume(self, ctx, volume: int):
        self.add_guild(ctx)
        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return
        ctx.voice_client.source.volume = volume / 100
        self.properties[str(ctx.guild.id)]["vol"] = volume / 100
        async with ctx.typing():
            embed = discord.Embed(
                title=str(volume) + "%",
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name="Volume set to",
                             icon_url=ctx.author.avatar.url)
        await ctx.send(reference=ctx.message, embed=embed)
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="stop", aliases=["stfu", "shut"], description="stops the music player and clears the queue")
    async def stop(self, ctx):
        self.add_guild(ctx)
        self.properties[str(ctx.guild.id)]["current"] = -1
        self.properties[str(ctx.guild.id)]["queued"] = 0
        self.properties[str(ctx.guild.id)]["vol"] = 1
        self.properties[str(ctx.guild.id)]["loop_queue"] = False
        self.properties[str(ctx.guild.id)]["repeat_song"] = False
        self.properties[str(ctx.guild.id)]["currently_playing_player"] = None
        self.properties[str(ctx.guild.id)]["inside_keep_playing"] = False
        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            self.music_queue[str(ctx.guild.id)].clear()
            ctx.voice_client.stop()
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="pause", description="pauses the music player")
    async def pause(self, ctx):
        self.add_guild(ctx)
        if ctx.voice_client is None:
            embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
        elif ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="resume", description="resumes the music player")
    async def resume(self, ctx):
        self.add_guild(ctx)
        if ctx.voice_client is None:
            embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
        elif ctx.voice_client.is_paused():
            ctx.voice_client.resume()
        elif not ctx.voice_client.is_playing():
            if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
                await self.keep_playing(ctx)
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="skip", aliases=["sk"], description="plays the next song in the queue")
    async def skip(self, ctx):
        self.add_guild(ctx)
        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            if (self.properties[str(ctx.guild.id)]["current"] < len(self.music_queue[str(ctx.guild.id)]) - 1) or self.properties[str(ctx.guild.id)]["loop_queue"]:
                self.properties[str(ctx.guild.id)]["current"] += 0
                self.properties[str(ctx.guild.id)]["repeat_song"] = False
                ctx.voice_client.stop()
                if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
                    await self.keep_playing(ctx)
            else:
                async with ctx.typing():
                    embed = discord.Embed(
                        title="Error",
                        description="Nothing to play after this",
                        colour=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                await ctx.send(reference=ctx.message, embed=embed)
        return
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name="previous", aliases=["prev"], description="plays the previous song in the queue")
    async def previous(self, ctx):
        self.add_guild(ctx)
        if ctx.voice_client is None:
            async with ctx.typing():
                embed = self.embed_error_no_vc_dex
            await ctx.send(reference=ctx.message, embed=embed)
            return
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            if self.properties[str(ctx.guild.id)]["current"] > 0 or self.properties[str(ctx.guild.id)]["loop_queue"]:
                self.properties[str(ctx.guild.id)]["current"] -= 2
                self.properties[str(ctx.guild.id)]["repeat_song"] = False
                ctx.voice_client.stop()
                if not self.properties[str(ctx.guild.id)]["inside_keep_playing"]:
                    await self.keep_playing(ctx)
            else:
                async with ctx.typing():
                    embed = discord.Embed(
                        title="Error",
                        description="Nothing to play before this",
                        colour=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                await ctx.send(reference=ctx.message, embed=embed)
        return
    # ----------------------------------------------------------------------------------------------------------------------
'''
    async def get_lyrics(self, song_title):
        API_URL = "https://some-random-api.ml/lyrics?title=" + song_title
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL) as response:
                data_json = await response.json()
                return data_json
    # ----------------------------------------------------------------------------------------------------------------------

    @commands.command(name='lyrics', description='sends the lyrics of the song')
    async def lyrics(self, ctx, *args) -> None:
        self.add_guild(ctx)
        song_title = ''
        for arg in args:
            song_title += arg+'%20'
        if len(song_title) > 0:
            song_title = song_title[:-3]
        else:
            if self.properties[str(ctx.guild.id)]["currently_playing_player"] is None:
                async with ctx.typing():
                    embed = discord.Embed(
                        title="Error",
                        description="No song is currently playing",
                        color=0xff0000,
                        timestamp=datetime.utcnow(),
                    )
                await ctx.send(reference=ctx.message, embed=embed)
                return
            args = self.properties[str(
                ctx.guild.id)]["currently_playing_player"].title.split()
            for arg in args:
                song_title += arg+'%20'
            song_title = song_title[:-3]

        data = await self.get_lyrics(song_title)
        if not 'lyrics' in data.keys():
            err_mssg = data['error']
            embed = discord.Embed(
                title="Error",
                description=err_mssg +
                ('\n'+'[see results from GoogleSearch](https://www.google.com/search?q='+song_title+'+lyrics)'),
                colour=discord.Color.blue(),
                timestamp=datetime.utcnow(),
            )
            await ctx.send(reference=ctx.message, embed=embed)
        else:
            async with ctx.typing():
                lyrics = data['lyrics']
                extend_text = '[see results from GoogleSearch](https://www.google.com/search?q=' + data['author'].strip().replace(' ', '+') + '+' + \
                    song_title+'+lyrics)'
                if len(lyrics) > 3500:
                    lyrics = lyrics[:3500]+'... '
                    extend_text = '[read more](https://www.google.com/search?q=' + data['author'].strip().replace(' ', '+') + '+' + \
                        song_title+'+lyrics)'

                embed = discord.Embed(
                    title=data['title'],
                    description=lyrics+extend_text,
                    color=0x00ff00,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(
                    name=data['author'],
                )
                embed.set_thumbnail(url=data['thumbnail']['genius'])
                embed.set_footer(
                    icon_url=ctx.author.avatar.url,
                )
            await ctx.send(reference=ctx.message, embed=embed)
    # ----------------------------------------------------------------------------------------------------------------------
'''
async def setup(bot):
    await bot.add_cog(Music(bot))
