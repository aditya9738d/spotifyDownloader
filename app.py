import os
import yt_dlp

def verify_youtube_cookie(cookie_file):
    # Step 1: Check if the cookie file exists
    if not os.path.exists(cookie_file):
        print(f"Cookie file '{cookie_file}' not found.")
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
                print(f"Cookie file '{cookie_file}' is valid. Successfully fetched video info.")
                return True
            else:
                print(f"Failed to fetch video info using the cookie file '{cookie_file}'.")
                return False
    except Exception as e:
        print(f"Error verifying cookie file: {e}")
        return False

# Example usage
cookie_file = 'youtube_cookies.txt'  # Replace with your actual cookie file path
if verify_youtube_cookie(cookie_file):
    print("Cookie verification succeeded!")
else:
    print("Cookie verification failed.")
