from discord.ext import commands

class Ping(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
	
	@commands.command(name = 'ping', description = 'Pong! Shows bot latency.')
	async def ping(self, ctx):
		await ctx.send('🏓 Pong! {0}'.format(round(self.bot.latency, 1)))

async def setup(bot):
	await bot.add_cog(Ping(bot))