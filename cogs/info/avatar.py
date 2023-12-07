from discord.ext import commands
import discord

class Avatar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name = 'Avatar', aliases = ['a', 'av', 'ava', 'avatar'], description = 'Show a mentioned person\'s avatar.')
    async def avatar(self, ctx, *, avamember: discord.Member = None):
        if avamember == None:
                embed = discord.Embed(description='❌ Error! Please specify a user',
                                    color=discord.Color.red())
                await ctx.reply(embed=embed, mention_author=False)

        else:
            userAvatarUrl = avamember.avatar.url
            embed = discord.Embed(title=('{}\'s Avatar'.format(avamember.name)), colour=discord.Color.blue())
            embed.set_image(url='{}'.format(userAvatarUrl))
            await ctx.reply(embed=embed, mention_author=False) 

async def setup(bot):
    await bot.add_cog(Avatar(bot))