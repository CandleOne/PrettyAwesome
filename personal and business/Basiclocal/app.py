import os
import base64
import io
import qrcode
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, current_app, g
from werkzeug.utils import secure_filename
import PyPDF2
from pdf2image import convert_from_path
from PIL import Image
import time
from celery import Celery
from flask_compress import Compress

# Configuration for upload folders
UPLOAD_FOLDERS = {
    'photo': 'uploads/photos',
    'video': 'uploads/videos',
    'document': 'uploads/documents',
    'audio': 'uploads/audio',
    'other': 'uploads/other'
}

# File type mappings
FILE_CATEGORIES = {
    'photo': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
    'video': ['mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'],
    'document': ['txt', 'pdf', 'docx', 'doc', 'rtf', 'odt'],
    'audio': ['mp3', 'wav', 'ogg', 'flac', 'aac']
}

app = Flask(__name__, static_folder='static')

celery = Celery(app.name, broker='redis://localhost:6379/0')

Compress(app)

# Ensure all upload folders exist
for folder in UPLOAD_FOLDERS.values():
    os.makedirs(folder, exist_ok=True)

def generate_qr_code(url):
    qr_folder = 'static/qr_codes'
    os.makedirs(qr_folder, exist_ok=True)

    qr_filename = f'{hash(url)}.png'
    qr_path = os.path.join(qr_folder, qr_filename)

    # Always generate a new QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=5,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(qr_path)

    return f'qr_codes/{qr_filename}'  # Return path relative to the static folder

def get_pdf_preview(filepath):
    """
    Generate a preview for PDF files
    
    Args:
        filepath (str): Path to the PDF file
    
    Returns:
        dict: A dictionary containing preview information
    """
    try:
        # Read first page content (text)
        with open(filepath, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            first_page = pdf_reader.pages[0]
            text_preview = first_page.extract_text()[:300] + '...' if len(first_page.extract_text()) > 300 else first_page.extract_text()
        
        # Convert first page to image for visual preview
        images = convert_from_path(filepath, first_page=1, last_page=1, size=(300, None))
        
        if images:
            # Convert image to base64
            buffered = io.BytesIO()
            images[0].save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return {
                'text_preview': text_preview,
                'image_preview': img_base64
            }
        
        return {
            'text_preview': text_preview,
            'image_preview': None
        }
    
    except Exception as e:
        print(f"PDF preview error: {e}")
        return {
            'text_preview': f"Error generating preview: {str(e)}",
            'image_preview': None
        }

@celery.task
def process_pdf(filepath):
    return get_pdf_preview(filepath)

def save_file_preview(filepath, category):
    if category == 'document' and filepath.endswith('.pdf'):
        preview = get_pdf_preview(filepath)
        preview_path = f'{filepath}.preview'
        print(f"Saving preview to: {preview_path}")  # Debugging
        with open(preview_path, 'w') as f:
            f.write(preview['text_preview'])

def get_file_category(filename):
    """Determine the category of a file based on its extension"""
    ext = filename.rsplit('.', 1)[1].lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return 'other'

def read_file_preview(filepath, category):
    preview_path = f'{filepath}.preview'
    if os.path.exists(preview_path):
        with open(preview_path, 'r') as f:
            return f.read()
    return "Preview not available"

def list_files():
    """List all files in upload categories with previews"""
    files_by_category = {}
    for category, folder in UPLOAD_FOLDERS.items():
        try:
            category_files = []
            for f in os.listdir(folder):
                filepath = os.path.join(folder, f)
                preview = read_file_preview(filepath, category)
                category_files.append({
                    'name': f, 
                    'path': f'{category}/{f}',
                    'preview': preview
                })
            files_by_category[category] = category_files
        except FileNotFoundError:
            files_by_category[category] = []
    
    return files_by_category

def get_cached_file_list():
    if 'file_cache' not in g or time.time() - g.file_cache['timestamp'] > 10:
        g.file_cache = {
            'files': list_files(),
            'timestamp': time.time()
        }
    return g.file_cache['files']

@app.context_processor
def inject_qr_code():
    """Inject QR code into every template for the current URL"""
    qr_code_path = generate_qr_code(request.url_root)
    print(f"QR Code Path: {qr_code_path}")  # Debugging
    return dict(qr_code_path=qr_code_path)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if files were uploaded
        if 'files[]' not in request.files:
            return redirect(request.url)
        
        files = request.files.getlist('files[]')
        
        for file in files:
            # If no file is selected, skip
            if file.filename == '':
                continue
            
            # Determine file category
            category = get_file_category(file.filename)
            
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Save the file to the appropriate folder
            filepath = os.path.join(UPLOAD_FOLDERS.get(category, 'uploads/other'), filename)
            file.save(filepath)
            
            # Save file preview if applicable
            save_file_preview(filepath, category)
        
        # If this is an AJAX request (from the periodic update), return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            uploaded_files = list_files()
            return jsonify(uploaded_files)
        
        return redirect(url_for('index'))
    
    # Get list of uploaded files
    files = get_cached_file_list()
    
    return render_template('index.html', files=files)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    try:
        parts = filename.replace('\\', '/').split('/')
        if len(parts) < 2:
            return "Invalid file path", 400
        
        category = parts[0]
        file = parts[-1]
        upload_folder = UPLOAD_FOLDERS.get(category, UPLOAD_FOLDERS['other'])
        return send_from_directory(upload_folder, file)
    except Exception as e:
        return f"Error serving file: {str(e)}", 500

@app.route('/file-content/<path:filename>')
def file_content(filename):
    """Get full file content for preview"""
    try:
        # Split the path and handle potential backslash issues
        parts = filename.replace('\\', '/').split('/')
        
        # Ensure we have at least two parts (category and filename)
        if len(parts) < 2:
            return jsonify({'error': 'Invalid file path'}), 400
        
        category = parts[0]
        file = parts[-1]
        
        # Get the correct upload folder, default to 'other' if not found
        upload_folder = UPLOAD_FOLDERS.get(category, UPLOAD_FOLDERS['other'])
        filepath = os.path.join(upload_folder, file)
        
        # Handle different file types
        if category == 'document':
            if filepath.endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return jsonify({'content': f.read()})
            
            elif filepath.endswith('.pdf'):
                # Use the PDF preview function
                pdf_preview = get_pdf_preview(filepath)
                return jsonify({
                    'content': pdf_preview['text_preview'],
                    'image_preview': pdf_preview['image_preview']
                })
        
        elif category == 'photo':
            with open(filepath, 'rb') as f:
                return jsonify({'content': base64.b64encode(f.read()).decode('utf-8')})
        
        elif category == 'video':
            return jsonify({'content': 'Video preview not implemented'})
        
        elif category == 'audio':
            return jsonify({'content': 'Audio preview not implemented'})
        
        return jsonify({'content': 'Unable to preview this file type'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_file/<path:filename>', methods=['POST'])
def delete_file(filename):
    """Delete a file from the upload directory"""
    try:
        # Split the path and handle potential backslash issues
        parts = filename.replace('\\', '/').split('/')
        
        # Ensure we have at least two parts (category and filename)
        if len(parts) < 2:
            return jsonify({'error': 'Invalid file path'}), 400
        
        category = parts[0]
        file = parts[-1]
        
        # Get the correct upload folder, default to 'other' if not found
        upload_folder = UPLOAD_FOLDERS.get(category, UPLOAD_FOLDERS['other'])
        filepath = os.path.join(upload_folder, file)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Delete the file
        os.remove(filepath)
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename, cache_timeout=3600)

if __name__ == '__main__':
    app.run(port=5002, debug=True)