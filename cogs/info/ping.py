from discord.ext import commands

class Ping(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
	
	@commands.command(name = 'ping', description = 'Pong! Shows the ping between the bot and discord.')
	async def ping(self, ctx):
		await ctx.send('🏓 Pong! My ping is: {0}'.format(round(self.bot.latency * 1000)))

async def setup(bot):
	await bot.add_cog(Ping(bot))