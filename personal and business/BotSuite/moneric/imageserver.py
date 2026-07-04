import os
import time
from flask import Flask, render_template, send_file
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

app = Flask(__name__)

# Path to the folder containing the images
image_folder_path = r'C:\Users\jacob\Desktop\moneroqr\SavedQRs'  # Use raw string to avoid unicode escape issues
latest_image_path = None

# Class to handle file changes
class ImageFolderWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        global latest_image_path
        if event.is_directory:
            return
        if any(event.src_path.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            latest_image_path = get_most_recent_image(image_folder_path)

# Function to get the most recent image
def get_most_recent_image(folder_path):
    files = os.listdir(folder_path)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    if not image_files:
        return None
    most_recent_image = max(image_files, key=lambda f: os.path.getmtime(os.path.join(folder_path, f)))
    return os.path.join(folder_path, most_recent_image)

# Route to serve the most recent image
@app.route('/latest_image')
def latest_image():
    if latest_image_path:
        return send_file(latest_image_path, mimetype='image/jpeg')  # Adjust mimetype if necessary
    return "No image available", 404

# Route to display the HTML page with the image
@app.route('/')
def index():
    return render_template('index.html')

# Start folder watcher in background
def start_folder_watcher():
    global latest_image_path
    latest_image_path = get_most_recent_image(image_folder_path)
    event_handler = ImageFolderWatcher()
    observer = Observer()
    observer.schedule(event_handler, image_folder_path, recursive=False)
    observer.start()

if __name__ == "__main__":
    start_folder_watcher()
    app.run(debug=True, threaded=True)
