import subprocess
import signal
import sys
import time
import requests
import webbrowser

# Start imageserver.py
imageserver_process = subprocess.Popen(['python', 'moneric/imageserver.py'])

# Start moneroqr.py
moneroqr_process = subprocess.Popen(['python', 'moneroqr.py'])

# Start ngrok with host-header option to skip the warning
ngrok_process = subprocess.Popen(['ngrok', 'http', 'http://127.0.0.1:5000', '--host-header=127.0.0.1'])

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
    imageserver_process.terminate()
    moneroqr_process.terminate()
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
    imageserver_process.wait()
    moneroqr_process.wait()
    ngrok_process.wait()
except KeyboardInterrupt:
    print("Terminating processes...")
    terminate_processes()
finally:
    terminate_processes()
    sys.exit(0)