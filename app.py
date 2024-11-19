import os
import requests
import sys
from flask import Flask, request, jsonify
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from flask_cors import CORS  # Importing CORS from flask_cors

# Spotify API credentials
CLIENT_ID = '6fa6c92cdbf64239a09f921a2e7ef207'
CLIENT_SECRET = '3cb7b2afdf12457f9d8843d58f4c8ae5'

# Initialize Spotify API client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

app = Flask(__name__)

# Enable CORS for all routes and origins (you can restrict this later as needed)
CORS(app)

def search_youtube_for_song(song_name):
    """
    Perform a search on YouTube (including YouTube Music) using yt-dlp's built-in search functionality.
    """
    search_query = song_name  # Simply search for the song name without site filtering
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Only extract metadata, not the full video
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch:{search_query}", download=False)

        # Debugging: print the raw search results to understand what we got
        sys.stdout.buffer.write(f"Search result for '{song_name}': {result}\n".encode('utf-8'))

        if 'entries' in result and result['entries']:
            # Get the first video ID from search results
            video_id = result['entries'][0]['id']
            return video_id, result['entries'][0]['url']
        else:
            print(f"No results found for '{song_name}' on YouTube.")
            return None, None

def get_spotify_song_data(song_id):
    """
    Fetch song data (name, artist, album) from Spotify using the song ID.
    """
    try:
        # Fetch the song details using the Spotify track ID
        track = sp.track(song_id)
        
        # Extract basic information
        song_name = track['name']
        artist_name = track['artists'][0]['name']
        album_name = track['album']['name']
        album_cover = track['album']['images'][0]['url'] if track['album'].get('images') else ''  # Fallback if no cover image

        # Handle missing genre information gracefully
        genre = track['album']['genres'][0] if track['album'].get('genres') else 'Unknown'  # Default to 'Unknown' if no genres

        # Extract other metadata with error handling for missing fields
        release_year = track['album']['release_date'][:4] if 'release_date' in track['album'] else 'Unknown'  # Default to 'Unknown' if no release date
        isrc = track['external_ids'].get('isrc', 'Unknown')  # Default to 'Unknown' if no ISRC available
        copyright_info = track['copyrights'][0]['text'] if track.get('copyrights') else 'No copyright information'  # Handle missing copyrights
        track_number = track.get('track_number', 'Unknown')  # Default to 'Unknown' if no track number
        duration_ms = track['duration_ms']  # Duration in milliseconds
        duration = f"{(duration_ms // 60000)}:{(duration_ms % 60000) // 1000:02d}"  # Format duration as mm:ss

        # Build the song data object
        song_data = {
            'song_name': song_name,
            'artist_name': artist_name,
            'album_name': album_name,
            'album_cover': album_cover,  # Album cover image URL
            'genre': genre,
            'release_year': release_year,
            'isrc': isrc,
            'copyright_info': copyright_info,
            'track_number': track_number,
            'duration': duration,
        }

        return song_data

    except Exception as e:
        # Handle any error that occurs and return a message
        return {
            'error': str(e),
            'message': 'An error occurred while fetching song data from Spotify.'
        }


def get_mp3_download_link(video_id):
    """
    Function to retrieve an MP3 download link from a third-party source.
    Downloads the MP3 file from the YouTube MP3 download API.
    """
    # API URL to fetch the MP3 download link
    url = f'https://youtube-mp36.p.rapidapi.com/dl?id={video_id}'
    
    # Headers to include in the request (ensure you have a valid RapidAPI key)
    headers = {
        'x-rapidapi-host': 'youtube-mp36.p.rapidapi.com',
        'x-rapidapi-key': '3dab8d0338msh860dc1baf2f6e9bp1a3029jsna4a66ccdd07d'
    }

    # Send the GET request
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response JSON to get the download URL
        data = response.json()

        # Debugging: print the full API response to understand why it's failing
        print(f"API Response: {data}")  # Debugging: print the full response

        if "link" in data:
            # Extract the MP3 download URL
            download_url = data['link']
            print(f"Download URL: {download_url}")
            return download_url
        else:
            print("Failed to find the download URL in the response.")
            return None
    else:
        # Handle errors and print the response details
        print(f"Error: {response.status_code}")
        print("Response Body:", response.text)
        return None


@app.route('/get-song-details', methods=['GET'])
def get_song_details():
    """
    Endpoint to fetch song details, YouTube video ID, and MP3 download link.
    """
    # Get the Spotify song ID from query parameters
    spotify_song_url = request.args.get('spotify_song_url')

    if not spotify_song_url:
        return jsonify({'error': 'Spotify song URL is required'}), 400

    # Extract the Spotify song ID from the URL
    try:
        spotify_song_id = spotify_song_url.split("/track/")[1].split("?")[0]
    except IndexError:
        return jsonify({'error': 'Invalid Spotify song URL'}), 400
    
    try:
        # Get song data from Spotify
        song_data = get_spotify_song_data(spotify_song_id)
        
        # Search for the song on YouTube and get the video ID
        video_id, video_url = search_youtube_for_song(song_data['song_name'])
        
        if video_id:
            song_data['youtube_video_id'] = video_id
            song_data['youtube_video_url'] = video_url
            
            # Get the MP3 download link
            mp3_download_link = get_mp3_download_link(video_id)
            if mp3_download_link:
                song_data['mp3_download_link'] = mp3_download_link
            
            return jsonify(song_data)
        else:
            return jsonify({'error': 'No YouTube video found for this song'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    # Get the dynamic port from the environment (Render or cloud providers)
    port = int(os.getenv('PORT', 5000))  # Default to 5000 if not provided
    app.run(debug=True, host='0.0.0.0', port=port)
