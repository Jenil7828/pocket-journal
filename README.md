# Pocket Journal
A personal journaling application with mood detection and summarization features.

## Features
- User authentication (signup, login)
- Journal entry creation and retrieval
- Mood detection using a pre-trained model
- Text summarization
- Insight generation from journal entries
- RESTful API endpoints
- MySQL database integration

## Technologies Used
- Flutter (Frontend)
- Python (Backend)
- Flask (Python web framework)
- MySQL (Database)
- Transformers (Hugging Face for NLP tasks)
- Scikit-learn (Machine learning)
- Torch (Deep learning)
- Spotipy 
- Langchain

## Setup Instructions
1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd pocket-journal
   ```
3. Set up a virtual environment and activate it:
   ```bash
   cd Backend
   python -m venv venv
   cd venv/Scripts
   activate
   ```
4. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
    ```
5. Set up the MySQL database:
   - Create a MySQL database and user.
   - Run the SQL script located at `Backend/database/database.sql` to create the necessary tables.
6. Configure environment variables:
   - Create a `.env` file in the `Backend` directory.
    - Add your database credentials and any other necessary configurations.
7. Run the Flask application:
    ```bash
    python app.py
    ```
8. The backend server should now be running at  http://127.0.0.1:5000 and http://192.168.1.33:5000

## API Endpoints
- Process Journal Entry: `POST /process_entry` Requires JSON body with `user_id` and `entry_text`.
- Generate Insights: `POST /generate_insights` Requires JSON body with `user_id` , `start_date`, and `end_date`.
- Movies Recommendation by Mood: `GET  /api/recommend?mood=<mood>` 
- Movies Recommendation by Search Query: `GET /api/search?movie=<query>`
- Songs Recommendation by Mood: `GET /api/songs?mood=<mood>&language=<language>&limit=<limit>`
    - Parameters: 
        - mood: Mood of the songs (happy, sad, chill, energetic, romantic)
        - language: Song language (english, hindi, both). Default = both
        - limit: Number of songs (default = 10)
- Songs Search by Artist or Title: `GET /api/search_song?q=<query>&type=<type>&limit=<limit>`
    - Parameters:
        - q: Song or artist name (typo-tolerant)
        - type: "track" or "artist" (default = track)
        - limit: Number of results (default = 10)
- Books Recommendation by Emotion: `GET /api/books?emotion=<emotion>&limit=<limit>`
    - Example emotions: happy, sad, angry, romantic, stressed, bored
    - limit: Number of results (default = 5)
- Books Search by Title or Author: `GET /api/search_books?query=<query>&type=<type>&limit=<limit>`
    - Parameters:
        - query: Book title or author
        - type: "title", "author", or "both" (default = both)
        - limit: Number of results (default = 10)

## Example Usage
### Journal Entry Processing
```bash
  POST http://127.0.0.1:5000/process_entry user_id=1 entry_text="Today was a great day! I went to the park and enjoyed the sunshine."
```
### Generate Insights
```bash
  POST http://127.0.0.1:5000/generate_insights user_id=1 start_date="2023-01-01" end_date="2023-01-31"
```
### Movies Recommendation by Mood
```bash
  GET http://127.0.0.1:5000/api/recommend?mood=happy
```
### Songs Recommendation by Mood
```bash
  GET http://127.0.0.1:5000/api/songs?mood=happy&language=both&limit=10
```
### Books Recommendation by Emotion
```bash
  GET http://127.0.0.1:5000/api/books?emotion=happy&limit=5
```
## Notes
- Ensure that the MySQL server is running and accessible.
- Modify the database connection settings in `Backend/database/db_manager.py` as per your configuration.
- The mood detection and summarization models are pre-trained and may require internet access for the first run to download necessary files.
- For any issues or contributions, please open an issue or pull request on the repository.
## Environment Variables
- `DATABASE_PASSWORD`: Password for the MySQL database user.
- `SONG_ID`: Spotify API Client ID.
- `SONG_SECRET`: Spotify API Client Secret.
- `TMDB_API_KEY`: API key for The Movie Database (TMDb).
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to the Google Cloud service account JSON file for book recommendations.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements
- Thanks to the developers of the open-source libraries and frameworks used in this project.

## Contributions
Contributions are welcome! Please fork the repository and create a pull request with your changes.

## Contributors
- Jenil Rathod
- Manas Joshi
- Saloni Naik
- Aditya Nalla


