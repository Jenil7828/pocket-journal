import requests
from rapidfuzz import process, fuzz

def search_books_robust(query, max_results=10, search_type="both"):

    query = query.strip()
    if not query:
        return {"error": "Query cannot be empty", "results": []}

    # Open Library search API
    url = "https://openlibrary.org/search.json"
    response = requests.get(url, params={"q": query, "limit": 50})
    
    if response.status_code != 200:
        return {"error": "Failed to fetch data from Open Library", "results": []}

    data = response.json()
    docs = data.get("docs", [])

    if not docs:
        return {"searched": query, "matched_term": None, "results": []}

    # Prepare list of possible terms for fuzzy matching
    if search_type == "title":
        candidates = [doc.get("title", "") for doc in docs]
    elif search_type == "author":
        candidates = [a for doc in docs for a in doc.get("author_name", [])]
    else:  # both
        candidates = [doc.get("title", "") for doc in docs] + [a for doc in docs for a in doc.get("author_name", [])]

    # Find best match using RapidFuzz
    best_match, score, _ = process.extractOne(query, candidates, scorer=fuzz.WRatio)

    # Filter docs containing best_match (case-insensitive)
    filtered_docs = []
    for doc in docs:
        title_match = best_match.lower() in doc.get("title", "").lower()
        author_match = any(best_match.lower() in a.lower() for a in doc.get("author_name", []))
        if title_match or author_match:
            filtered_docs.append(doc)

    # Prepare output
    results = []
    for doc in filtered_docs[:max_results]:
        results.append({
            "title": doc.get("title"),
            "authors": doc.get("author_name", []),
            "cover": f"http://covers.openlibrary.org/b/id/{doc['cover_i']}-M.jpg" if doc.get("cover_i") else None,
            "openlibrary_url": f"https://openlibrary.org{doc['key']}" if doc.get("key") else None
        })

    return {
        "searched": query,
        "matched_term": best_match,
        "results": results
    }


# -------------------------------
# Example test run
# -------------------------------
if __name__ == "__main__":
    search_query = "wiliam shakesphere"  # can type both book and author name
    results = search_books_robust(search_query, max_results=5, search_type="both")

    print(f"\n🔎 Search Results for: {search_query}")
    print(f"✅ Matched term: {results.get('matched_term')}\n")
    for idx, book in enumerate(results["results"], start=1):
        print(f"{idx}. {book['title']} by {', '.join(book['authors']) if book['authors'] else 'Unknown'}")
        print(f"   🔗 {book['openlibrary_url']}")
        if book['cover']:
            print(f"   🖼️ {book['cover']}")
        print()
