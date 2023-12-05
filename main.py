import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_PREFIX = os.getenv('BOT_PREFIX')

def run():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix = BOT_PREFIX, intents = intents)

    @bot.event
    async def on_ready():
        print(f'User: {bot.user} [ID: {bot.user.id}]')

    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')

    bot.run(BOT_TOKEN)

if __name__ == '__main__':
    run()