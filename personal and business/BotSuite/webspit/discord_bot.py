import discord
from discord.ext import commands
import os

TOKEN = 'MTM1MDMxNjYyMjg2MjA5NDM2Nw.GeTOx0.csGfV1bEVMu4GkPmzEwjN8hnfxAJtjgGfftU8E'
CHANNEL_ID = 1350288167982338148

intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        with open('ngrok_url.txt', 'r') as f:
            ngrok_url = f.read().strip()
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(f'Service Online! Active URL: {ngrok_url}')
            else:
                print(f"Channel with ID {CHANNEL_ID} not found.")
    except Exception as e:
        print(f"Error reading ngrok URL: {e}")

@bot.command(name='current-url')
async def current_url(ctx):
    try:
        with open('ngrok_url.txt', 'r') as f:
            ngrok_url = f.read().strip()
            await ctx.send(f'Current Active URL: {ngrok_url}')
    except Exception as e:
        await ctx.send(f"Error reading ngrok URL: {e}")

bot.run(TOKEN)