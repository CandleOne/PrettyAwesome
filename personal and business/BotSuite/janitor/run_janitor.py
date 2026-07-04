import subprocess
import signal
import sys
import time
import requests
import webbrowser

# Start the Discord bot
bot_process = subprocess.Popen(['python', 'janitor/discord_bot.py'])

def terminate_processes():
    bot_process.terminate()

try:
    # Wait for all processes to complete
    bot_process.wait()
except KeyboardInterrupt:
    print("Terminating processes...")
    terminate_processes()
finally:
    terminate_processes()
    sys.exit(0)