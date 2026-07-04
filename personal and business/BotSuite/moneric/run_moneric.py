import subprocess
import time
import psutil
import os  # Add os import for directory operations

def terminate_existing_processes(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            try:
                proc.terminate()
                proc.wait()
            except psutil.NoSuchProcess:
                pass  # Process already terminated

# Terminate any existing instances of the Flask app and ngrok
terminate_existing_processes('python.exe')
terminate_existing_processes('ngrok.exe') 

# Create necessary directories
def create_required_directories():
    directories = [
        'c:\\Users\\jacob\\Desktop\\murp'
    ]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

# Create directories before running scripts
create_required_directories()

# Function to check if a process is already running
def is_process_running(script_name):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        # Check if cmdline is not None
        if proc.info['cmdline'] and script_name in proc.info['cmdline']:
            return True
    return False

# Define the commands to run the scripts
commands = [
    "python moneric/discbot.py",
    "python moneric/log_stats.py",
    "start /min cmd /c python moneric/moneroqr.py"
]

# Filter out any None or invalid commands
valid_commands = [command for command in commands if isinstance(command, str) and command.strip()]

# Use subprocess to run the commands concurrently if not already running
processes = []
for command in valid_commands:
    script_name = command.split()[-1]
    if not is_process_running(script_name):
        processes.append(subprocess.Popen(command, shell=True))

# Wait for all processes to complete
for process in processes:
    process.wait()

if __name__ == "__main__":
    # Ensure directories exist
    create_required_directories()
    
    script_name = "discbot.py"
    if not is_process_running(script_name):
        subprocess.Popen("python moneric/discbot.py", shell=True)
    else:
        print(f"{script_name} is already running.")
