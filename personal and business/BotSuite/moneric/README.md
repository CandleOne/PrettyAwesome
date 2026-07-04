# Monero QR Code Generator

This project is a Monero Payment Request Generator that allows users to create QR codes for Monero transactions. The application provides a user-friendly interface for generating payment requests, customizing QR code appearance, and saving or copying the generated QR code.

## Features

- Generate Monero payment QR codes.
- Validate Monero wallet addresses and transaction amounts.
- Customize QR code appearance (scale, border, colors, footer).
- Save generated QR codes as PNG files.
- Copy payment URI to clipboard.
- Display generated QR code in a separate window for customer-facing point of sale (POS) use.

## Requirements

- Python 3.x
- `qrcode` library
- `Pillow` library
- `pyperclip` library
- `tkinter` (included with standard Python installations)

## Installation

1. Clone the repository or download the source code.
2. Install the required libraries using pip:

   ```
   pip install qrcode[pil] Pillow pyperclip
   ```

3. Run the application:

   ```
   python moneroqr.py
   ```

## Usage

1. Enter your Monero wallet address in the designated field.
2. Specify the amount of XMR you wish to request.
3. Optionally, add a description for the payment request.
4. Customize the QR code appearance using the provided options.
5. Click "Generate QR Code" to create the QR code.
6. Use the "Save QR Code" button to save the generated QR code as a PNG file.
7. Click "Copy Payment URI" to copy the generated payment URI to your clipboard.
8. To display the QR code in a separate window for POS use, click the appropriate button after generating the QR code.

## License

This project is licensed under the MIT License. See the LICENSE file for details.