# **POCKET JOURNAL — AI-POWERED JOURNALING PLATFORM**

## **📖 PROJECT OVERVIEW**

**Pocket Journal** is a comprehensive, AI-powered digital journaling application that helps users reflect on their lives through intelligent mood detection, automated summarization, personalized media recommendations, and AI-generated insights.

### **Core Objectives:**
- 🎭 **Mood Detection**: Analyze journal entries to detect and categorize user emotions using transformer-based models (RoBERTa)
- 📝 **Automated Summarization**: Generate concise summaries of journal entries using BART models
- 🎬 **Media Recommendations**: Suggest movies and music based on detected moods and user preferences using multi-modal embeddings
- 💡 **AI Insights**: Generate personalized insights and reflections using Google Gemini and advanced NLP
- 📊 **Analytics & Stats**: Track mood patterns, entry frequency, and provide visual analytics
- 🔐 **Secure & Scalable**: Built with Firebase for authentication and data persistence
- 🚀 **Production-Ready**: Deployed with Docker, GPU support, and optimized for performance

This README covers:
- Project structure and folder descriptions
- Local setup (Python app.py)
- Docker deployment
- API documentation and Postman integration
- Notes, tips, and contributing guidelines

---

## **📁 REPOSITORY STRUCTURE & FOLDER DESCRIPTIONS**

```
pocket-journal/
├── Backend/                          # Flask REST API backend (main application)
│   ├── app.py                        # Entry point - Flask application server
│   ├── config.yml                    # Centralized configuration (ML, API, server settings)
│   ├── config_loader.py              # Config file parser and validator
│   ├── requirements.txt              # Core dependencies (Flask, Firebase, ML, etc.)
│   ├── requirements.train.txt        # Training-specific dependencies (transformers, etc.)
│   ├── requirements.prod.txt         # Production optimized dependencies
│   ├── Docker.md                     # Docker deployment documentation
│   ├── Dockerfile                    # Production Docker image with GPU support
│   ├── docker-compose.yml            # Docker Compose configuration
│   │
│   ├── routes/                       # API route handlers (Flask blueprints)
│   │   ├── auth.py                   # Authentication & user registration endpoints
│   │   ├── entries.py                # Journal entry CRUD operations
│   │   ├── home.py                   # Home page & landing endpoints
│   │   ├── process_entry.py          # Entry processing (mood, summary, insights)
│   │   ├── insights.py               # AI-generated insights endpoints
│   │   ├── media.py                  # Media recommendation endpoints
│   │   ├── stats.py                  # User analytics & statistics endpoints
│   │   ├── export_route.py           # Data export functionality (CSV, PDF, etc.)
│   │   ├── user.py                   # User profile management endpoints
│   │   ├── jobs.py                   # Background job status & monitoring
│   │   ├── health.py                 # Health check & system status endpoints
│   │   └── app_meta.py               # Application metadata endpoints
│   │
│   ├── ml/                           # Machine Learning & Inference Engine
│   │   ├── inference/                # Pre-trained model inference
│   │   │   ├── mood_detection/       # Mood classification inference (RoBERTa)
│   │   │   ├── summarization/        # Text summarization inference (BART)
│   │   │   └── insight_generation/   # Insight generation with LLMs
│   │   ├── training/                 # Model training scripts (offline)
│   │   │   ├── mood_detection/       # RoBERTa mood detection training
│   │   │   └── summarization/        # BART summarization training
│   │   └── utils/                    # ML utility functions & helpers
│   │
│   ├── persistence/                  # Database & Storage Layer
│   │   ├── db_manager.py             # Firestore database operations manager
│   │   └── database_schema.py        # Data models & schema definitions
│   │
│   ├── services/                     # Business Logic & Service Layer
│   │   ├── journal_entries/          # Journal entry management services
│   │   ├── insights_service/         # Insight generation & analysis services
│   │   ├── export_service/           # Data export service (CSV, JSON, PDF)
│   │   ├── stats_service/            # Analytics & statistics computation
│   │   ├── media_recommendations.py  # Media recommendation engine
│   │   ├── media_recommender/        # Advanced media recommendation models
│   │   ├── health_service.py         # System health monitoring service
│   │   ├── embedding_service.py      # Text embedding & vector operations
│   │   └── suppression.py            # Duplicate & spam suppression logic
│   │
│   ├── data/                         # Training datasets & data files
│   │   ├── mood_detection_data/      # Labeled mood detection training data
│   │   └── summarization_data/       # Summarization training datasets
│   │
│   ├── secrets/                      # API credentials & service accounts (⚠️ DO NOT COMMIT)
│   │   ├── pocket-journal-be-firebase-adminsdk-*.json  # Firebase service account
│   │   └── gen-lang-client-*.json    # Google API credentials
│   │
│   ├── utils/                        # Utility functions & helpers
│   │   ├── log_formatter.py          # Colored logging formatter
│   │   └── logging_utils.py          # Logging configuration utilities
│   │
│   ├── templates/                    # HTML templates
│   │   └── home.html                 # Landing page HTML
│   │
│   └── scripts/                      # Utility & maintenance scripts
│       ├── download_models.py        # Pre-download model artifacts
│       ├── entrypoint.sh             # Docker entrypoint script
│       └── db/                       # Database management scripts
│
├── F/                                # Flutter Frontend (Mobile App)
│   └── diary/                        # Flutter project root
│       ├── lib/                      # Dart source code
│       ├── ios/ & android/           # Native platform code
│       ├── pubspec.yaml              # Flutter dependencies
│       └── pubspec.lock              # Locked dependency versions
│
├── Documentation/                    # Project documentation & research
│   ├── SYNOPSIS.pdf                  # Project synopsis & overview
│   ├── Research Papers/              # Academic references & papers
│   ├── Review_*/                     # Review phase documentation
│   └── Diagram/                      # Architecture & flow diagrams
│
├── scripts/                          # Root-level utility scripts
│   ├── db/                           # Database management & migration scripts
│   │   ├── add_updated_at_field.py   # Add timestamp fields to Firestore documents
│   │   ├── database_manager.py       # Database operations & management utilities
│   │   ├── reset_database.py         # Reset/clear Firestore collections (development)
│   │   └── verify_database.py        # Verify database schema & integrity
│   ├── deploy/                       # Deployment & release scripts (if available)
│   └── maintenance/                  # Maintenance & utility scripts (if available)
│
├── build/                            # Build artifacts (CMake, C++ build files)
├── docker-compose.yml                # Root-level Docker Compose config
├── Dockerfile                        # Root-level Dockerfile
├── .env.example                      # Example environment variables (template)
├── LICENSE                           # MIT License
├── README.md                         # This file
└── Postman JSON Collections/         # API testing collections
    ├── Pocket Journal API Collection.postman_collection.json
    └── New Pocket Journal API Collection.postman_collection.json
```

### **🎯 Key Folder Use Cases:**

| Folder | Purpose | Key Files |
|--------|---------|-----------|
| **Backend/** | Core REST API application | `app.py`, `config.yml`, routes/ |
| **routes/** | HTTP endpoint handlers | `auth.py`, `entries.py`, `media.py` |
| **ml/** | Machine learning models & inference | `inference/`, `training/` |
| **services/** | Business logic & data processing | `journal_entries/`, `insights_service/` |
| **persistence/** | Database & storage layer | `db_manager.py`, `database_schema.py` |
| **data/** | Training datasets & samples | Labeled mood data, summaries |
| **secrets/** | Credentials (excluded from git) | Firebase, Google API keys |
| **F/diary/** | Mobile UI (Flutter/Dart) | Flutter app source code |
| **Documentation/** | Research & architecture docs | PDFs, diagrams, reviews |
| **scripts/** | Root-level utility scripts | Database, deployment, maintenance |

---

## **⚙️ PREREQUISITES**

Before you begin, ensure you have the following installed:
- **Git** - Version control system
- **Python 3.10+** - Programming language runtime
- **pip** - Python package manager
- **Docker** (optional) - For containerized deployment
- **Docker Compose** (optional) - For multi-container orchestration
- **Firebase Service Account JSON** - From Firebase Console
- **API Keys** - Gemini API, TMDB, Spotify (for media recommendations)

---

## **🚀 QUICK START GUIDE**

### **Step 1: Clone the Repository**

```powershell
# Clone the repository
git clone <repository-url> pocket-journal
cd pocket-journal
```

---

### **Step 2: LOCAL SETUP (PYTHON - DEVELOPMENT)**

#### **Option A: Quick Local Development Setup**

```powershell
# Navigate to Backend directory
cd Backend

# Create a virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### **Option B: Training Setup (for model training)**

If you need to train models locally:

```powershell
# From Backend directory
python -m venv venv-train
venv-train\Scripts\activate
pip install -r requirements.train.txt
```

---

### **Step 3: Environment Configuration**

#### **Create `.env` file in `Backend/` directory:**

Create `Backend/.env` (do NOT commit this file):

```ini
# Firebase Configuration (REQUIRED)
FIREBASE_CREDENTIALS_PATH=secrets/pocket-journal-be-firebase-adminsdk-fbsvc-b311d88edc.json

# API Keys (REQUIRED for features)
GEMINI_API_KEY=your_gemini_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here

# Server Configuration
FLASK_ENV=development
PORT=5000
DEBUG=True

# ML Configuration
MODEL_SOURCE=local
MODEL_STORE_PATH=./ml/models
MODEL_CACHE_DIR=/tmp/models
MODEL_DOWNLOAD_ON_STARTUP=false

# Logging
LOG_LEVEL=INFO
```

#### **Place Firebase Service Account:**

1. Get your Firebase service account JSON from Firebase Console
2. Place it in: `Backend/secrets/pocket-journal-be-firebase-adminsdk-fbsvc-b311d88edc.json`
3. Reference it in your `.env` file

---

### **Step 4: Run the Flask App Locally**

```powershell
# From Backend directory with venv activated
python app.py
```

The server will start on `http://127.0.0.1:5000`

✅ **Success Indicators:**
- Flask server starts without errors
- Models are loaded successfully
- API endpoints are accessible at http://127.0.0.1:5000

---

### **Step 5: DOCKER DEPLOYMENT (PRODUCTION)**

#### **Option A: Docker Compose (Recommended for Production)**

```powershell
# From repository root directory
docker-compose up -d
```

This will:
- Build the Docker image
- Start the container with GPU support
- Mount volumes for secrets and models
- Expose the API on port 8080

Check logs:
```powershell
docker-compose logs -f pocket-journal
```

Stop the container:
```powershell
docker-compose down
```

#### **Option B: Manual Docker Build & Run**

```powershell
# Build the production image
docker build -f Dockerfile -t pocket-journal:latest .

# Run the container
docker run ^
  --gpus all ^
  --env-file Backend/.env ^
  -v "%cd%\Backend\secrets:/app/secrets:ro" ^
  -v "D:\Pocket Journal\models:/models:ro" ^
  -p 8080:8080 ^
  --name pocket-journal-api ^
  pocket-journal:latest
```

---

## **🔧 CONFIGURATION DETAILS**

### **config.yml - Main Configuration File**

The `Backend/config.yml` file contains all application settings:

```yaml
# Server Settings
server:
  port: 5000
  debug: false
  
# Application Settings
app:
  environment: production
  hf_hub_disable_xet: true
  
# Logging Configuration
logging:
  app_level: INFO
  werkzeug_level: WARNING
  firebase_level: WARNING

# Firestore Collections
firestore:
  users_collection: users
  entries_collection: entries
  insights_collection: insights
  
# API Configuration
api:
  rate_limit: 100
  timeout: 30
  
# ML Model Settings
ml:
  mood_detection:
    model: roberta-base-finetuned
    version: v2
  summarization:
    model: facebook/bart-large-cnn
    version: v2
  insights:
    model: gemini-pro
```

---

## **📊 API COLLECTION & POSTMAN INTEGRATION**

### **What is Postman Collection?**

The Pocket Journal API Collection is a pre-built Postman collection that contains all API endpoints with example requests, authentication, and response formats.

### **Getting the Collection**

Two Postman collections are provided in the repository root:

1. **`Pocket Journal API Collection.postman_collection.json`** - Original collection
2. **`New Pocket Journal API Collection.postman_collection.json`** - Updated collection

### **How to Import into Postman**

#### **Method 1: Direct Import from File**

1. Open **Postman** application
2. Click **File** → **Import**
3. Select **Upload Files** tab
4. Choose the collection JSON file from repository root:
   ```
   pocket-journal/Pocket Journal API Collection.postman_collection.json
   ```
5. Click **Import**

#### **Method 2: Import via URL**

1. Copy the collection file path
2. In Postman, go to **File** → **Import**
3. Paste the file path or URL
4. Select **Import as a collection**

#### **Method 3: Direct Folder Drag & Drop**

1. Locate the `.postman_collection.json` file
2. Drag and drop it into Postman window
3. Confirm import

### **API Collection Structure**

The collection is organized by feature:

```
📦 Pocket Journal API
├── 🔐 Authentication
│   ├── Register User
│   ├── Login
│   ├── Verify Token
│   └── Logout
│
├── 📝 Journal Entries
│   ├── Create Entry
│   ├── Get Entry by ID
│   ├── Get All Entries (Paginated)
│   ├── Update Entry
│   ├── Delete Entry
│   └── Search Entries
│
├── 🎭 Mood Detection & Processing
│   ├── Analyze Entry (Mood + Summary + Insights)
│   ├── Get Mood History
│   ├── Get Mood Statistics
│   └── Mood Trends
│
├── 💡 AI Insights
│   ├── Generate Insights
│   ├── Get Insights for Period
│   ├── Personalized Reflections
│   └── Get Insight History
│
├── 🎬 Media Recommendations
│   ├── Get Movie Recommendations
│   ├── Get Music Recommendations
│   ├── Recommendations by Mood
│   └── Save Favorite Recommendation
│
├── 📊 Analytics & Statistics
│   ├── Get Overall Statistics
│   ├── Get Mood Distribution
│   ├── Get Entry Frequency
│   ├── Get Writing Patterns
│   └── Get Insights Summary
│
├── 👤 User Profile
│   ├── Get Profile
│   ├── Update Profile
│   ├── Get Preferences
│   └── Update Preferences
│
├── 📤 Data Export
│   ├── Export as CSV
│   ├── Export as JSON
│   ├── Export as PDF
│   └── Schedule Export
│
└── 🏥 Health & System
    ├── Health Check
    ├── System Status
    ├── Model Status
    └── Background Jobs Status
```

### **Using the Collection**

#### **Setup Environment Variables**

1. Click the **Environment** icon (gear icon in top-right)
2. Select or create an environment
3. Add variables:
   ```json
   {
     "base_url": "http://127.0.0.1:5000",
     "auth_token": "your_firebase_token_here",
     "user_id": "your_user_id"
   }
   ```

#### **Example API Requests**

**1. Register a New User:**
```json
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "secure_password",
  "display_name": "John Doe"
}
```

**2. Create a Journal Entry:**
```json
POST /api/entries
Authorization: Bearer {auth_token}
{
  "title": "My Daily Reflection",
  "content": "Today was a great day...",
  "mood": "happy"
}
```

**3. Get Mood Recommendations:**
```json
GET /api/media/recommendations?mood=happy&type=movie
Authorization: Bearer {auth_token}
```

**4. Get Analytics:**
```json
GET /api/stats/overview?period=month
Authorization: Bearer {auth_token}
```

---

## **🔄 API FLOW OVERVIEW**

### **Entry Processing Flow**

```
User Creates Entry
       ↓
Entry Stored in Firestore
       ↓
Trigger Entry Processing Pipeline
       ├─→ Mood Detection (RoBERTa)
       │   └─→ Emotion Classification
       ├─→ Summarization (BART)
       │   └─→ Entry Summary Generation
       └─→ Insight Generation (Gemini)
           └─→ Personalized Insights
       ↓
Media Recommendation Engine
       ├─→ Extract Mood & Context
       ├─→ Query Movie Database (TMDB)
       ├─→ Query Music Database (Spotify)
       └─→ Rank & Filter Results
       ↓
Return Enhanced Entry with:
   - Detected Mood
   - Generated Summary
   - AI Insights
   - Media Recommendations
```

### **Key API Endpoints**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | User login |
| `/api/entries` | GET | Fetch user's entries |
| `/api/entries` | POST | Create new entry |
| `/api/entries/<id>` | PUT | Update entry |
| `/api/entries/<id>` | DELETE | Delete entry |
| `/api/process/entry` | POST | Analyze entry (mood, summary, insights) |
| `/api/insights` | GET | Get generated insights |
| `/api/media/recommendations` | GET | Get media recommendations |
| `/api/stats/overview` | GET | Get analytics dashboard |
| `/api/export/csv` | POST | Export entries as CSV |
| `/api/health` | GET | System health check |

---

## **🧠 MACHINE LEARNING MODELS**

### **Mood Detection (RoBERTa)**

- **Model**: RoBERTa (Robustly Optimized BERT)
- **Task**: Multi-class emotion classification
- **Input**: Journal entry text
- **Output**: Emotion labels (happy, sad, angry, neutral, etc.)
- **Location**: `Backend/ml/inference/mood_detection/roberta/`

### **Summarization (BART)**

- **Model**: BART (Denoising Autoencoder)
- **Task**: Abstractive text summarization
- **Input**: Full journal entry
- **Output**: Concise summary (2-3 sentences)
- **Location**: `Backend/ml/inference/summarization/`

### **Insight Generation (Google Gemini)**

- **Model**: Google Gemini Pro
- **Task**: Personalized insight generation
- **Input**: Entry text, mood, history
- **Output**: AI-generated reflections and insights
- **Location**: `Backend/ml/inference/insight_generation/`

---

## **🏋️ MODEL TRAINING (OFFLINE)**

Training is performed offline using separate scripts:

### **Train Mood Detection Model**

```powershell
cd Backend
python -m venv venv-train
venv-train\Scripts\activate
pip install -r requirements.train.txt
python ml/training/mood_detection/roberta/train.py
```

### **Train Summarization Model**

```powershell
cd Backend
python ml/training/summarization/bart/train.py
```

Models will be saved to:
- `Backend/ml/models/roberta/` (mood detection)
- `Backend/ml/models/bart/` (summarization)

---

## **💾 DATABASE SCHEMA**

### **Firestore Collections**

**1. users Collection**
```json
{
  "uid": "user_firebase_id",
  "email": "user@example.com",
  "displayName": "User Name",
  "createdAt": "timestamp",
  "preferences": {
    "theme": "dark",
    "notifications": true,
    "language": "en"
  }
}
```

**2. entries Collection**
```json
{
  "entryId": "entry_unique_id",
  "userId": "user_firebase_id",
  "title": "Entry Title",
  "content": "Full journal entry text...",
  "mood": "happy",
  "summary": "Generated summary...",
  "createdAt": "timestamp",
  "updatedAt": "timestamp",
  "tags": ["work", "family"],
  "insights": ["insight_id_1", "insight_id_2"]
}
```

**3. insights Collection**
```json
{
  "insightId": "unique_id",
  "userId": "user_firebase_id",
  "entryIds": ["entry_1", "entry_2"],
  "insight": "Generated insight text...",
  "type": "reflection",
  "generatedAt": "timestamp"
}
```

---

## **📋 NOTES & TIPS**

### **Important Notes:**
- ⚠️ **Never commit** `.env` or Firebase service account JSONs to version control
- 🔒 Store all API keys securely in environment variables
- 📦 Use Git LFS for storing large model artifacts (if necessary)
- 🐳 Docker deployment includes GPU support for faster inference
- 🔄 Models are automatically loaded from the configured model store on startup
- 📊 Firestore collections must be initialized before the app starts

### **Development Tips:**
- 🔍 Check `Backend/config.yml` for all configurable settings
- 📝 Use `Backend/requirements.txt` for production, `requirements.train.txt` for training
- 🧪 Test API endpoints using the Postman collection
- 🐛 Enable `DEBUG=True` in `.env` for detailed error messages
- 📈 Monitor logs in Docker using `docker-compose logs -f`

### **Common Issues & Solutions:**

| Issue | Solution |
|-------|----------|
| Firebase credentials not found | Ensure `FIREBASE_CREDENTIALS_PATH` is set correctly in `.env` |
| Models not loading | Check `MODEL_STORE_PATH` points to correct directory |
| CUDA/GPU not detected | Verify NVIDIA Docker runtime is installed |
| Port already in use | Change `PORT` in `.env` or Docker compose |
| Out of memory | Reduce batch size in `config.yml` |

---

## **👨‍💻 CONTRIBUTORS**

This project was developed by:
- **Jenil Rathod** - Backend Development, ML Infrastructure & API with Deployment
- **Manas Joshi** - User Interface (UI) & API Architecture
- **Saloni Naik** - Frontend & Mobile Development
- **Aditya Nalla** - Media Recommendation APIs & Algorithm Design

---

## **📄 LICENSE**

This project is licensed under the MIT License. See the `LICENSE` file in the repository root for more details.
