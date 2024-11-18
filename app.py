import os
import logging
from flask import Flask, request, jsonify
import yt_dlp
from flask_cors import CORS


# Initialize Flask app
app = Flask(__name__)

# Enable CORS for the app
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcoded path to the cookie file (adjust this path as needed)
COOKIE_FILE_PATH = 'youtube_cookies.txt'  # Replace with the actual path to your cookie.txt file

# Function to get cookies from environment variable (base64-encoded)
def verify_youtube_cookie(cookie_file):
    # Step 1: Check if the cookie file exists
    if not os.path.exists(cookie_file):
        logger.error(f"Cookie file '{cookie_file}' not found.")
        return False
    
    # Step 2: Try downloading or extracting info using the cookie file
    ydl_opts = {
        'cookies': cookie_file,  # Path to the cookies file
        'quiet': True,            # Silence the download process (we only want to check the cookie)
        'extract_flat': True,     # Don't download, just extract metadata
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Example video to verify the cookie (using a public, not age-restricted YouTube video)
            test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'  # You can replace this with any YouTube URL
            result = ydl.extract_info(test_url, download=False)
            
            # If we successfully get the result, the cookie is valid
            if result:
                logger.info(f"Cookie file '{cookie_file}' is valid. Successfully fetched video info.")
                return True
            else:
                logger.error(f"Failed to fetch video info using the cookie file '{cookie_file}'.")
                return False
    except Exception as e:
        logger.error(f"Error verifying cookie file: {e}")
        return False


# API endpoint to verify the YouTube cookie
@app.route('/verify-cookie', methods=['GET'])
def verify_cookie():
    # Use the hardcoded cookie file path
    logger.info(f"Received request to verify cookie: {COOKIE_FILE_PATH}")
    
    # Call the verify function
    is_valid = verify_youtube_cookie(COOKIE_FILE_PATH)
    
    # Respond with the result
    if is_valid:
        logger.info(f"Cookie verification successful for file: {COOKIE_FILE_PATH}")
        return jsonify({'message': 'Cookie file is valid.'}), 200
    else:
        logger.error(f"Cookie verification failed for file: {COOKIE_FILE_PATH}")
        return jsonify({'error': 'Invalid cookie file.'}), 400


# Main entry point for the app
if __name__ == "__main__":
    # Get the dynamic port from the environment (Render or cloud providers)
    port = int(os.getenv('PORT', 5000))  # Default to 5000 if not provided
    logger.info(f"Starting app on port {port}...")
    app.run(debug=True, host='0.0.0.0', port=port)
