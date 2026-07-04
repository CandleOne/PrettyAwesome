# Color Picker Project

This project is a simple web application that allows users to select a color using a color wheel input. The selected color is then displayed on the web page.

## Project Structure

```
color-picker-project
├── src
│   ├── app.py          # Main Python application
│   └── static
│       └── index.html  # HTML file with color wheel input
├── requirements.txt     # List of dependencies
└── README.md            # Project documentation
```

## Setup Instructions

1. Clone the repository or download the project files.
2. Navigate to the project directory.
3. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```
5. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python src/app.py
   ```
2. Open your web browser and go to `http://127.0.0.1:5000` to access the color picker.
3. Use the color wheel to select a color, and the selected color will be displayed on the page.

## Dependencies

- Flask: A lightweight WSGI web application framework in Python.

## License

This project is licensed under the MIT License.