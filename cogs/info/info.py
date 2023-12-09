from discord.ext import commands
import discord

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name = 'info', description = 'Shows info about the bot.')
    async def info(self, ctx):
        guild = self.bot.guilds[0]

        embed = discord.Embed(title = 'Bot info page', color = discord.Color.blue())

        embed.add_field(name = 'Servers:', value = '')

        for guild in self.bot.guilds:
            embed.add_field(name = '', value = f'`{guild.name} | {len(guild.members)}`')

        embed.set_footer(text = f'Amount of servers: {len(self.bot.guilds)}')

        await ctx.send(embed = embed)

#           await ctx.send(f'Servers: {guild.name} | {len(guild.members)}')
#           await ctx.send(f'Amount of servers: {len(self.bot.guilds)}')

async def setup(bot):
    await bot.add_cog(Info(bot))