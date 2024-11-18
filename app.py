from flask import Flask, request, send_file
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
import os
import tempfile
import time  # <-- Import time module
from flask_cors import CORS

# Spotify API credentials
CLIENT_ID = '6fa6c92cdbf64239a09f921a2e7ef207'
CLIENT_SECRET = '3cb7b2afdf12457f9d8843d58f4c8ae5'

# Initialize Spotify API client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for the app
CORS(app)

def search_youtube_for_song(song_name):
    search_query = song_name
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch:{search_query}", download=False)
        if 'entries' in result and result['entries']:
            return f"https://www.youtube.com/watch?v={result['entries'][0]['id']}"
    return None

def get_spotify_song_name(song_id):
    track = sp.track(song_id)
    return track['name']

def download_audio_from_youtube(video_url, temp_file_path):
    # Add a timestamp to the temporary filename to avoid overwriting
    unique_filename = f"{temp_file_path}_{int(time.time())}.mp3"  # <-- Using time.time()

    # Set options to download audio directly without converting
    ydl_opts = {
        'format': 'bestaudio/best',  # Download the best audio quality
        'quiet': False,              # Disable quiet mode for debugging
        'extractaudio': True,        # Only extract audio (no video)
        'outtmpl': unique_filename,  # Save to the specified temporary file with a unique name
        'noplaylist': True,          # Avoid downloading the whole playlist if one is found
        'cookies': 'youtube_cookies.txt',  # Path to the cookies file (relative path)
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

    try:
        # Step 1: Get song name from Spotify
        song_name = get_spotify_song_name(spotify_song_id)

        # Step 2: Search YouTube for the song
        video_url = search_youtube_for_song(song_name)
        if not video_url:
            return {"error": f"No results found for {song_name} on YouTube."}, 404

        # Step 3: Download audio from YouTube
        file_path = download_audio_from_youtube(video_url, song_name)
        if not file_path or not os.path.exists(file_path):
            return {"error": "Failed to download the song."}, 500

        # Step 4: Send the file as a response
        return send_file(file_path, mimetype='audio/mpeg', as_attachment=True, download_name=f"{song_name}.mp3")

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    # Get the dynamic port from the environment (Render or cloud providers)
    port = int(os.getenv('PORT', 5000))  # Default to 5000 if not provided
    app.run(debug=True, host='0.0.0.0', port=port)
