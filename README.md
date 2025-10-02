# 📓 Pocket Journal
A personal journaling application that helps users write journal entries, track moods, get summaries, generate insights, and receive media recommendations (movies, songs, books) based on their emotions.

## 🚀 Features
- 🔐 Firebase Authentication (signup/login with secure token verification)
- 📝 Journal Entry Creation & Retrieval (stored in Firestore)
- 😊 Mood Detection (sentence-level analysis using pre-trained model)
- ✍️ Text Summarization of journal entries
- 📊 Insight Generation from past entries (progress, remedies, behavior patterns, etc.)
- 🎬🎶📚 Personalized Recommendations:
  - Movies (via TMDB API)
  - Songs (via Spotify API)
  - Books (via Google Books API)

## 🛠️ Technologies Used

- Frontend: Flutter
- Backend: Python (Flask)
- Database: Firebase Firestore
- Authentication: Firebase Authentication
- NLP/ML: Transformers (Hugging Face), Torch, Scikit-learn
- Recommendations: TMDB API, Spotify API, Google Books API
- LangChain & Gemini AI for insights generation

## 📂 Project Structure
```bash
pocket-journal/
├── Backend/
│   ├── app.py                        # Main Flask app
│   ├── requirements.txt
│   ├── pocket-journal-be-firebase-adminsdk.json  # Firebase credentials
│   ├── gen-lang-client-XXXX.json      # Gemini credentials
│   ├── song_history.json
│   ├── Media_Recommendation/          # Media recommendation module
│   │   ├── app.py
│   │   ├── books_recommendation.py
│   │   ├── mood_recommend.py
│   │   ├── movie_search.py
│   │   ├── search_books.py
│   │   ├── search_song.py
│   │   ├── song_recommend.py
│   │   ├── song_history.json
│   │   └── __pycache__/
│   │
│   ├── Mood_Detection/                # Mood detection & NLP module
│   │   ├── app.py
│   │   ├── main.py
│   │   ├── train_mood_sentence.py
│   │   ├── analysis/
│   │   │   └── insight_analyzer.py
│   │   ├── database/
│   │   │   └── db_manager.py
│   │   ├── data/                      # Datasets
│   │   ├── embeddings/                # Embedding storage
│   │   ├── mood_detection_sentence/
│   │   │   ├── config_sentence.py
│   │   │   ├── dataset_loader.py
│   │   │   ├── predictor_sentence_level.py
│   │   │   ├── trainer_sentence.py
│   │   │   ├── evaluator_sentence_level.py
│   │   │   └── visualizer.py
│   │   ├── outputs/                   # Model checkpoints, logs
│   │   └── summarization/
│   │       ├── summarizer.py
│   │       ├── trainer.py
│   │       ├── config.py
│   │       └── dataset_loader.py
│   │
│   └── venv/                          # Python virtual environment
│
├── Frontend/
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/
│   │   ├── widgets/
│   │   └── services/
```

## ⚙️ Setup Instructions
1️⃣ Clone the Repository
```bash
git clone https://github.com/Jenil7828/pocket-journal.git
cd pocket-journal
```
2️⃣ Backend Setup
```bash
cd Backend
python -m venv venv
source venv/bin/activate   # (Linux/Mac)
venv\Scripts\activate      # (Windows)
pip install -r requirements.txt
```
3️⃣ Firebase Setup
```bash
Create a Firebase project.
Enable Authentication (Email/Password or Google Sign-in).
Enable Cloud Firestore.
Download your Service Account JSON and set the path in .env.
```
4️⃣ Environment Variables
```bash
Create a .env file inside Backend/:

# Firebase
FIREBASE_CREDENTIALS_PATH=serviceAccount.json

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key
GEMINI_CREDENTIALS_PATH=path_to_gemini_service.json

# External APIs
TMDB_API_KEY=your_tmdb_key
SONG_ID=your_spotify_client_id
SONG_SECRET=your_spotify_client_secret
```
5️⃣ Run the Flask App
```bash
python app.py
```

## Server will run at:

Local: 
```bash 
http://127.0.0.1:5000
```

LAN:
```bash
 http://192.168.1.33:5000
```

## 📡 API Endpoints
- 🔑 Authentication
 - All endpoints require
 ```  bash
  Authorization: Bearer <Firebase_ID_Token> in headers.
  ```

- 📝 Journal APIs
  - Process Journal Entry

  ``` bash
  POST /process_entry
  Authorization: Bearer <token>
  Content-Type: application/json
  {
    "entry_text": "Today was amazing, I had a great time with friends."
  }
  ```

  - ✅ Returns: entry_id, summary, mood_probs

- Generate Insights
```bash
POST /generate_insights
Authorization: Bearer <token>
Content-Type: application/json

{
  "start_date": "2025-09-01",
  "end_date": "2025-09-30"
}
```
  - ✅ Returns: AI-generated insights + fetched entries (for debugging).

- 🎬 Movies
  - By Mood
``` bash
GET /api/recommend?mood=happy
Authorization: Bearer <token>
```
  - Search
``` bash
GET /api/search?movie=Inception
Authorization: Bearer <token>
```
- 🎶 Songs
  - By Mood
``` bash
GET /api/songs?mood=sad&language=english&limit=5
Authorization: Bearer <token>
```
  - Search
``` bash
GET /api/search_song?q=Arijit Singh&type=artist&limit=10
Authorization: Bearer <token>
```
- 📚 Books
  - By Emotion
``` bash
GET /api/books?emotion=stressed&limit=5
Authorization: Bearer <token>
```
  - Search
``` bash
GET /api/search_books?query=Harry Potter&type=both&limit=5
Authorization: Bearer <token>
```

## 🧪 Example Postman Collection
- Import the above endpoints into Postman.
- Add a variable {{token}} for Authorization.
- Get Firebase ID Token after login and set it as {{token}}.

## 📌 Notes

- Ensure Firebase and APIs are enabled.
- Models for summarization & mood detection may need initial downloads.
- Firestore stores:
  - journal_entries → {entry_id, user_id, entry_text, created_at}
  - entry_analysis → {entry_id, summary, mood}

## 👨‍💻 Contributors
- Jenil Rathod
- Manas Joshi
- Saloni Naik
- Aditya Nalla

## 📜 License
MIT License – Free to use and modify.
