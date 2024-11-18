import logging
from flask import Flask, jsonify
import yt_dlp
from flask_cors import CORS
import os


# Initialize Flask app
app = Flask(__name__)

# Enable CORS for the app
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcoded cookie data in Netscape format (replace with your actual cookie data)
COOKIE_DATA_NETSCP = """
payments.youtube.com	FALSE	/	TRUE	TRUE	S	billing-ui-v3=gfBsDJfUKUd5R_E07yr2QV3p-CC-c4Ug:billing-ui-v3-efe=gfBsDJfUKUd5R_E07yr2QV3p-CC-c4Ug
.youtube.com	FALSE	/	TRUE	TRUE	SOCS	CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwODI5LjA3X3AxGgJlbiADGgYIgJnPpwY
.youtube.com	FALSE	/	FALSE	FALSE	HSID	AyIPMRbMm6_6oJYjo
.youtube.com	FALSE	/	FALSE	TRUE	SSID	AOy9ERY5qG3Ia0mc4
.youtube.com	FALSE	/	FALSE	FALSE	APISID	tkVWyN1kLnXFFRZf/A_Ri2zl6hJtAHnDm6
.youtube.com	FALSE	/	FALSE	TRUE	SAPISID	6ikH0r55AJQG1al6/AdmgkxDe7ycn1gml2
.youtube.com	FALSE	/	FALSE	TRUE	__Secure-1PAPISID	6ikH0r55AJQG1al6/AdmgkxDe7ycn1gml2
.youtube.com	FALSE	/	FALSE	TRUE	__Secure-3PAPISID	6ikH0r55AJQG1al6/AdmgkxDe7ycn1gml2
www.youtube.com	FALSE	/	FALSE	TRUE	ig_did	0C826C21-17C3-444A-ABB7-EBABD37214D7
.youtube.com	FALSE	/	FALSE	TRUE	VISITOR_PRIVACY_METADATA	CgJJThIEGgAgRw%3D%3D
.youtube.com	FALSE	/	FALSE	FALSE	SID	g.a000qQimVw1frlnwT0r0Fu_yeJM4GqK6SURLh6vopdowoKyxjWUzrbFMnQMRGf0zvbs5cMdYqAACgYKARUSARMSFQHGX2MiUl4PoPvSJV9cvtdywkGsDRoVAUF8yKqcaIHS5GnFsVjuC22G2NmD0076
.youtube.com	FALSE	/	FALSE	TRUE	__Secure-1PSID	g.a000qQimVw1frlnwT0r0Fu_yeJM4GqK6SURLh6vopdowoKyxjWUz0E57-_jnOC8oUyHS5PuRtwACgYKAeASARMSFQHGX2Mi17i7Di0Y4VdfBcxmvBf1axoVAUF8yKrspD18l0N9S6TgRUkM7EdI0076
.youtube.com	FALSE	/	FALSE	TRUE	__Secure-3PSID	g.a000qQimVw1frlnwT0r0Fu_yeJM4GqK6SURLh6vopdowoKyxjWUz3b-51xXlzPct3--Wt8uPIgACgYKAd0SARMSFQHGX2Mi7EJ7OfPBRGAJytDksZYNfhoVAUF8yKpSVCj42HBoKPpD8xDoDYET0076
.youtube.com	FALSE	/	FALSE	TRUE	PREF	f6=40000000&f7=4140&tz=Asia.Calcutta&f4=4000000&f5=30000&repeat=NONE&autoplay=true
www.youtube.com	FALSE	/	TRUE	TRUE	S	billing-ui-v3=gfBsDJfUKUd5R_E07yr2QV3p-CC-c4Ug:billing-ui-v3-efe=gfBsDJfUKUd5R_E07yr2QV3p-CC-c4Ug
.youtube.com	FALSE	/	FALSE	TRUE	__Secure-1PSIDTS	sidts-CjIBQT4rX-zMtUDBR9p4BU7_OTpdCJyxYA1zW-zOGbnylSmwJMjcuSD89C2sYYCJADLghRAA
.youtube.com	FALSE	/	FALSE	TRUE	__Secure-3PSIDTS	sidts-CjIBQT4rX-zMtUDBR9p4BU7_OTpdCJyxYA1zW-zOGbnylSmwJMjcuSD89C2sYYCJADLghRAA
.youtube.com	FALSE	/	FALSE	TRUE	LOGIN_INFO	AFmmF2swRAIgB6aGrJdQZpTeqQKDacsrEw5qWpetHTcpBjfk1bmNxpgCIG_6ekm4IKAnBiq60LQ1e_-1alABsoPZ8utgfyaUa_7E:QUQ3MjNmeV9RZHVXQUloSXo1M1RoTHJobzJmNUluOXVEbXV4VmpzSjdONVV5YTdLYzJTR3hqWUZJVG5uVHBfVkVycW5PejJJTkViRFNnOG9SQzJMdHRVMlBFcHJsR0hyTXVFRnh3Q2RabTNfVkZXdUU3Q3pxX3h3cUN0Sm1zdExYQTA5NEkwMnFvczNXX2NvMWpFenpVN2pTRFdJYzR0eFV0cF9DVEszSkR6Ym5iOW9ldWNKZUZ0c2cyM0tZZk9GSDgyNzBUanJTeXBFaVBuLTh4aUhYel9SYWJvbzM5M2s5Zw==
.youtube.com	FALSE	/	FALSE	FALSE	ST-3opvp5	session_logininfo=AFmmF2swRAIgB6aGrJdQZpTeqQKDacsrEw5qWpetHTcpBjfk1bmNxpgCIG_6ekm4IKAnBiq60LQ1e_-1alABsoPZ8utgfyaUa_7E%3AQUQ3MjNmeV9RZHVXQUloSXo1M1RoTHJobzJmNUluOXVEbXV4VmpzSjdONVV5YTdLYzJTR3hqWUZJVG5uVHBfVkVycW5PejJJTkViRFNnOG9SQzJMdHRVMlBFcHJsR0hyTXVFRnh3Q2RabTNfVkZXdUU3Q3pxX3h3cUN0Sm1zdExYQTA5NEkwMnFvczNXX2NvMWpFenpVN2pTRFdJYzR0eFV0cF9DVEszSkR6Ym5iOW9ldWNKZUZ0c2cyM0tZZk9GSDgyNzBUanJTeXBFaVBuLTh4aUhYel9SYWJvbzM5M2s5Zw%3D%3D
.youtube.com	FALSE	/	FALSE	FALSE	SIDCC	AKEyXzX8KsS3GT-8xORhmv_R5kC4cUI4kevgoJSu12xQO4aEoR-elOWjcl9pGJqEf3rYkAddL2c
.youtube.com	FALSE	/	FALSE	TRUE	__Secure-1PSIDCC	AKEyXzUYf7EqFecbGElvgH_HW_XnKnk0MttlRvcstFzEMn4cEHNgvu8iMco7okV31-YTOblzZek
.youtube.com	FALSE	/	FALSE	TRUE	__Secure-3PSIDCC	AKEyXzVEOPsyb-LKRhG57uekiCy73LN5h93b4R9APzx3UNTRuZBvOZs-D9ESqyvHjGSXa_iONlc
"""

# Convert the Netscape cookie format into a list of dictionaries for yt-dlp
def parse_netscape_cookie(cookie_data):
    cookies = []
    for line in cookie_data.strip().split('\n'):
        parts = line.split('\t')
        if len(parts) != 7:
            continue  # Skip malformed lines
        
        domain, flag, path, secure, expiration, name, value = parts
        cookie = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
        }
        cookies.append(cookie)
    
    return cookies

# Log the cookies for debugging (ensure no sensitive data is exposed)
logger.info(f"Using hardcoded cookies: {COOKIE_DATA_NETSCP}")

# Function to verify the YouTube cookie using hardcoded cookie data
def verify_youtube_cookie(cookie_data):
    # Convert the raw Netscape cookie format into a list of dictionaries
    cookies = parse_netscape_cookie(cookie_data)
    
    # Step 2: Try downloading or extracting info using the cookies
    ydl_opts = {
        'cookies': cookies,  # Pass the parsed cookies
        'quiet': True,        # Silence the download process (we only want to check the cookie)
        'extract_flat': True, # Don't download, just extract metadata
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Example video to verify the cookie (using a public, not age-restricted YouTube video)
            test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'  # You can replace this with any YouTube URL
            result = ydl.extract_info(test_url, download=False)
            
            # If we successfully get the result, the cookie is valid
            if result:
                logger.info("Cookie data is valid. Successfully fetched video info.")
                return True
            else:
                logger.error("Failed to fetch video info using the hardcoded cookie data.")
                return False
    except Exception as e:
        logger.error(f"Error verifying cookie data: {e}")
        return False


# API endpoint to verify the YouTube cookie
@app.route('/verify-cookie', methods=['GET'])
def verify_cookie():
    # Log the received request (for debugging)
    logger.info(f"Received request to verify cookie data.")
    
    # Call the verify function with the hardcoded cookie data
    is_valid = verify_youtube_cookie(COOKIE_DATA_NETSCP)
    
    # Respond with the result
    if is_valid:
        logger.info("Cookie verification successful.")
        return jsonify({'message': 'Cookie data is valid.'}), 200
    else:
        logger.error("Cookie verification failed.")
        return jsonify({'error': 'Invalid cookie data.'}), 400


# Main entry point for the app
if __name__ == "__main__":
    # Get the dynamic port from the environment (Render or cloud providers)
    port = int(os.getenv('PORT', 5000))  # Default to 5000 if not provided
    logger.info(f"Starting app on port {port}...")
    app.run(debug=True, host='0.0.0.0', port=port)
