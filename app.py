import os
import requests
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from flask import Flask, request, jsonify, Response, send_file
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from flask_cors import CORS
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Spotify API credentials - Use environment variables for security
CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '6fa6c92cdbf64239a09f921a2e7ef207')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '3cb7b2afdf12457f9d8843d58f4c8ae5')
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '3dab8d0338msh860dc1baf2f6e9bp1a3029jsna4a66ccdd07d')

# Initialize Spotify API client with retry strategy
sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET),
    retries=3,
    backoff_factor=0.3
)

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size
app.config['JSON_SORT_KEYS'] = False  # Maintain JSON key order

# Enable CORS for all routes and origins (you can restrict this later as needed)
CORS(app)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'Request too large'}), 413

# Configure requests session with connection pooling and retry strategy
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Global session for reuse
session = create_session()

# Cache for YouTube search results (24 hour TTL)
youtube_search_cache = {}
CACHE_TTL = 24 * 60 * 60  # 24 hours in seconds

@lru_cache(maxsize=1000)
def search_youtube_for_song(song_name):
    """
    Perform a search on YouTube (including YouTube Music) using yt-dlp's built-in search functionality.
    Uses caching to avoid repeated searches for the same song.
    """
    # Check cache first
    cache_key = f"yt_search:{song_name}"
    current_time = time.time()
    
    if cache_key in youtube_search_cache:
        cache_entry = youtube_search_cache[cache_key]
        if current_time - cache_entry['timestamp'] < CACHE_TTL:
            return cache_entry['video_id'], cache_entry['url']
    
    search_query = song_name
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'socket_timeout': 30,
        # Anti-bot measures
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'extractor_args': {
            'youtube': {
                'skip': ['dash', 'hls'],
                'player_skip': ['js'],
                'player_client': ['web'],
            }
        },
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch:{search_query}", download=False)

            if 'entries' in result and result['entries']:
                video_id = result['entries'][0]['id']
                url = result['entries'][0]['url']
                
                # Cache the result
                youtube_search_cache[cache_key] = {
                    'video_id': video_id,
                    'url': url,
                    'timestamp': current_time
                }
                
                return video_id, url
            else:
                print(f"No results found for '{song_name}' on YouTube.")
                return None, None
    except Exception as e:
        print(f"Error searching YouTube for '{song_name}': {str(e)}")
        return None, None

@lru_cache(maxsize=1000)
def get_spotify_song_data(song_id):
    """
    Fetch song data (name, artist, album) from Spotify using the song ID.
    Uses caching to avoid repeated API calls for the same track.
    """
    if not song_id:
        return {'error': 'Invalid song ID', 'message': 'Song ID cannot be empty'}
    
    try:
        # Fetch the song details using the Spotify track ID
        track = sp.track(song_id)
        
        if not track:
            return {'error': 'Track not found', 'message': 'The specified track could not be found'}
        
        # Extract basic information with safe access
        song_name = track.get('name', 'Unknown')
        artist_name = track['artists'][0]['name'] if track.get('artists') else 'Unknown Artist'
        album_name = track['album']['name'] if track.get('album', {}).get('name') else 'Unknown Album'
        
        # Album cover with safe access
        album_images = track.get('album', {}).get('images', [])
        album_cover = album_images[0]['url'] if album_images else ''

        # Handle missing genre information gracefully
        album_genres = track.get('album', {}).get('genres', [])
        genre = album_genres[0] if album_genres else 'Unknown'

        # Extract other metadata with safe access
        release_date = track.get('album', {}).get('release_date', '')
        release_year = release_date[:4] if release_date else 'Unknown'
        
        isrc = track.get('external_ids', {}).get('isrc', 'Unknown')
        
        # Handle copyrights safely
        copyrights = track.get('copyrights', [])
        copyright_info = copyrights[0]['text'] if copyrights else 'No copyright information'
        
        track_number = track.get('track_number', 'Unknown')
        duration_ms = track.get('duration_ms', 0)
        
        # Format duration as mm:ss
        if duration_ms > 0:
            minutes = duration_ms // 60000
            seconds = (duration_ms % 60000) // 1000
            duration = f"{minutes}:{seconds:02d}"
        else:
            duration = "0:00"

        # Build the song data object
        song_data = {
            'song_name': song_name,
            'artist_name': artist_name,
            'album_name': album_name,
            'album_cover': album_cover,
            'genre': genre,
            'release_year': release_year,
            'isrc': isrc,
            'copyright_info': copyright_info,
            'track_number': track_number,
            'duration': duration,
        }

        return song_data

    except spotipy.exceptions.SpotifyException as e:
        return {'error': f'Spotify API error: {str(e)}', 'message': 'An error occurred while fetching song data from Spotify.'}
    except Exception as e:
        return {'error': str(e), 'message': 'An unexpected error occurred while fetching song data.'}

@lru_cache(maxsize=500)
def get_mp3_download_link(video_id):
    """
    Function to retrieve an MP3 download link from a third-party source.
    Downloads the MP3 file from the YouTube MP3 download API.
    Uses caching and improved error handling.
    """
    if not video_id:
        return None
    
    # API URL to fetch the MP3 download link
    url = f'https://youtube-mp36.p.rapidapi.com/dl?id={video_id}'
    
    headers = {
        'x-rapidapi-host': 'youtube-mp36.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
    }

    try:
        # Send the GET request with timeout and session
        response = session.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            
            # Log the full response for debugging (only in development)
            if app.debug:
                print(f"Full API Response: {data}")
            
            if "link" in data:
                return data['link']
            else:
                print("No 'link' found in API response.")
                return None
        elif response.status_code == 429:
            print("Rate limit exceeded. Please try again later.")
            return None
        else:
            print(f"API Error: {response.status_code}")
            if app.debug:
                print(f"Response Body: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("Request timeout while fetching MP3 download link")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None


def process_single_track(track_item, is_playlist=False):
    """
    Process a single track - get Spotify data and YouTube video ID.
    Used for parallel processing of albums and playlists.
    """
    try:
        # Extract song ID based on whether it's from a playlist or album
        song_id = track_item['track']['id'] if is_playlist else track_item['id']
        
        if not song_id:
            return {'error': 'Invalid track ID'}
        
        song_data = get_spotify_song_data(song_id)
        
        if 'error' not in song_data:
            # Search YouTube for the song and get the video ID
            video_id, video_url = search_youtube_for_song(
                f"{song_data['artist_name']} {song_data['song_name']}"
            )
            if video_id:
                song_data['youtube_video_id'] = video_id
                song_data['youtube_video_url'] = video_url
        
        return song_data
        
    except Exception as e:
        return {'error': str(e), 'message': 'Error processing track'}


def process_tracks_parallel(tracks, is_playlist=False, max_workers=10):
    """
    Process multiple tracks in parallel using ThreadPoolExecutor.
    """
    results = []
    
    # Limit the number of workers to avoid overwhelming APIs
    actual_workers = min(max_workers, len(tracks), 10)
    
    with ThreadPoolExecutor(max_workers=actual_workers) as executor:
        # Submit all tasks
        future_to_track = {
            executor.submit(process_single_track, track, is_playlist): track 
            for track in tracks
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_track):
            try:
                result = future.result(timeout=30)  # 30 second timeout per track
                results.append(result)
            except Exception as e:
                print(f"Error processing track: {str(e)}")
                results.append({'error': str(e), 'message': 'Track processing failed'})
    
    return results


def validate_spotify_url(url):
    """
    Validate and extract information from Spotify URLs.
    Returns tuple: (url_type, spotify_id) or (None, None) if invalid.
    """
    if not url or not isinstance(url, str):
        return None, None
    
    # Spotify URL patterns
    patterns = {
        'track': r'https://open\.spotify\.com/track/([a-zA-Z0-9]+)',
        'album': r'https://open\.spotify\.com/album/([a-zA-Z0-9]+)',
        'playlist': r'https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)'
    }
    
    for url_type, pattern in patterns.items():
        match = re.search(pattern, url)
        if match:
            return url_type, match.group(1)
    
    return None, None


def validate_youtube_video_id(video_id):
    """
    Validate YouTube video ID format.
    """
    if not video_id or not isinstance(video_id, str):
        return False
    
    # YouTube video IDs are typically 11 characters long
    pattern = r'^[a-zA-Z0-9_-]{11}$'
    return re.match(pattern, video_id) is not None


@app.route('/get-music-details', methods=['GET'])
def get_music_details():
    """
    General endpoint to fetch track, album, or playlist details, YouTube video ID, and MP3 download links.
    """
    # Get the URL from query parameters
    spotify_url = request.args.get('spotify_url')

    if not spotify_url:
        return jsonify({'error': 'Spotify URL is required'}), 400

    # Validate and parse the Spotify URL
    url_type, spotify_id = validate_spotify_url(spotify_url)
    
    if not url_type or not spotify_id:
        return jsonify({'error': 'Invalid Spotify URL format'}), 400

    # Process based on URL type
    if url_type == 'track':
        try:
            track_data = get_spotify_song_data(spotify_id)

            if 'error' not in track_data:
                # Search YouTube for the song and get the video ID
                video_id, video_url = search_youtube_for_song(
                    f"{track_data['artist_name']} {track_data['song_name']}"
                )
                if video_id:
                    track_data['youtube_video_id'] = video_id
                    track_data['youtube_video_url'] = video_url

            return jsonify([track_data])

        except spotipy.exceptions.SpotifyException as e:
            return jsonify({'error': f'Spotify API error: {str(e)}'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif url_type == 'album':
        try:
            # Fetch the album's tracks
            album_tracks = sp.album_tracks(spotify_id)

            # Check if the album contains any tracks
            if 'items' not in album_tracks or not album_tracks['items']:
                return jsonify({'error': 'No tracks found in this album'}), 404

            # Process tracks in parallel for better performance
            album_data = process_tracks_parallel(album_tracks['items'], is_playlist=False)

            return jsonify(album_data)

        except spotipy.exceptions.SpotifyException as e:
            return jsonify({'error': f'Spotify API error: {str(e)}'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif url_type == 'playlist':
        try:
            playlist_tracks = sp.playlist_tracks(spotify_id)

            # Check if the playlist contains any tracks
            if 'items' not in playlist_tracks or not playlist_tracks['items']:
                return jsonify({'error': 'No tracks found in this playlist'}), 404

            # Process tracks in parallel for better performance
            playlist_data = process_tracks_parallel(playlist_tracks['items'], is_playlist=True)

            return jsonify(playlist_data)

        except spotipy.exceptions.SpotifyException as e:
            return jsonify({'error': f'Spotify API error: {str(e)}'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': f'Unsupported URL type: {url_type}'}), 400

@app.route('/get-music-download', methods=['GET'])
def get_mp3_download():
    """Fetch the MP3 download link using RapidAPI."""
    video_id = request.args.get('video_id')
    
    if not video_id:
        return jsonify({'error': 'Video ID is required'}), 400
    
    if not validate_youtube_video_id(video_id):
        return jsonify({'error': 'Invalid YouTube video ID format'}), 400
    
    try:
        mp3_download_link = get_mp3_download_link(video_id)
        if mp3_download_link:
            return jsonify({'mp3_download_link': mp3_download_link})
        return jsonify({'error': 'MP3 download link not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'cache_size': len(youtube_search_cache)
    })


@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all caches."""
    try:
        # Clear function caches
        search_youtube_for_song.cache_clear()
        get_spotify_song_data.cache_clear()
        get_mp3_download_link.cache_clear()
        
        # Clear YouTube search cache
        youtube_search_cache.clear()
        
        return jsonify({'message': 'All caches cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    
    print(f"Starting Spotify Downloader API on port {port}")
    print(f"Debug mode: {debug_mode}")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port, threaded=True)
