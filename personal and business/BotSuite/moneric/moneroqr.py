import qrcode
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont  # Add Image import
import re
import pyperclip
import os
import time


class MoneroQRGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Monero Payment Request Generator")

        # Get screen width and height
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Set the window size to the screen size
        self.root.geometry(f"{screen_width}x{screen_height}")
        self.root.resizable(True, True)  # Allow resizing

        # Create subfolder for saving QR codes if it doesn't exist
        self.subfolder = "SavedQRs"
        os.makedirs(self.subfolder, exist_ok=True)

        # Configure style
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("Arial", 12))
        self.style.configure("TButton", font=("Arial", 12))
        self.style.configure("TEntry", font=("Arial", 12))

        # Create main frame
        self.main_frame = ttk.Frame(root, padding=20)
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid to expand
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Title
        ttk.Label(self.main_frame, text="Monero Payment Request", font=("Arial", 18, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        # Wallet address input
        address_frame = ttk.Frame(self.main_frame)
        address_frame.grid(row=1, column=0, sticky="ew", pady=10)
        ttk.Label(address_frame, text="Your Monero Address:").pack(anchor=tk.W)
        self.address_entry = ttk.Entry(address_frame, width=50)
        self.address_entry.insert(0, "4xxxxxxx...")  # Example placeholder
        self.address_entry.pack(fill=tk.X, pady=5)

        # Amount input
        amount_frame = ttk.Frame(self.main_frame)
        amount_frame.grid(row=2, column=0, sticky="ew", pady=10)
        ttk.Label(amount_frame, text="Amount (XMR):").pack(anchor=tk.W)
        self.amount_entry = ttk.Entry(amount_frame)
        self.amount_entry.insert(0, "1.0")  # Example placeholder
        self.amount_entry.pack(fill=tk.X, pady=5)

        # Description input
        desc_frame = ttk.Frame(self.main_frame)
        desc_frame.grid(row=3, column=0, sticky="ew", pady=10)
        ttk.Label(desc_frame, text="Description (optional):").pack(anchor=tk.W)
        self.desc_entry = ttk.Entry(desc_frame)
        self.desc_entry.pack(fill=tk.X, pady=5)

        # Customization options
        customization_frame = ttk.Frame(self.main_frame)
        customization_frame.grid(row=1, column=1, rowspan=3, padx=20, sticky="nsew")

        self.scale_var = tk.IntVar(value=5)  # Default scale value
        self.border_var = tk.IntVar(value=4)  # Default border value
        self.dark_color_var = tk.StringVar(value="black")  # Default dark color
        self.light_color_var = tk.StringVar(value="white")  # Default light color
        self.footer_enabled_var = tk.BooleanVar(value=True)  # Footer enabled by default
        self.font_size_var = tk.IntVar(value=12)  # Default font size
        self.footer_position_var = tk.StringVar(value="bottom")  # Default footer position

        # Scale and Border
        ttk.Label(customization_frame, text="QR Code Scale:").pack(anchor=tk.W)
        self.scale_entry = ttk.Entry(customization_frame, textvariable=self.scale_var)
        self.scale_entry.pack(fill=tk.X, pady=5)
        self.scale_entry.bind("<KeyRelease>", self.update_qr_preview)

        ttk.Label(customization_frame, text="QR Code Border:").pack(anchor=tk.W)
        self.border_entry = ttk.Entry(customization_frame, textvariable=self.border_var)
        self.border_entry.pack(fill=tk.X, pady=5)
        self.border_entry.bind("<KeyRelease>", self.update_qr_preview)

        # Color selection buttons
        ttk.Button(customization_frame, text="Choose Dark Color", command=self.choose_dark_color).pack(pady=5)
        ttk.Button(customization_frame, text="Choose Light Color", command=self.choose_light_color).pack(pady=5)

        # Footer toggle
        ttk.Checkbutton(customization_frame, text="Enable Footer", variable=self.footer_enabled_var, command=self.update_qr_preview).pack(pady=5)

        # Font size
        ttk.Label(customization_frame, text="Footer Font Size:").pack(anchor=tk.W)
        self.font_size_entry = ttk.Entry(customization_frame, textvariable=self.font_size_var)
        self.font_size_entry.pack(fill=tk.X, pady=5)
        self.font_size_entry.bind("<KeyRelease>", self.update_qr_preview)

        # Footer position
        ttk.Label(customization_frame, text="Footer Position:").pack(anchor=tk.W)
        self.footer_position_menu = ttk.OptionMenu(customization_frame, self.footer_position_var, "bottom", "bottom", "top")
        self.footer_position_menu.pack(fill=tk.X, pady=5)

        # Generate button
        self.generate_btn = ttk.Button(self.main_frame, text="Generate QR Code", command=self.generate_qr)
        self.generate_btn.grid(row=4, column=1, pady=5, sticky="ew")

        # Save button (initially hidden)
        self.save_btn = ttk.Button(self.main_frame, text="Save QR Code", command=self.save_qr, state=tk.DISABLED)
        self.save_btn.grid(row=5, column=1, pady=5, sticky="ew")

        # Copy URI button (initially hidden)
        self.copy_btn = ttk.Button(self.main_frame, text="Copy Payment URI", command=self.copy_uri, state=tk.DISABLED)
        self.copy_btn.grid(row=6, column=1, pady=5, sticky="ew")

        # POS button (initially hidden)
        self.pos_btn = ttk.Button(self.main_frame, text="Open POS Window", command=self.open_pos_window, state=tk.DISABLED)
        self.pos_btn.grid(row=7, column=1, pady=5, sticky="ew")

        # Add a button to select the destination folder
        self.select_folder_btn = ttk.Button(self.main_frame, text="Select Destination Folder", command=self.select_destination_folder)
        self.select_folder_btn.grid(row=8, column=1, pady=5, sticky="ew")

        # Add this in the __init__ method to create the checkbox for automatic naming
        self.auto_naming_var = tk.BooleanVar(value=True)  # Automatic naming enabled by default
        ttk.Checkbutton(self.main_frame, text="Enable Automatic Naming", variable=self.auto_naming_var).grid(row=9, column=1, pady=5, sticky="ew")

        # QR code display with scrollable canvas
        self.qr_canvas_frame = ttk.Frame(self.main_frame)
        self.qr_canvas_frame.grid(row=4, column=0, rowspan=3, sticky="nsew", pady=0)
        
        self.qr_canvas = tk.Canvas(self.qr_canvas_frame)
        self.qr_scrollbar = ttk.Scrollbar(self.qr_canvas_frame, orient="vertical", command=self.qr_canvas.yview)
        self.qr_canvas.configure(yscrollcommand=self.qr_scrollbar.set)
        
        self.qr_scrollbar.pack(side="right", fill="y")
        self.qr_canvas.pack(side="left", fill="both", expand=True)
        
        self.qr_frame = ttk.Frame(self.qr_canvas)
        self.qr_canvas.create_window((0, 0), window=self.qr_frame, anchor="nw")
        
        self.qr_label = ttk.Label(self.qr_frame)
        self.qr_label.pack(pady=0)
        
        self.qr_frame.bind("<Configure>", lambda e: self.qr_canvas.configure(scrollregion=self.qr_canvas.bbox("all")))

        # Payment info
        self.payment_info = ttk.Label(self.main_frame, text="", wraplength=550)
        self.payment_info.grid(row=8, column=0, columnspan=1, pady=0)

        # Hot URL frame
        hot_url_frame = ttk.Frame(self.main_frame)
        hot_url_frame.grid(row=10, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Label(hot_url_frame, text="Hot URL:", font=("Arial", 14, "bold")).pack(anchor=tk.W)
        self.hot_url_label = ttk.Label(hot_url_frame, text="", font=("Arial", 12), wraplength=screen_width - 40)
        self.hot_url_label.pack(fill=tk.X, pady=5)
        self.copy_hot_url_btn = ttk.Button(hot_url_frame, text="Copy Hot URL", command=self.copy_hot_url)
        self.copy_hot_url_btn.pack(pady=5)

        # Current QR code image
        self.current_qr = None
        self.qr_image = None
        self.payment_uri = ""

        # Destination folder for saving QR codes
        self.destination_folder = tk.StringVar(value=self.subfolder)

        self.check_ngrok_url()  # Start checking for ngrok URL

    def validate_monero_address(self, address):
        # Basic validation for Monero address (starts with 4 or 8 and is 95 characters long)
        pattern = r'^(4|8)[1-9A-HJ-NP-Za-km-z]{94}$'
        return re.match(pattern, address) is not None

    def validate_amount(self, amount_str):
        try:
            amount = float(amount_str)
            return amount > 0
        except ValueError:
            return False

    def generate_payment_uri(self, address, amount, description=""):
        # Create Monero URI format
        uri = f"monero:{address}?tx_amount={amount}"
        if description:
            uri += f"&tx_description={description}"
        return uri

    def generate_qr(self):
        # Get input values
        address = self.address_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        description = self.desc_entry.get().strip()

        # Validate input
        if not address:
            messagebox.showerror("Error", "Please enter your Monero wallet address")
            return

        if not self.validate_monero_address(address):
            messagebox.showerror("Error", "Invalid Monero address format")
            return

        if not amount_str or not self.validate_amount(amount_str):
            messagebox.showerror("Error", "Please enter a valid amount")
            return

        amount = float(amount_str)

        # Generate payment URI
        self.payment_uri = self.generate_payment_uri(address, amount, description)

        # Generate QR code with a fixed scale of 5
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5 * 10,  # Fixed scale of 5
            border=self.border_var.get(),
        )
        qr.add_data(self.payment_uri)
        qr.make(fit=True)

        # Create QR image with customization
        self.qr_image = qr.make_image(
            fill_color=self.dark_color_var.get(), back_color=self.light_color_var.get()
        )

        # Resize the QR image for display using the user-set scale
        display_scale = self.scale_var.get()
        self.qr_image = self.qr_image.resize((display_scale * 50, display_scale * 50))

        # Add text to the QR code image if footer is enabled
        if self.footer_enabled_var.get():
            draw = ImageDraw.Draw(self.qr_image)
            font_size = self.font_size_var.get()
            font = ImageFont.truetype("arial.ttf", font_size)
            text = f"Amount: {amount} XMR"
            if description:
                text += f"\n| {description}"

            # Split text into multiple lines if it exceeds a certain width
            max_width = self.qr_image.width - 20  # Allow some padding
            lines = []
            words = text.split()
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                test_bbox = draw.textbbox((0, 0, 0, 0), test_line, font=font)
                test_width = test_bbox[2] - test_bbox[0]
                if test_width <= max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            # Calculate the total height of the text
            text_height = sum(draw.textbbox((0, 0, 0, 0), line, font=font)[3] - draw.textbbox((0, 0, 0, 0), line, font=font)[1] for line in lines)
            image_width, image_height = self.qr_image.size

            # Create a new image with additional space for the footer
            new_image_height = image_height + text_height + 20  # Add some padding
            new_image = Image.new("RGB", (image_width, new_image_height), self.light_color_var.get())
            if self.footer_position_var.get() == "bottom":
                new_image.paste(self.qr_image, (0, 0))
                text_y = image_height + 10
            else:
                new_image.paste(self.qr_image, (0, text_height + 20))
                text_y = 10

            # Draw the text on the new image
            draw = ImageDraw.Draw(new_image)
            for line in lines:
                text_bbox = draw.textbbox((0, 0, 0, 0), line, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_x = (image_width - text_width) // 2
                draw.text((text_x, text_y), line, font=font, fill=self.dark_color_var.get())
                text_y += text_bbox[3] - text_bbox[1]

            self.qr_image = new_image

        # Convert for display
        self.current_qr = ImageTk.PhotoImage(self.qr_image)
        self.qr_label.config(image=self.current_qr)
        
        # Update the scroll region
        self.qr_canvas.configure(scrollregion=self.qr_canvas.bbox("all"))

        # Show payment info
        payment_data = {
            "address": address,
            "amount": amount,
            "description": description,
        }
        info_text = f"Payment Request:\n• Amount: {amount} XMR\n• Address: {address[:8]}...{address[-8:]}"
        if description:
            info_text += f"\n• Description: {description}"
        self.payment_info.config(text=info_text)

        # Enable save button, copy button, and POS button
        self.save_btn.config(state=tk.NORMAL)
        self.copy_btn.config(state=tk.NORMAL)
        self.pos_btn.config(state=tk.NORMAL)

    def save_qr(self):
        if self.qr_image:
            if self.auto_naming_var.get():
                # Generate a filename based on the current timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"QR_{timestamp}.png"
                file_path = os.path.join(self.destination_folder.get(), filename)
                
            else:
                # Ask user for the destination file path within the selected folder
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG files", "*.png")],
                    initialdir=self.destination_folder.get(),
                    title="Save QR Code"
                )
            
            if file_path:
                # Save the image
                self.qr_image.save(file_path)
                messagebox.showinfo("Success", f"QR code saved as {file_path}")
                self.cleanup_old_qr_codes(file_path)

    def cleanup_old_qr_codes(self, new_file_path):
        # Delete all QR codes in the folder except the new one
        for filename in os.listdir(self.destination_folder.get()):
            file_path = os.path.join(self.destination_folder.get(), filename)
            if file_path != new_file_path and filename.endswith(".png"):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

    def copy_uri(self):
        if self.payment_uri:
            pyperclip.copy(self.payment_uri)  # Requires the pyperclip library
            messagebox.showinfo("Success", "Payment URI copied to clipboard")

    def choose_dark_color(self):
        color_code = colorchooser.askcolor(title="Choose dark color")[1]
        if color_code:
            self.dark_color_var.set(color_code)
            self.update_qr_preview()

    def choose_light_color(self):
        color_code = colorchooser.askcolor(title="Choose light color")[1]
        if color_code:
            self.light_color_var.set(color_code)
            self.update_qr_preview()

    def update_qr_preview(self, *args):
        self.generate_qr()  # Regenerate the QR code to reflect any changes

    def open_pos_window(self):
        pos_window = tk.Toplevel(self.root)
        pos_window.title("POS QR Code")

        # Calculate the size of the QR code image
        qr_width, qr_height = self.qr_image.size

        # Set the window size to fit the QR code image with some padding
        window_width = qr_width + 40
        window_height = qr_height + 100

        pos_window.geometry(f"{window_width}x{window_height}")
        pos_window.resizable(False, False)

        pos_qr_label = ttk.Label(pos_window, text="Scan to Pay!", font=("Arial", 16, "bold"))
        pos_qr_label.pack(pady=10)

        pos_qr_display = ttk.Label(pos_window, image=self.current_qr)
        pos_qr_display.pack(pady=10)

        close_btn = ttk.Button(pos_window, text="Close", command=pos_window.destroy)
        close_btn.pack(pady=10)

    def select_destination_folder(self):
        folder_selected = filedialog.askdirectory(initialdir=self.subfolder, title="Select Destination Folder")
        if folder_selected:
            self.destination_folder.set(folder_selected)

    def display_ngrok_url(self):
        try:
            with open('ngrok_url.txt', 'r') as f:
                ngrok_url = f.read().strip()
                self.hot_url_label.config(text=ngrok_url)
        except FileNotFoundError:
            self.hot_url_label.config(text="ngrok URL file not found.")
        except Exception as e:
            self.hot_url_label.config(text=f"Error reading ngrok URL: {e}")

    def check_ngrok_url(self):
        self.display_ngrok_url()
        self.root.after(5, self.check_ngrok_url)  # Check every 5ms

    def copy_hot_url(self):
        hot_url = self.hot_url_label.cget("text")
        if hot_url:
            pyperclip.copy(hot_url)
            messagebox.showinfo("Success", "Hot URL copied to clipboard")

def display_ngrok_url():
    try:
        with open('ngrok_url.txt', 'r') as f:
            ngrok_url = f.read().strip()
            print(f"ngrok URL: {ngrok_url}")
    except FileNotFoundError:
        print("ngrok URL file not found.")
    except Exception as e:
        print(f"Error reading ngrok URL: {e}")

def main():
    root = tk.Tk()
    app = MoneroQRGenerator(root)
    app.display_ngrok_url()  # Display the ngrok URL when the application starts
    root.mainloop()

if __name__ == "__main__":
    display_ngrok_url()
    # main()  # Comment out or remove this line to prevent opening the UI app

def generate_payment_uri(address, amount, payment_id=None):
    """
    Generate a Monero payment URI.
    
    :param address: Monero address
    :param amount: Amount to be paid
    :param payment_id: Optional payment ID
    :return: Payment URI string
    """
    uri = f"monero:{address}?tx_amount={amount}"
    if payment_id:
        uri += f"&tx_payment_id={payment_id}"
    return uri