import subprocess
import time
import tkinter as tk
from tkinter import messagebox

# List of Python scripts to run
python_scripts = [
    "moneric\\run_moneric.py",
    "webspit\\run_webspit.py",
    "janitor\\run_janitor.py",
]

processes = {}

def start_script(script):
    if script not in processes or processes[script].poll() is not None:
        processes[script] = subprocess.Popen(['cmd', '/k', 'python', script], creationflags=subprocess.CREATE_NEW_CONSOLE)
        update_status(script, "Running")
    else:
        messagebox.showinfo("Info", f"{script} is already running.")

def stop_script(script):
    if script in processes and processes[script].poll() is None:
        processes[script].terminate()
        update_status(script, "Stopped")
    else:
        messagebox.showinfo("Info", f"{script} is not running.")

def start_all():
    for script in python_scripts:
        start_script(script)

def stop_all():
    for script in python_scripts:
        stop_script(script)

def update_status(script, status):
    status_labels[script].config(text=f"{script}: {status}")

def create_ui():
    root = tk.Tk()
    root.title("BotSuite")

    for script in python_scripts:
        frame = tk.Frame(root)
        frame.pack(fill=tk.X)

        label = tk.Label(frame, text=script)
        label.pack(side=tk.LEFT)

        start_button = tk.Button(frame, text="Start", command=lambda s=script: start_script(s))
        start_button.pack(side=tk.LEFT)

        stop_button = tk.Button(frame, text="Stop", command=lambda s=script: stop_script(s))
        stop_button.pack(side=tk.LEFT)

        status_label = tk.Label(frame, text=f"{script}: Stopped")
        status_label.pack(side=tk.LEFT)
        status_labels[script] = status_label

    start_all_button = tk.Button(root, text="Start All", command=start_all)
    start_all_button.pack(fill=tk.X)

    stop_all_button = tk.Button(root, text="Stop All", command=stop_all)
    stop_all_button.pack(fill=tk.X)

    root.mainloop()

status_labels = {}
create_ui()