# **POCKET JOURNAL — BACKEND (QUICK START)**

This short README covers only the essential developer steps to:
- Clone the repository
- Set up the Python backend environment
- Run the server locally using `app.py`
- Build and run the production Docker image

Keep this file focused — detailed developer notes and architecture live in the project docs.

### **REPOSITORY FOLDER STRUCTURE (TOP-LEVEL)**
```
pocket-journal/
├── LICENSE
├── Model_Training_Result_RoBERTa.txt
├── Pocket Journal API Collection.postman_collection.json
├── README.md
├── Backend/
│   ├── __init__.py
│   ├── app.py
│   ├── Docker.md
│   ├── Dockerfile.prod
│   ├── docker-compose.prod.yml
│   ├── requirements.prod.txt
│   ├── requirements.train.txt
│   ├── utils.py
│   ├── ai_insights/
│   │   ├── __init__.py
│   │   ├── gaurds.py
│   │   ├── insight_analyzer.py
│   │   └── prompts/
│   │       └── journal_insights.txt
│   ├── data/
│   │   ├── mood_detection_data/
│   │   │   ├── summarization_dataset.jsonl
│   │   │   └── (label subfolders...)
│   │   └── summarization_data/
│   │       └── summary.csv
│   ├── Media_Recommendation/
│   │   ├── app.py
│   │   ├── books_recommendation.py
│   │   ├── mood_recommend.py
│   │   ├── movie_search.py
│   │   ├── search_books.py
│   │   ├── search_song.py
│   │   ├── song_recommend.py
│   ├── ml/
│   │   └── mood_detection/
│   │       ├── inference/
│   │       │   └── mood_detection/roberta/   # predictor + config
│   │       ├── training/
│   │       │   ├── mood_detection/roberta/   # train.py, trainer
│   │       │   └── summarization/bart/       # train.py, trainer
│   │       └── models/                       # model artifacts
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── database_schema.py
│   │   └── db_manager.py
│   ├── secrets/
│   │   └── firebase-adminsdk.json
│   ├── services/
│   │   ├── entry_response.py
│   │   ├── entry_response_builder.py
│   │   ├── entry_response.py
│   │   ├── entry_response_builder.py
│   │   ├── entry_response.py
│   │   └── (many service modules...)
│   └── templates/
│       └── home.html
├── F/
│   └── diary/
│       ├── pubspec.yaml
│       ├── pubspec.lock
│       ├── android/
│       ├── ios/
│       ├── lib/
│       ├── web/
│       └── windows/
├── scripts/
│   └── db/
│       ├── add_updated_at_field.py
│       ├── database_manager.py
│       ├── reset_database.py
│       └── verify_database.py
```

### **PREREQUISITES**
- Git
- Python 3.10+ (or the version in `Backend/requirements.txt`)
- pip
- Docker (for container run)

### **1) CLONE THE REPOSITORY**

```bash
git clone <repository-url> "pocket-journal"
cd "pocket-journal/Backend"
```

### **2) LOCAL SETUP (DEVELOPMENT)**

- Create and activate a virtual environment, then install dependencies:

```powershell
# Windows PowerShell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- Configure secrets/environment variables
  - Create a `.env` file (or set environment variables) in `Backend/` with the scalar secrets your environment needs (do not commit `.env`).
  - If you use JSON service account files (Firebase, etc.), mount or place them in a secure location and reference them via an environment variable like `FIREBASE_CREDENTIALS_PATH`.

### **3) RUN THE FLASK APP DIRECTLY**

- Start the server (models are expected to be available locally if required by your deployment):

```powershell
# from Backend/ with venv active
python app.py
```

- The server will start and listen on the configured host/port (default: `http://127.0.0.1:5000`) — check `Backend/app.py` for overrides.

### **4) BUILD AND RUN WITH DOCKER (PRODUCTION-STYLE)**

- Build the production image (uses `Dockerfile.prod`):

```powershell
# from repository root
docker build -f Backend/Dockerfile.prod -t pocket-journal:prod .
```

- Run the container (example PowerShell):

```powershell
docker run ^
  --env-file Backend/.env ^
  -v "%cd%\Backend\secrets:/app/secrets:ro" ^
  -v "%cd%\Backend\ml\mood_detection\models:/app/models:ro" ^
  -p 8080:8080 ^
  pocket-journal:prod
```

### **RUNNING WITH DOCKER COMPOSE (COMMAND ONLY)**
- From the repository root run:

```powershell
# PowerShell
docker-compose -f docker-compose.prod.yml up -d
```

> Note: The compose file `docker-compose.prod.yml` is present under `Backend/` — ensure you run the command from the repository root or adjust the path accordingly.

### **TRAINING & DEVELOPMENT (HOW IT'S DONE)**

This project separates production inference (the running backend) from model training. Training is performed offline using the training scripts present under `Backend/ml/mood_detection/training/...` and uses a separate training dependency set.

Where training code lives and how to run it:
- Mood detection training (RoBERTa)
  - Script: `Backend/ml/mood_detection/training/mood_detection/roberta/train.py`
  - Run example:

```powershell
# from repository root (or adjust path)
cd Backend
python ml/mood_detection/training/mood_detection/roberta/train.py
```

- Summarizer training (BART)
  - Script: `Backend/ml/mood_detection/training/summarization/bart/train.py`
  - Run example:

```powershell
cd Backend
python ml/mood_detection/training/summarization/bart/train.py
```

Training environment setup:

```powershell
# from Backend/
python -m venv venv-train
venv-train\Scripts\activate
pip install -r requirements.train.txt
```

- Training scripts will write model artifacts to `Backend/ml/mood_detection/models/` or `Backend/ml/mood_detection/outputs/` as configured by each trainer.
- Use Git LFS for storing or distributing large model artifacts. Do not check large model binaries into regular Git history.

Development workflow
- Run the Flask app locally for API development. Ensure models are present under `Backend/ml/mood_detection/models/...` (or the path expected by the inference config) so the app can load them at startup.
- Unit tests and quick checks:
  - There is a `Backend/test_roberta_and_builder.py` test file for validating model + builder behaviour locally — run it using your test runner or `python -m pytest` from `Backend/`.

### **SAMPLE `.env` (Backend/.env)**

Create `Backend/.env` (do NOT commit) with scalar keys referenced by the app and the compose file. Example values below are placeholders—replace with your real secrets or set them as host env vars.

```ini
# Firebase service account path inside container (matches docker-compose mapping)
FIREBASE_CREDENTIALS_PATH=/app/secrets/pocket-journal-be-firebase-adminsdk.json

# Short scalar secrets (API keys)
GEMINI_API_KEY=your_gemini_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here

# App configuration
FLASK_ENV=production
# Optional: PORT to bind inside container (if app.py reads it)
PORT=8080
```

### **NOTES AND TIPS**
- Do not commit `.env` or service account JSONs to source control.
- Ensure required model artifacts are present before starting the server in production.
- This README is intentionally minimal — see project docs for architecture, storage contracts, and developer patterns.

### 👨‍💻 Contributors
- Jenil Rathod
- Manas Joshi
- Saloni Naik
- Aditya Nalla

### **LICENSE**
MIT License. See `LICENSE` file in repository root.
