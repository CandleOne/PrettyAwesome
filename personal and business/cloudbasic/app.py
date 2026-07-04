import os
import base64
import io
import qrcode
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image

# Import PDF libraries with error handling
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    print("Warning: PyPDF2 not available. PDF text extraction will be disabled.")
    PDF_SUPPORT = False

try:
    from pdf2image import convert_from_path
    PDF_IMAGE_SUPPORT = True
except ImportError:
    print("Warning: pdf2image not available. PDF preview images will be disabled.")
    PDF_IMAGE_SUPPORT = False

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

app = Flask(__name__)

# Ensure all upload folders exist
for folder in UPLOAD_FOLDERS.values():
    os.makedirs(folder, exist_ok=True)

def generate_qr_code(url):
    """
    Generate a QR code for the given URL
    
    Args:
        url (str): URL to encode in the QR code
    
    Returns:
        str: Base64 encoded QR code image
    """
    try:
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create an image from the QR Code
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffered = io.BytesIO()
        qr_image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return img_base64
    except Exception as e:
        print(f"QR Code generation error: {e}")
        return None

def get_pdf_preview(filepath):
    """
    Generate a preview for PDF files
    
    Args:
        filepath (str): Path to the PDF file
    
    Returns:
        dict: A dictionary containing preview information
    """
    result = {'text_preview': None, 'image_preview': None}
    
    # Try to extract text if PyPDF2 is available
    if PDF_SUPPORT:
        try:
            with open(filepath, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                if len(pdf_reader.pages) > 0:
                    first_page = pdf_reader.pages[0]
                    text_content = first_page.extract_text()
                    result['text_preview'] = text_content[:300] + '...' if len(text_content) > 300 else text_content
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
    
    # Try to generate image preview if pdf2image is available
    if PDF_IMAGE_SUPPORT:
        try:
            images = convert_from_path(filepath, first_page=1, last_page=1, size=(300, None))
            
            if images:
                # Convert image to base64
                buffered = io.BytesIO()
                images[0].save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                result['image_preview'] = img_base64
        except Exception as e:
            print(f"Error generating PDF image preview: {e}")
    
    # If no preview methods worked, provide a fallback
    if not result['text_preview'] and not result['image_preview']:
        result['text_preview'] = "PDF preview not available. Please download to view."
    
    return result

def get_file_category(filename):
    """Determine the category of a file based on its extension"""
    ext = filename.rsplit('.', 1)[1].lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return 'other'

def read_file_preview(filepath, category):
    """Generate a preview for different file types"""
    try:
        if category == 'document':
            # For text files, read first 200 characters
            if filepath.endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return content[:200] + '...' if len(content) > 200 else content
            
            # For PDFs, use the PDF preview function
            if filepath.endswith('.pdf'):
                pdf_preview = get_pdf_preview(filepath)
                return pdf_preview['text_preview']
            
            return "Document File"
        
        elif category == 'photo':
            # Encode photo as base64 for inline display
            with open(filepath, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        
        elif category == 'video':
            return "Video File"
        
        elif category == 'audio':
            return "Audio File"
        
        return "Unknown File Type"
    except Exception as e:
        return f"Error reading file: {str(e)}"

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

@app.context_processor
def inject_qr_code():
    """Inject QR code into every template for current URL"""
    qr_code = generate_qr_code(request.url_root)
    return dict(qr_code=qr_code)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        
        # If no file is selected, redirect
        if file.filename == '':
            return redirect(request.url)
        
        # Determine file category
        category = get_file_category(file.filename)
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Save the file to the appropriate folder
        filepath = os.path.join(UPLOAD_FOLDERS.get(category, 'uploads/other'), filename)
        file.save(filepath)
        
        # If this is an AJAX request (from the periodic update), return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            uploaded_files = list_files()
            return jsonify(uploaded_files)
        
        return redirect(url_for('index'))
    
    # Get list of uploaded files
    uploaded_files = list_files()
    
    return render_template('index.html', files=uploaded_files)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    try:
        # Split the path and handle potential backslash issues
        parts = filename.replace('\\', '/').split('/')
        
        # Ensure we have at least two parts (category and filename)
        if len(parts) < 2:
            return "Invalid file path", 400
        
        category = parts[0]
        file = parts[-1]
        
        # Get the correct upload folder, default to 'other' if not found
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

if __name__ == '__main__':
    app.run(port=5002, debug=True)