from discord.ext import commands
import discord
import aiohttp
import random

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name = 'meme', description = 'Gives you a random meme from reddit. Subreddit: r/dankmemes')
    async def meme(self, ctx):
        embed = discord.Embed(title="", description="", color= discord.Color.blue())

        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://www.reddit.com/r/dankmemes/new.json?sort=hot') as r:
                res = await r.json()
                embed.set_image(url=res['data']['children'] [random.randint(0, 25)]['data']['url'])
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Meme(bot))