import sys
import os
import webview
from threading import Thread
from app import app
from utils.data_manager import DataManager

def run_flask():
    """Run Flask server in background thread"""
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False,
        use_reloader=False,  # Important: disable reloader for PyInstaller
    )

def main():
    """Create and start desktop application"""
    # Initialize data files (copy from bundle to exe directory if needed)
    data_manager = DataManager()
    data_manager.initialize_data_files()
    
    # Start Flask server in background
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Create and display PyWebView window
    window = webview.create_window(
        title='GB Delight - AI Cake Assistant',
        url='http://127.0.0.1:5000',
        background_color='#FFF7F9',
        min_size=(800, 600),
        width=1200,
        height=800,
    )

    webview.start(debug=False)

if __name__ == '__main__':
    main()