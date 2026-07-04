import subprocess
import signal
import sys
import time
import requests
import webbrowser
import os

def create_upload_directories():
    """Create necessary upload directories"""
    upload_dirs = [
        'uploads',
        'uploads/photos',
        'uploads/videos', 
        'uploads/documents', 
        'uploads/audio', 
        'uploads/other'
    ]
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)

# Create upload directories
create_upload_directories()

# Start app.py
app_process = subprocess.Popen(['python', 'app.py'])
# app_process = subprocess.Popen(['python', 'faaalerts.py'])

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

try:
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        print(f"ngrok URL: {ngrok_url}")
        webbrowser.open(ngrok_url)
        with open('ngrok_url.txt', 'w') as f:
            f.write(ngrok_url)
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