import requests

def recommend_books_by_emotion(emotion, limit=5):
    # Map emotions to subjects
    MOOD_BOOK_MAP = {
        "happy": ["comedy", "romance", "adventure"],
        "sad": ["self-help", "inspirational", "drama"],
        "angry": ["thriller", "mystery"],
        "romantic": ["romance", "poetry"],
        "stressed": ["philosophy", "mindfulness"],
        "bored": ["fantasy", "science_fiction"],
    }

    # Get subjects for the emotion
    subjects = MOOD_BOOK_MAP.get(emotion.lower(), ["fiction"])
    books = []

    # Fetch books from Open Library by subject
    for subject in subjects:
        url = f"https://openlibrary.org/subjects/{subject}.json?limit={limit}"
        response = requests.get(url).json()

        for work in response.get("works", []):
            books.append({
                "title": work.get("title"),
                "author": [a.get("name") for a in work.get("authors", [])],
                "cover": f"http://covers.openlibrary.org/b/id/{work['cover_id']}-M.jpg" if work.get("cover_id") else None,
                "openlibrary_url": f"https://openlibrary.org{work['key']}"
            })

    # Return limited number of books
    return books[:limit]

# -------------------------------
# Example test run
# -------------------------------
if __name__ == "__main__":
    emotion = "sad"   
    recommended = recommend_books_by_emotion(emotion, limit=5)

    print(f"\n📚 Book recommendations for emotion: {emotion}\n")
    for idx, book in enumerate(recommended, start=1):
        print(f"{idx}. {book['title']} by {', '.join(book['author']) if book['author'] else 'Unknown'}")
        print(f"   🔗 {book['openlibrary_url']}")
        if book['cover']:
            print(f"   🖼️ {book['cover']}")
        print()
