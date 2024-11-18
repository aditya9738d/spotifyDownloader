import os
import requests
import sys
from flask import Flask, request, jsonify
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp

# Spotify API credentials
CLIENT_ID = '6fa6c92cdbf64239a09f921a2e7ef207'
CLIENT_SECRET = '3cb7b2afdf12457f9d8843d58f4c8ae5'

# Initialize Spotify API client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

app = Flask(__name__)

def search_youtube_for_song(song_name):
    # Perform a search on YouTube (including YouTube Music) using yt-dlp's built-in search functionality
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
            return video_id
        else:
            print(f"No results found for '{song_name}' on YouTube.")
            return None

def get_spotify_song_data(song_id):
    # Fetch the song details using the Spotify track ID
    track = sp.track(song_id)
    song_name = track['name']
    artist_name = track['artists'][0]['name']
    album_name = track['album']['name']
    album_cover = track['album']['images'][0]['url']
    song_data = {
        'song_name': song_name,
        'artist_name': artist_name,
        'album_name': album_name,
        'album_cover': album_cover
    }
    return song_data

def get_mp3_download_link(song_name):
    """
    Function to retrieve an MP3 download link from a third-party source.
    For now, using a mock example URL (the one you provided).
    """
    # You can modify this to fetch dynamically from a service or database
    mp3_download_link = f'https://mbeta.123tokyo.xyz/get.php/1/49/_iktURk0X-A.mp3?cid=MmEwMTo0Zjg6YzAxMjozMmVlOjoxfE5BfERF&h=U2ysMxF2xlxC7uAjaHLugQ&s=1731937392&n=Phir%20Bhi%20Tumko%20Chaahunga%20-%20Full%20Song%20_%20Arijit%20Singh%20_%20Arjun%20K%20%26%20Shraddha%20K%20_%20Mithoon%2C%20Manoj%20K&uT=R&uN=YWRpdHlhOTczOA%3D%3D'
    
    # You could potentially integrate this with a third-party API or another method
    return mp3_download_link

@app.route('/get-song-details', methods=['GET'])
def get_song_details():
    # Get the Spotify song ID from query parameters
    spotify_song_id = request.args.get('spotify_song_id')

    if not spotify_song_id:
        return jsonify({'error': 'Spotify song ID is required'}), 400
    
    try:
        # Get song data from Spotify
        song_data = get_spotify_song_data(spotify_song_id)
        
        # Search for the song on YouTube and get the video ID
        video_id = search_youtube_for_song(song_data['song_name'])
        
        if video_id:
            song_data['youtube_video_id'] = video_id
            song_data['youtube_video_url'] = f'https://www.youtube.com/watch?v={video_id}'
            
            # Get the MP3 download link
            mp3_download_link = get_mp3_download_link(song_data['song_name'])
            song_data['mp3_download_link'] = mp3_download_link
            
            return jsonify(song_data)
        else:
            return jsonify({'error': 'No YouTube video found for this song'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
