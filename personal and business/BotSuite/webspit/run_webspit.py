import subprocess
import signal
import sys
import time
import requests
import webbrowser
import psutil

def terminate_existing_processes(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            proc.terminate()
            proc.wait()

# Terminate any existing instances of the Flask app and ngrok
terminate_existing_processes('python.exe')
terminate_existing_processes('ngrok.exe')

# Start the Flask app
app_process = subprocess.Popen(['python', 'webspit/app.py'])

# Wait for the app to start
time.sleep(5)

# Start ngrok with host-header option to skip the warning
ngrok_process = subprocess.Popen(['ngrok', 'http', 'http://127.0.0.1:5002'])

def get_ngrok_url():
    time.sleep(2)  # Wait for ngrok to initialize
    try:
        headers = {'ngrok-skip-browser-warning': 'true'}
        response = requests.get('http://127.0.0.1:4040/api/tunnels', headers=headers)
        data = response.json()
        return data['tunnels'][0]['public_url']
    except Exception as e:
        print(f"Error fetching ngrok URL: {e}")
        return None

def terminate_processes():
    app_process.terminate()
    ngrok_process.terminate()
    if 'discord_bot_process' in globals():
        discord_bot_process.terminate()

try:
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        print(f"Service Online! Active URL: {ngrok_url}")
        # webbrowser.open(ngrok_url)  # Commented out to prevent opening the webpage
        with open('ngrok_url.txt', 'w') as f:
            f.write(ngrok_url)
        
        # Start the Discord bot
        discord_bot_process = subprocess.Popen(['python', 'webspit/discord_bot.py'])
    else:
        print("Failed to retrieve ngrok URL")

    # Wait for all processes to complete
    app_process.wait()
    ngrok_process.wait()
    
except KeyboardInterrupt:
    print("Terminating processes...")
    terminate_processes()
finally:
    terminate_processes()
    sys.exit(0)