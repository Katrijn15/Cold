from discord.ext import commands
import discord
import aiohttp
import random
import redditeasy
import datetime

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name = 'meme', description = 'Gives you a random meme from reddit. Subreddit: r/dankmemes')
    async def meme(self, ctx):
        post = redditeasy.Subreddit()
        postoutput = post.get_post(subreddit="meme")
        formatted_time = datetime.datetime.fromtimestamp(postoutput.created_at).strftime("%d/%m/%Y %I:%M:%S UTC")
        embed = discord.Embed(title = postoutput.title, description = postoutput.subreddit_name, color = discord.Color.blue())
        embed.set_image(url = postoutput.content)
        await ctx.send(embed = embed)

async def setup(bot):
    await bot.add_cog(Meme(bot))