import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import random 
import os
from dotenv import load_dotenv
# 1️⃣ Authentication
load_dotenv()
client_id = os.getenv("SONG_ID")
client_secret = os.getenv("SONG_SECRET")

auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

# ----------------- History File -----------------
HISTORY_FILE = "song_history.json"
def get_mood_songs(user_mood, limit=10, language="both"):
    """
    Returns a list of song recommendations for the given mood and language.
    language: "english", "hindi", or "both"
    """
    # Load or initialize history
   

# Load or initialize history safely
    if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
        song_history = {}
    else:
        try:
            with open(HISTORY_FILE, "r") as f:
                song_history = json.load(f)
        except json.JSONDecodeError:
            # If file is corrupted or empty
            song_history = {}

    mood_queries = {
        "sad": "sad acoustic",
        "happy": "happy pop",
        "chill": "chill lofi",
        "energetic": "energetic rock",
        "romantic": "romantic r&b"
    }

    if user_mood not in mood_queries:
        return {"error": "Mood not recognized."}

    query = mood_queries[user_mood]

    if user_mood not in song_history:
        song_history[user_mood] = []

    # Random offset to get different songs
    random_offset = random.randint(0, 1000)
    results = sp.search(q=query, limit=20, type="track", offset=random_offset)

    tracks = results['tracks']['items']
    random.shuffle(tracks)

    # Filter out previously suggested songs
    new_songs = []
    for track in tracks:
        track_id = track['id']
        track_name = track['name'].lower()
        artist_name = track['artists'][0]['name'].lower()

        # Language filter
        if language == "english" and any(word in track_name for word in ["हिंदी", "bollywood"]) :
            continue
        if language == "hindi" and all(word not in track_name for word in ["हिंदी", "bollywood"]):
            continue

        if track_id not in song_history[user_mood]:
            new_songs.append(track)
            song_history[user_mood].append(track_id)

    # Reset history if all songs exhausted
    if not new_songs:
        song_history[user_mood] = []
        results = sp.search(q=query, limit=20, type="track", offset=random_offset)
        tracks = results['tracks']['items']
        random.shuffle(tracks)
        for track in tracks:
            track_id = track['id']
            if track_id not in song_history[user_mood]:
                new_songs.append(track)
                song_history[user_mood].append(track_id)

    # Save updated history
    with open(HISTORY_FILE, "w") as f:
        json.dump(song_history, f)

    # Prepare output
    output = []
    for track in new_songs[:limit]:
        item = {
            "song_name": track['name'],
            "artist_name": track['artists'][0]['name'],
            "spotify_link": track['external_urls']['spotify'],
            "poster_url": track['album']['images'][0]['url'] if track['album']['images'] else None
        }
        output.append(item)

    return output