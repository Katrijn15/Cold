import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_PREFIX = os.getenv('BOT_PREFIX')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix = BOT_PREFIX, intents = intents)

async def main():

    @bot.event
    async def on_ready():
        print(f'User: {bot.user} [ID: {bot.user.id}]')
        bot.remove_command('help')

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"Loaded Cog: {filename[:-3]}")

asyncio.run(main())
bot.run(BOT_TOKEN)