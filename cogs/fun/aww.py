from discord.ext import commands
import discord
import aiohttp
import random

class Aww(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name = 'aww', description = 'Gives you a random cute image from reddit. Subreddit: r/aww')
    async def aww(self, ctx):
        embed = discord.Embed(title="", description="", color= discord.Color.blue())

        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://www.reddit.com/r/aww/new.json?sort=hot') as r:
                res = await r.json()
                embed.set_image(url=res['data']['children'] [random.randint(0, 25)]['data']['url'])
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Aww(bot))