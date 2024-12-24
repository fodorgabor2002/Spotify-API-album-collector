import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
import json
import os
import requests
from urllib.parse import urlparse
import time


def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


def download_image(url, path, retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 OPR/96.0.0.0'
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=10, allow_redirects=True)
            response.raise_for_status()  # Trigger an error for bad status codes
            with open(path, 'wb') as out_file:
                for chunk in response.iter_content(chunk_size=8192):
                    out_file.write(chunk)
            print(f"Saved album cover: {path}")
            return True

        except requests.exceptions.RequestException as req_err:
            print(f"Attempt {attempt+1} failed: {req_err}")
            time.sleep(2)  # Wait before retrying

    print(f"Failed to download {url} after {retries} attempts.")
    return False


# Load credentials from the JSON file
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Authenticate using credentials from JSON
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=config["client_id"],
    client_secret=config["client_secret"],
    redirect_uri=config["redirect_uri"],
    scope="user-follow-read playlist-read-private",
    open_browser=True  # Ensures a browser window opens for login
))

current_year = str(datetime.now().year)
all_releases_folder = f"releases_{current_year}"
albums_folder = f"albums_{current_year}"
os.makedirs(all_releases_folder, exist_ok=True)
os.makedirs(albums_folder, exist_ok=True)

new_albums = {}

# Fetch followed artists (handling pagination)
def get_followed_artists():
    artists = set()
    results = sp.current_user_followed_artists(limit=50)
    while results:
        for artist in results['artists']['items']:
            artists.add((artist['id'], artist['name']))
        if results['artists']['next']:
            results = sp.next(results['artists'])
        else:
            break
    return artists

followed_artists = get_followed_artists()

# Check new albums from followed artists
for artist_id, artist_name in followed_artists:
    try:
        artist_albums = sp.artist_albums(artist_id, album_type='album')
        for album in artist_albums['items']:
            release_date = album['release_date']
            if release_date.startswith(current_year):
                album_name = album['name']
                album_key = f"{album_name} by {artist_name}"

                if album_key not in new_albums:
                    new_albums[album_key] = {
                        "name": album_name,
                        "artist": artist_name,
                        "release_date": release_date,
                        "url": album['external_urls']['spotify'],
                        "image_url": album['images'][0]['url'],  # Album cover URL
                        "total_tracks": album['total_tracks']
                    }
    except Exception as e:
        print(f"Error getting albums for artist {artist_name}: {e}")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 OPR/96.0.0.0'
}
# Improved download and save album covers
for album_key, album in new_albums.items():
    try:
        image_url = album['image_url']
        image_filename = f"{album['artist']} - {album['name']}.jpg"
        image_path = os.path.join(all_releases_folder, image_filename)

        if is_valid_url(image_url):
            download_image(image_url, image_path)
        else:
            print(f"Invalid URL: {image_url}")
        
        response = requests.get(image_url, headers=headers, stream=True, timeout=10, allow_redirects=True)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Text: {response.text}")

        with open(image_path, 'wb') as out_file:
            for chunk in response.iter_content(chunk_size=8192):
                out_file.write(chunk)

        # Save only full albums
        if album["total_tracks"] > 1:
            album_path = image_path.replace(all_releases_folder, albums_folder)
            with open(album_path, 'wb') as out_file:
                for chunk in response.iter_content(chunk_size=8192):
                    out_file.write(chunk)

        print(f"Saved album cover: {image_path}")

    except requests.exceptions.RequestException as req_err:
        print(f"Request error while downloading cover for {album_key}: {req_err}")

    except OSError as os_err:
        print(f"File error while saving cover for {album_key}: {os_err}")

    except Exception as e:
        print(f"Unexpected error while processing {album_key}: {e}")

# Display results
if new_albums:
    print(f"\nNew albums from {current_year} by artists you follow:")
    for album_key, album in new_albums.items():
        print(f"{album['name']} by {album['artist']} (Released: {album['release_date']})")
        print(f"Link: {album['url']}\n")
else:
    print(f"No new albums from {current_year} found by artists you follow.")
