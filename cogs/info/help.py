import discord
from discord.ext import commands
from discord.errors import Forbidden
import os
from dotenv import load_dotenv

load_dotenv()

BOT_PREFIX = os.getenv('BOT_PREFIX')
OWNER_ID = os.getenv('OWNER_ID')
OWNER_NAME = os.getenv('OWNER_NAME')

async def send_embed(ctx, embed):

    try:
        await ctx.send(embed=embed)
    except Forbidden:
        try:
            await ctx.send('Hey, seems like I can\'t send embeds. Please check my permissions :)')
        except Forbidden:
            await ctx.author.send(
                f'Hey, seems like I can\'t send any message in {ctx.channel.name} on {ctx.guild.name}', embed=embed)


class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.owner_id = OWNER_ID
        self.owner_name = OWNER_NAME
        self.bot_prefix = BOT_PREFIX

    @commands.command(name = 'help', description = 'Shows all commands.')
    @commands.bot_has_permissions(add_reactions=True,embed_links=True)
    async def help(self, ctx, *input):
        prefix = self.bot_prefix
        version = '1'
        owner = self.owner_id
        owner_name = self.owner_name

    
        if not input:

            try:
                owner = ctx.guild.get_member(owner).mention

            except AttributeError as e:
                owner = owner

            # starting to build embed
            emb = discord.Embed(title='Commands and modules', color=discord.Color.blue(),
                                description=f'Use `{prefix}help <command>` to gain more information about that module.')

            # iterating trough cogs, gathering descriptions
            cogs_desc = ''
            for cog in self.bot.cogs:
                cogs_desc += f'`{cog}` {self.bot.cogs[cog].__doc__}\n'

            # adding 'list' of cogs to embed
            emb.add_field(name='Commands', value='')

            # integrating trough uncategorized commands
            commands_desc = ''
            for command in self.bot.walk_commands():
                commands_d = f'`{prefix}{command.name}` {command.description}'
                emb.add_field(name = '', value=commands_d, inline=False)
                # if cog not in a cog
                # listing command if cog name is None and command isn't hidden
                if not command.cog_name and not command.hidden:
                    commands_desc += f'{command.name} - {command.description}\n'

            # adding those commands to embed
            if commands_desc:
                emb.add_field(name='Not belonging to a module', value=commands_desc, inline=False)

            emb.set_footer(text=f'Bot is running v{version}')

        # block called when one cog-name is given
        # trying to find matching cog and it's commands
        elif len(input) == 1:

            # iterating trough cogs
            for cog in self.bot.cogs:
                # check if cog is the matching one
                if cog.lower() == input[0].lower():

                    # making title - getting description from doc-string below class
                    emb = discord.Embed(title=f'{cog} - Commands', description=self.bot.cogs[cog].__doc__,
                                        color=discord.Color.blue()())

                    # getting commands from cog
                    for command in self.bot.get_cog(cog).get_commands():
                        # if cog is not hidden
                        if not command.hidden:
                            emb.add_field(name=f'`{prefix}{command.name}`', value=command.description, inline=False)
                    # found cog - breaking loop
                    break

            # if input not found
            # yes, for-loops have an else statement, it's called when no 'break' was issued
            else:
                emb = discord.Embed(title='What\'s that?!',
                                    description='That category doesn\'t exist!',
                                    color=discord.Color.blue())

        # too many cogs requested - only one at a time allowed
        elif len(input) > 1:
            emb = discord.Embed(title='That\'s too much.',
                                description='Please request only one module at once.',
                                color=discord.Color.blue())

        else:
            emb = discord.Embed(title='It\'s a magical place.',
                                description='I don\'t know how you got here. But I didn\'t see this coming at all.\n',
                                color = discord.Color.blue())

        # sending reply embed using our own function defined above
        await send_embed(ctx, emb)


async def setup(bot):
    await bot.add_cog(Help(bot))