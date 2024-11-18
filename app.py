from flask import Flask, request, send_file
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
import os
from io import BytesIO
import time
import tempfile
from flask_cors import CORS

# Get Spotify API credentials from environment variables
CLIENT_ID = '6fa6c92cdbf64239a09f921a2e7ef207'
CLIENT_SECRET = '3cb7b2afdf12457f9d8843d58f4c8ae5'

# Initialize Spotify API client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for the app
CORS(app)

def search_youtube_for_song(song_name):
    # Perform a search on YouTube (including YouTube Music) using yt-dlp's built-in search functionality
    search_query = song_name  # Simply search for the song name without site filtering
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Only extract metadata, not the full video
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch:{search_query}", download=False)

        if 'entries' in result and result['entries']:
            # Get the first video URL from search results
            video_url = f"https://www.youtube.com/watch?v={result['entries'][0]['id']}"
            return video_url
        else:
            return None

def get_spotify_song_link(song_id):
    # Fetch the song details using the Spotify track ID
    track = sp.track(song_id)
    song_name = track['name']
    return song_name

def download_audio_from_youtube(video_url, temp_file_path):
    # Add a timestamp to the temporary filename to avoid overwriting
    unique_filename = f"{temp_file_path}_{int(time.time())}.mp3"

    # Set options to download audio directly without converting
    ydl_opts = {
        'format': 'bestaudio/best',  # Download the best audio quality
        'quiet': False,              # Disable quiet mode for debugging
        'extractaudio': True,        # Only extract audio (no video)
        'outtmpl': unique_filename,  # Save to the specified temporary file with a unique name
        'noplaylist': True,          # Avoid downloading the whole playlist if one is found
        'cookies': os.getenv('YT_COOKIES'),  # Use cookies from environment variable
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Starting download for {video_url}")
            ydl.download([video_url])  # Download the audio to the temp file path
            print(f"Download complete for {video_url}")

    except Exception as e:
        print(f"Error while downloading audio from YouTube: {e}")

    return unique_filename  # Return the unique file path for further use


@app.route('/download', methods=['GET'])
def download_song():
    spotify_song_id = request.args.get('spotify_song_id')

    if not spotify_song_id:
        return {"error": "Spotify song ID is required"}, 400

    # Step 1: Get the song name from Spotify using the ID
    song_name = get_spotify_song_link(spotify_song_id)

    # Step 2: Search for the song on YouTube and get the video URL
    video_url = search_youtube_for_song(song_name)
    
    if video_url:
        # Step 3: Download the song to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file_path = temp_file.name  # Get the path to the temp file

            # Download the audio from YouTube
            download_audio_from_youtube(video_url, temp_file_path)

            # After downloading, send the file to the client
            response = send_file(temp_file_path, mimetype='audio/mpeg', as_attachment=True, download_name='song.mp3')

            # Ensure temporary file cleanup after serving it
            os.remove(temp_file_path)  # Clean up the temporary file after sending it to the client

            return response

    else:
        return {"error": f"No results found for {song_name} on YouTube."}, 404


if __name__ == "__main__":
    # Get the dynamic port from the environment (Render or cloud providers)
    port = int(os.getenv('PORT', 5000))  # Default to 5000 if not provided
    app.run(debug=True, host='0.0.0.0', port=port)  # Bind to 0.0.0.0 for external access
