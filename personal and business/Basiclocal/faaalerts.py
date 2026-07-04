import discord
from discord.ext import commands, tasks
import os
import asyncio
import requests
from datetime import datetime

# Bot configuration
TOKEN = 'MTM1NzEwODc0NjQxMjg4NDE0OQ.G3vt5y.Idy2QRbfW0wx0ahQN1FSiKyHffvUdQgSilTHvU'  # Replace with your actual bot token
NGROK_URL_FILE = 'ngrok_url.txt'  # Path to the ngrok URL file
CHECK_INTERVAL = 60  # Seconds between URL checks

# Create bot instance with appropriate intents
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Store the current URL and users who should receive updates
current_url = None
subscribed_users = set()
service_online = False
last_status_change = None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    # Start the URL checking loop
    check_ngrok_url.start()
    # Start the service status checking loop
    check_service_status.start()

@bot.command()
async def subscribe(ctx):
    """Subscribe to receive ngrok URL updates via DM"""
    user_id = ctx.author.id
    subscribed_users.add(user_id)
   
    await ctx.send(f"You've been subscribed to receive ngrok URL updates via DM!")
   
    # If we already have a URL, send it immediately
    if current_url:
        user = bot.get_user(user_id)
        if user:
            try:
                status_text = "🟢 ONLINE" if service_online else "🔴 OFFLINE"
                await user.send(f"Current ngrok URL: {current_url}\nService status: {status_text}")
            except discord.Forbidden:
                print(f"Cannot send DM to user {user.name}#{user.discriminator}")

@bot.command()
async def unsubscribe(ctx):
    """Unsubscribe from ngrok URL updates"""
    user_id = ctx.author.id
    if user_id in subscribed_users:
        subscribed_users.remove(user_id)
        await ctx.send("You've been unsubscribed from ngrok URL updates.")
    else:
        await ctx.send("You weren't subscribed to updates.")

@bot.command()
async def geturl(ctx):
    """Get the current ngrok URL"""
    if current_url:
        status_text = "🟢 ONLINE" if service_online else "🔴 OFFLINE"
        uptime_text = ""
        if last_status_change:
            time_diff = datetime.now() - last_status_change
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_text = f"\nStatus duration: {hours}h {minutes}m {seconds}s"
            
        await ctx.send(f"Current ngrok URL: {current_url}\nService status: {status_text}{uptime_text}")
    else:
        await ctx.send("No ngrok URL is currently available.")

@bot.command()
async def status(ctx):
    """Check the current status of the file management service"""
    if current_url:
        status_text = "🟢 ONLINE" if service_online else "🔴 OFFLINE"
        
        uptime_text = ""
        if last_status_change:
            time_diff = datetime.now() - last_status_change
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_text = f"\nStatus duration: {hours}h {minutes}m {seconds}s"
            
        await ctx.send(f"Service status: {status_text}{uptime_text}")
    else:
        await ctx.send("No service is currently available.")

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_ngrok_url():
    """Check for updates to the ngrok URL file and notify subscribed users"""
    global current_url
   
    try:
        # Check if file exists
        if not os.path.exists(NGROK_URL_FILE):
            print(f"URL file not found: {NGROK_URL_FILE}")
            return
           
        # Read the URL file
        with open(NGROK_URL_FILE, 'r') as f:
            new_url = f.read().strip()
           
        # If URL has changed or is new, notify users
        if new_url and new_url != current_url:
            print(f"New URL detected: {new_url}")
            current_url = new_url
           
            # Notify all subscribed users
            for user_id in subscribed_users:
                user = bot.get_user(user_id)
                if user:
                    try:
                        await user.send(f"🔄 New ngrok URL available: {current_url}")
                    except discord.Forbidden:
                        print(f"Cannot send DM to user {user.name}#{user.discriminator}")
                else:
                    print(f"Could not find user with ID {user_id}")
                   
    except Exception as e:
        print(f"Error checking ngrok URL: {e}")

@tasks.loop(seconds=30)
async def check_service_status():
    """Check if the service is online and update bot status"""
    global service_online, last_status_change
    
    if not current_url:
        return
        
    try:
        # Try to connect to the service
        headers = {'ngrok-skip-browser-warning': 'true'}
        response = requests.get(current_url, headers=headers, timeout=5)
        new_status = response.status_code == 200
        
        # If status changed, update bot's presence and record time
        if new_status != service_online:
            service_online = new_status
            last_status_change = datetime.now()
            
            if service_online:
                await bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name="🟢 Service ONLINE"
                    ),
                    status=discord.Status.online
                )
                print("Service is now ONLINE")
                
                # Notify subscribed users about service coming online
                for user_id in subscribed_users:
                    user = bot.get_user(user_id)
                    if user:
                        try:
                            await user.send(f"🟢 Service is now ONLINE: {current_url}")
                        except discord.Forbidden:
                            pass
            else:
                await bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name="🔴 Service OFFLINE"
                    ),
                    status=discord.Status.dnd
                )
                print("Service is now OFFLINE")
                
                # Notify subscribed users about service going offline
                for user_id in subscribed_users:
                    user = bot.get_user(user_id)
                    if user:
                        try:
                            await user.send(f"🔴 Service is now OFFLINE")
                        except discord.Forbidden:
                            pass
                            
    except Exception as e:
        # If connection fails, mark service as offline
        if service_online:
            service_online = False
            last_status_change = datetime.now()
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="🔴 Service OFFLINE"
                ),
                status=discord.Status.dnd
            )
            print(f"Service is now OFFLINE (Error: {e})")
            
            # Notify subscribed users
            for user_id in subscribed_users:
                user = bot.get_user(user_id)
                if user:
                    try:
                        await user.send(f"🔴 Service is now OFFLINE")
                    except discord.Forbidden:
                        pass

@check_ngrok_url.before_loop
@check_service_status.before_loop
async def before_check():
    """Wait until the bot is ready before starting the loops"""
    await bot.wait_until_ready()

@bot.command()
async def admin_add_user(ctx, user_id: int):
    """Admin command to add a user to the subscription list"""
    # Check if the command issuer is an admin
    if ctx.author.id == 1247405348126720062:  # Your admin user ID
        subscribed_users.add(user_id)
        await ctx.send(f"User {user_id} has been added to subscription list.")
    else:
        await ctx.send("You don't have permission to use this command.")

# Run the bot
bot.run(TOKEN)