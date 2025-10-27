import os
import json
import random
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()
client_id = os.getenv("SONG_ID")
client_secret = os.getenv("SONG_SECRET")

# Spotify setup
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

HISTORY_FILE = "song_history.json"

# -------------------------------------------------------------------
# Mood → genre keywords
# -------------------------------------------------------------------
MOOD_KEYWORDS = {
    "happy": ["pop", "party", "dance", "feel good"],
    "sad": ["sad", "acoustic", "piano", "melancholy", "slow"],
    "chill": ["chill", "lofi", "relax", "ambient"],
    "romantic": ["love", "romantic", "r-n-b", "soft"],
    "energetic": ["rock", "edm", "hip-hop", "workout"]
}

# -------------------------------------------------------------------
# Main Function
# -------------------------------------------------------------------
def get_mood_songs(user_mood, limit=10, language="both"):
    """
    Returns a list of SONGS (tracks only) for the given mood.
    Uses Spotify search instead of recommendations (never 404s).
    """
    user_mood = user_mood.lower()
    if user_mood not in MOOD_KEYWORDS:
        return {"error": f"Unknown mood '{user_mood}'."}

    # Load or init history
    if not os.path.exists(HISTORY_FILE):
        song_history = {}
    else:
        try:
            with open(HISTORY_FILE, "r") as f:
                song_history = json.load(f)
        except:
            song_history = {}

    if user_mood not in song_history:
        song_history[user_mood] = []

    keywords = MOOD_KEYWORDS[user_mood]
    query = random.choice(keywords)
    print(f"🎵 Searching for mood='{user_mood}' using keyword='{query}'")

    try:
        results = sp.search(q=query, type="track", limit=limit * 2, market="IN")
        tracks = results.get("tracks", {}).get("items", [])
        random.shuffle(tracks)

        new_songs = []
        for track in tracks:
            tid = track["id"]
            if tid in song_history[user_mood]:
                continue

            name = track["name"]
            artist = track["artists"][0]["name"]

            new_songs.append({
                "song_name": name,
                "artist_name": artist,
                "spotify_link": track["external_urls"]["spotify"],
                "poster_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None
            })

            song_history[user_mood].append(tid)
            if len(new_songs) >= limit:
                break

        with open(HISTORY_FILE, "w") as f:
            json.dump(song_history, f, indent=4)

        if not new_songs:
            return {"message": "No new unique songs found. Try again!"}
        return new_songs

    except spotipy.exceptions.SpotifyException as e:
        return {"error": "Spotify API error", "details": str(e)}
    except Exception as e:
        return {"error": "Unknown error", "details": str(e)}

if __name__ == "__main__":
    mood = input("Enter mood (happy/sad/chill/romantic/energetic): ").strip().lower()
    songs = get_mood_songs(mood, limit=5)
    print(json.dumps(songs, indent=2, ensure_ascii=False))
