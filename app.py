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
        return {'error': str(e), 'message': 'An error occurred while fetching song data from Spotify.'}

def get_mp3_download_link(video_id):
    """
    Function to retrieve an MP3 download link from a third-party source.
    Downloads the MP3 file from the YouTube MP3 download API.
    """
    # API URL to fetch the MP3 download link
    url = f'https://youtube-mp36.p.rapidapi.com/dl?id={video_id}'
    
    headers = {
        'x-rapidapi-host': 'youtube-mp36.p.rapidapi.com',
        'x-rapidapi-key': '3dab8d0338msh860dc1baf2f6e9bp1a3029jsna4a66ccdd07d'
    }

    # Send the GET request
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        
        # Log the full response for debugging
        print(f"Full API Response: {data}")
        
        if "link" in data:
            return data['link']
        else:
            print("No 'link' found in API response.")
    else:
        print(f"Error: {response.status_code}")
        print(f"Response Body: {response.text}")
    return None


@app.route('/get-music-details', methods=['GET'])
def get_music_details():
    """
    General endpoint to fetch track, album, or playlist details, YouTube video ID, and MP3 download links.
    """
    # Get the URL from query parameters
    spotify_url = request.args.get('spotify_url')

    if not spotify_url:
        return jsonify({'error': 'Spotify URL is required'}), 400

    # Identify whether the URL is a track, album, or playlist and extract the ID
    if 'track' in spotify_url:
        try:
            spotify_track_id = spotify_url.split("/track/")[1].split("?")[0]
            track_data = get_spotify_song_data(spotify_track_id)

            # Search YouTube for the song and get the video ID
            video_id, video_url = search_youtube_for_song(track_data['song_name'])
            if video_id:
                track_data['youtube_video_id'] = video_id
                track_data['youtube_video_url'] = video_url


            return jsonify([track_data])

        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif 'album' in spotify_url:
        try:
            # Fix: Extract album ID and remove any extra query parameters like 'highlight'
            spotify_album_id = spotify_url.split("/album/")[1].split("?")[0]

            # Fetch the album's tracks
            album_tracks = sp.album_tracks(spotify_album_id)

            # Check if the album contains any tracks
            if 'items' not in album_tracks or not album_tracks['items']:
                return jsonify({'error': 'No tracks found in this album'}), 404

            album_data = []
            for item in album_tracks['items']:
                song_id = item['id']
                song_data = get_spotify_song_data(song_id)
                
                # Search YouTube for each song and get the video ID
                video_id, video_url = search_youtube_for_song(song_data['song_name'])
                if video_id:
                    song_data['youtube_video_id'] = video_id
                    song_data['youtube_video_url'] = video_url


                album_data.append(song_data)

            return jsonify(album_data)

        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif 'playlist' in spotify_url:
        try:
            spotify_playlist_id = spotify_url.split("/playlist/")[1].split("?")[0]
            playlist_tracks = sp.playlist_tracks(spotify_playlist_id)

            # Check if the playlist contains any tracks
            if 'items' not in playlist_tracks or not playlist_tracks['items']:
                return jsonify({'error': 'No tracks found in this playlist'}), 404

            playlist_data = []
            for item in playlist_tracks['items']:
                song_id = item['track']['id']
                song_data = get_spotify_song_data(song_id)
                
                # Search YouTube for each song and get the video ID
                video_id, video_url = search_youtube_for_song(song_data['song_name'])
                if video_id:
                    song_data['youtube_video_id'] = video_id
                    song_data['youtube_video_url'] = video_url

                playlist_data.append(song_data)

            return jsonify(playlist_data)

        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Invalid Spotify URL type (track, album, or playlist required)'}), 400

@app.route('/get-music-download', methods=['GET'])
def get_mp3_download():
    """Fetch the MP3 download link."""
    video_id = request.args.get('video_id')
    if not video_id:
        return jsonify({'error': 'Video ID is required'}), 400
    try:
        mp3_download_link = get_mp3_download_link(video_id)
        if mp3_download_link:
            return jsonify({'mp3_download_link': mp3_download_link})
        return jsonify({'error': 'MP3 download link not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
