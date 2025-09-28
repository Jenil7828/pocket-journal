import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json

class DBManager:
    def __init__(self, host="localhost", user="root", password="Jenil_7828", database="journal_app"):
        try:
            self.conn = mysql.connector.connect(
                host=host, user=user, password=password, database=database
            )
            self.cursor = self.conn.cursor(dictionary=True)
            print("✅ Connected to database.")
        except Error as e:
            print(f"❌ DB connection failed: {e}")

    def insert_entry(self, user_id, text, created_at=None):
        if not created_at:
            created_at = datetime.now()
        query = "INSERT INTO journal_entries (user_id, entry_text, created_at) VALUES (%s, %s, %s)"
        self.cursor.execute(query, (user_id, text, created_at))
        self.conn.commit()
        return self.cursor.lastrowid

    def fetch_entries(self, user_id, start_date=None, end_date=None):
        query = "SELECT * FROM journal_entries WHERE user_id=%s"
        params = [user_id]
        if start_date and end_date:
            query += " AND created_at BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def insert_analysis(self, entry_id, summary, mood_dict, embedding, created_at=None):
        if not created_at:
            created_at = datetime.now()

        # mood_dict is a dictionary like {"happy":0.7,"sad":0.2,...}
        mood_json = json.dumps(mood_dict)
        embedding_json = json.dumps(embedding) if embedding else None

        query = """
            INSERT INTO entry_analysis (entry_id, summary, mood, embedding, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (entry_id, summary, mood_json, embedding_json, created_at))
        self.conn.commit()
