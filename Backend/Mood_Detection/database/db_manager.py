# db_manager.py
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json, os
from dotenv import load_dotenv

load_dotenv()

class DBManager:
    def __init__(self, host="localhost", user="root",
                 password=None, database="journal_app"):
        if password is None:
            password = os.getenv("DATABASE_PASSWORD", "")
        try:
            self.conn = mysql.connector.connect(
                host=host, user=user, password=password, database=database
            )
            self.cursor = self.conn.cursor(dictionary=True)
            print("✅ Connected to database.")
        except Error as e:
            print(f"❌ DB connection failed: {e}")

    # Insert a journal entry
    def insert_entry(self, user_id, text, created_at=None):
        if not created_at:
            created_at = datetime.now()
        query = """
            INSERT INTO journal_entries (user_id, entry_text, created_at)
            VALUES (%s, %s, %s)
        """
        self.cursor.execute(query, (user_id, text, created_at))
        self.conn.commit()
        return self.cursor.lastrowid

    # Fetch entries (with analysis if exists)
    def fetch_entries_with_analysis(self, user_id, start_date=None, end_date=None):
        query = """
            SELECT je.id, je.entry_text, je.created_at, ea.summary, ea.mood
            FROM journal_entries je
            LEFT JOIN entry_analysis ea ON je.id = ea.entry_id
            WHERE je.user_id = %s
        """
        params = [user_id]
        if start_date and end_date:
            query += " AND je.created_at BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        query += " ORDER BY je.created_at ASC"

        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    # Insert insights
    def insert_insights(self, user_id, start_date, end_date,
                        goals=None, progress=None, negative_behaviors=None,
                        remedies=None, appreciation=None, conflicts=None,
                        raw_response=None):
        query = """
            INSERT INTO insights
            (user_id, start_date, end_date, goals, progress, negative_behaviors,
             remedies, appreciation, conflicts, raw_response)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (
            user_id,
            start_date,
            end_date,
            json.dumps(goals) if goals else None,
            json.dumps(progress) if progress else None,
            json.dumps(negative_behaviors) if negative_behaviors else None,
            json.dumps(remedies) if remedies else None,
            json.dumps(appreciation) if appreciation else None,
            json.dumps(conflicts) if conflicts else None,
            raw_response
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def fetch_entries(self, user_id, start_date=None, end_date=None):
        query = """
            SELECT id, entry_text, created_at
            FROM journal_entries
            WHERE user_id = %s
        """
        params = [user_id]
        if start_date and end_date:
            query += " AND created_at BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        query += " ORDER BY created_at ASC"

        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def insert_analysis(self, entry_id, summary, mood_probs):
        query = """
            INSERT INTO entry_analysis (entry_id, summary, mood)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE summary=%s, mood=%s
        """
        mood_json = json.dumps(mood_probs)
        self.cursor.execute(query, (entry_id, summary, mood_json, summary, mood_json))
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_insight_mapping(self, insight_id, entry_id, relation_type="analyzed"):
        query = """
            INSERT INTO insight_entry_mapping (insight_id, entry_id, relation_type)
            VALUES (%s, %s, %s)
        """
        self.cursor.execute(query, (insight_id, entry_id, relation_type))
        self.conn.commit()
        return self.cursor.lastrowid
