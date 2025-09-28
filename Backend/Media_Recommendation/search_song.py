import requests
from rapidfuzz import process, fuzz

ITUNES_API = "https://itunes.apple.com/search"

def search_songs_or_artist(query, search_type="artist", limit=10):
    """
    Search songs by artist or song name with typo correction using RapidFuzz.
    """
    query = query.strip()
    search_type = search_type.lower()

    # Step 1: Fetch a wide pool (generic search, not exact misspelled query)
    params = {
        "term": query.split()[0],   # use first word as base
        "entity": "musicTrack" if search_type == "song" else "musicArtist",
        "limit": 200
    }
    response = requests.get(ITUNES_API, params=params)
    if response.status_code != 200:
        return {"error": "API request failed"}

    results = response.json().get("results", [])
    if not results:
        return {"error": "No results found"}

    if search_type == "artist":
        # Extract unique artist names
        artist_names = list({r["artistName"] for r in results if "artistName" in r})

        # Step 2: Fuzzy match
        best_match = process.extractOne(query, artist_names, scorer=fuzz.WRatio)
        if not best_match:
            return {"error": "No close artist match found"}

        matched_artist = best_match[0]

        # Step 3: Fetch songs of matched artist
        song_params = {
            "term": matched_artist,
            "entity": "musicTrack",
            "limit": limit
        }
        song_response = requests.get(ITUNES_API, params=song_params)
        song_results = song_response.json().get("results", [])

        songs = [
            {
                "artist_name": s["artistName"],
                "song_name": s["trackName"],
                "poster_url": s.get("artworkUrl100", ""),
                "preview_link": s.get("previewUrl", "")
            }
            for s in song_results
        ]

        return {"searched": query, "matched_artist": matched_artist, "results": songs}

    elif search_type == "song":
        # Extract song names
        song_names = [r["trackName"] for r in results if "trackName" in r]

        # Step 2: Fuzzy match
        best_match = process.extractOne(query, song_names, scorer=fuzz.WRatio)
        if not best_match:
            return {"error": "No close song match found"}

        matched_song = best_match[0]

        # Step 3: Collect matched tracks
        matched_tracks = [r for r in results if r.get("trackName") == matched_song]

        songs = [
            {
                "artist_name": s["artistName"],
                "song_name": s["trackName"],
                "poster_url": s.get("artworkUrl100", ""),
                "preview_link": s.get("previewUrl", "")
            }
            for s in matched_tracks[:limit]
        ]

        return {"searched": query, "matched_song": matched_song, "results": songs}
