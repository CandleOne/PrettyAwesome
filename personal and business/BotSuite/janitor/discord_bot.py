import discord
import os
import requests
import pyshorteners
import asyncio

TOKEN = 'MTM1MDMxODA5Mjc0NzgwNDY4Mg.GbXuD5.1wLrK9E0OrGOJL_JST5AGdyesHz_LnhtvCz-S0'
CHANNEL_ID = 1350288167982338148  # Replace with your channel ID

intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ngrok_url = None
        self.short_url = None

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content == '/clear-chat':
            async for msg in message.channel.history(limit=100):
                if msg.author == self.user:
                    await msg.delete()

        if message.content.startswith('/nuke'):
            await message.channel.send('Please enter the admin password:')
            def check(m):
                return m.author == message.author and m.channel == message.channel

            try:
                response = await self.wait_for('message', check=check, timeout=30.0)
                if response.content == '1234':  # Replace with your actual admin password
                    async for msg in message.channel.history(limit=100):
                        await msg.delete()
                else:
                    await message.channel.send('Incorrect password. Nuke command aborted.')
            except asyncio.TimeoutError:
                await message.channel.send('Password prompt timed out. Nuke command aborted.')

client = MyClient(intents=intents)
client.run(TOKEN)