# Multi-Device File Management Web App

## Overview
This is a Flask-based web application that allows file uploads, previews, and management across multiple devices. Features include:
- File upload for various file types (documents, photos, videos, audio)
- QR code generation for easy access from other devices
- Real-time file list updates
- File preview and download functionality

## Prerequisites
- Python 3.8+
- ngrok (for external access)

## Setup Instructions

1. Clone the repository
```bash
git clone https://github.com/yourusername/file-management-app.git
cd file-management-app
```

2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Run the application
```bash
python run_concur.py
```

## Features
- Upload files from any device
- Generate QR code for sharing access
- Preview documents, images
- Delete files
- Automatic 2-second refresh of file list

## Technology Stack
- Flask
- Python
- HTML/CSS/JavaScript
- ngrok for external access

## Troubleshooting
- Ensure all dependencies are installed
- Check that ngrok is installed and in PATH
- Verify file upload directories have write permissions

## License
MIT License