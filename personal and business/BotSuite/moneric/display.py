import os
from tkinter import Tk, Label, Button, filedialog
from PIL import Image, ImageTk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from screeninfo import get_monitors

class ImageFolderWatcher(FileSystemEventHandler):
    def __init__(self, folder_path, update_callback):
        self.folder_path = folder_path
        self.update_callback = update_callback

    def on_modified(self, event):
        if event.is_directory:
            return
        if any(event.src_path.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            self.update_callback()

def get_most_recent_image(folder_path):
    files = os.listdir(folder_path)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    if not image_files:
        return None
    most_recent_image = max(image_files, key=lambda f: os.path.getmtime(os.path.join(folder_path, f)))
    return os.path.join(folder_path, most_recent_image)

class ImageViewer:
    def __init__(self, root):
        self.root = root
        self.folder_path = None
        self.image_label = Label(root)
        self.image_label.pack()

        self.refresh_button = Button(root, text="Refresh", command=self.update_image)
        self.refresh_button.pack()

        self.select_folder_button = Button(root, text="Select Folder", command=self.select_folder)
        self.select_folder_button.pack()

        self.watcher = None
        self.observer = None

        # Set the window to display on a specific monitor (e.g., second monitor)
        self.set_window_on_monitor(1)  # 0 for first monitor, 1 for second, etc.

    def set_window_on_monitor(self, monitor_index):
        monitors = get_monitors()
        if monitor_index < len(monitors):
            monitor = monitors[monitor_index]
            # Set the position of the window to the monitor's position (x, y)
            self.root.geometry(f"+{monitor.x+100}+{monitor.y+100}")  # Optional offset for margin

    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder")
        if folder_path:
            self.folder_path = folder_path
            self.start_folder_watcher(folder_path)
            self.update_image()

    def start_folder_watcher(self, folder_path):
        if self.watcher:
            self.observer.stop()
            self.observer.join()

        self.watcher = ImageFolderWatcher(folder_path, self.update_image)
        self.observer = Observer()
        self.observer.schedule(self.watcher, folder_path, recursive=False)
        self.observer.start()

    def update_image(self):
        if self.folder_path:
            most_recent_image_path = get_most_recent_image(self.folder_path)
            if most_recent_image_path:
                self.display_image(most_recent_image_path)

    def display_image(self, image_path):
        try:
            img = Image.open(image_path)
            img.thumbnail((500, 500))  # Resize for display
            img_tk = ImageTk.PhotoImage(img)
            self.image_label.config(image=img_tk)
            self.image_label.image = img_tk
        except Exception as e:
            print(f"Error opening image: {e}")

def start_gui():
    root = Tk()
    root.title("Image Viewer")

    viewer = ImageViewer(root)

    # Start the GUI loop
    root.mainloop()

if __name__ == "__main__":
    start_gui()
