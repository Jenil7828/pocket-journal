#!/usr/bin/env python3
"""
Database Schema Definition for Pocket Journal
This file defines the proper structure for all collections
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import pytz

class DatabaseSchema:
    """
    Defines the proper database schema for Pocket Journal Firebase collections
    """
    
    IST = pytz.timezone("Asia/Kolkata")
    
    @staticmethod
    def get_journal_entry_schema(uid: str, entry_text: str) -> Dict[str, Any]:
        """
        Returns the proper schema for a journal entry document
        
        Args:
            uid: Firebase Auth UID
            entry_text: The journal entry text
            
        Returns:
            Dictionary with proper journal entry structure
        """
        now = datetime.now(DatabaseSchema.IST)
        return {
            "uid": uid,                    # Firebase Auth UID (string)
            "entry_text": entry_text,      # Journal entry content (string)
            "created_at": now,             # When entry was created (timestamp)
            "updated_at": now              # When entry was last updated (timestamp)
        }
    
    @staticmethod
    def get_entry_analysis_schema(entry_id: str, summary: str, mood: Dict[str, float]) -> Dict[str, Any]:
        """
        Returns the proper schema for an entry analysis document
        
        Args:
            entry_id: Reference to journal_entries document ID
            summary: AI-generated summary
            mood: Mood probability scores
            
        Returns:
            Dictionary with proper entry analysis structure
        """
        now = datetime.now(DatabaseSchema.IST)
        return {
            "entry_id": entry_id,          # Reference to journal_entries (string)
            "summary": summary,            # AI-generated summary (string)
            "mood": mood,                  # Mood probabilities (object)
            "created_at": now              # When analysis was created (timestamp)
        }
    
    @staticmethod
    def get_insight_schema(uid: str, start_date: str, end_date: str, 
                          goals: List[Dict[str, str]], progress: str,
                          negative_behaviors: str, remedies: str,
                          appreciation: str, conflicts: str, 
                          raw_response: str) -> Dict[str, Any]:
        """
        Returns the proper schema for an insights document
        
        Args:
            uid: Firebase Auth UID
            start_date: Start date for insight period (YYYY-MM-DD)
            end_date: End date for insight period (YYYY-MM-DD)
            goals: List of goal objects with title and description
            progress: Progress assessment
            negative_behaviors: Identified negative patterns
            remedies: Suggested remedies
            appreciation: Positive aspects
            conflicts: Identified conflicts
            raw_response: Raw AI response
            
        Returns:
            Dictionary with proper insights structure
        """
        now = datetime.now(DatabaseSchema.IST)
        return {
            "uid": uid,                    # Firebase Auth UID (string)
            "start_date": start_date,      # Start date (string, YYYY-MM-DD)
            "end_date": end_date,          # End date (string, YYYY-MM-DD)
            "goals": goals,                # Array of goal objects
            "progress": progress,          # Progress description (string)
            "negative_behaviors": negative_behaviors,  # Negative patterns (string)
            "remedies": remedies,          # Suggested remedies (string)
            "appreciation": appreciation,  # Positive aspects (string)
            "conflicts": conflicts,        # Identified conflicts (string)
            "raw_response": raw_response,  # Raw AI response (string)
            "created_at": now              # When insight was created (timestamp)
        }
    
    @staticmethod
    def get_insight_mapping_schema(insight_id: str, entry_id: str) -> Dict[str, str]:
        """
        Returns the proper schema for an insight-entry mapping document
        
        Args:
            insight_id: Reference to insights document ID
            entry_id: Reference to journal_entries document ID
            
        Returns:
            Dictionary with proper mapping structure
        """
        return {
            "insight_id": insight_id,      # Reference to insights (string)
            "entry_id": entry_id          # Reference to journal_entries (string)
        }
    
    @staticmethod
    def validate_journal_entry(data: Dict[str, Any]) -> bool:
        """
        Validates if a journal entry document has the correct structure
        
        Args:
            data: Document data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["uid", "entry_text", "created_at", "updated_at"]
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_entry_analysis(data: Dict[str, Any]) -> bool:
        """
        Validates if an entry analysis document has the correct structure
        
        Args:
            data: Document data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["entry_id", "summary", "mood", "created_at"]
        if not all(field in data for field in required_fields):
            return False
        
        # Validate mood structure
        mood = data.get("mood", {})
        required_moods = ["happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"]
        return all(mood_key in mood for mood_key in required_moods)
    
    @staticmethod
    def validate_insight(data: Dict[str, Any]) -> bool:
        """
        Validates if an insights document has the correct structure
        
        Args:
            data: Document data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            "uid", "start_date", "end_date", "goals", "progress",
            "negative_behaviors", "remedies", "appreciation", 
            "conflicts", "raw_response", "created_at"
        ]
        return all(field in data for field in required_fields)
    
    @staticmethod
    def get_collection_rules() -> Dict[str, str]:
        """
        Returns Firestore security rules for each collection
        
        Returns:
            Dictionary with collection names and their security rules
        """
        return {
            "journal_entries": """
                rules_version = '2';
                service cloud.firestore {
                  match /databases/{database}/documents {
                    match /journal_entries/{document} {
                      allow read, write: if request.auth != null && request.auth.uid == resource.data.uid;
                      allow create: if request.auth != null && request.auth.uid == request.resource.data.uid;
                    }
                  }
                }
            """,
            "entry_analysis": """
                rules_version = '2';
                service cloud.firestore {
                  match /databases/{database}/documents {
                    match /entry_analysis/{document} {
                      allow read, write: if request.auth != null;
                    }
                  }
                }
            """,
            "insights": """
                rules_version = '2';
                service cloud.firestore {
                  match /databases/{database}/documents {
                    match /insights/{document} {
                      allow read, write: if request.auth != null && request.auth.uid == resource.data.uid;
                      allow create: if request.auth != null && request.auth.uid == request.resource.data.uid;
                    }
                  }
                }
            """,
            "insight_entry_mapping": """
                rules_version = '2';
                service cloud.firestore {
                  match /databases/{database}/documents {
                    match /insight_entry_mapping/{document} {
                      allow read, write: if request.auth != null;
                    }
                  }
                }
            """
        }

# Example usage and testing
if __name__ == "__main__":
    print("📋 Pocket Journal Database Schema")
    print("=" * 40)
    
    # Example journal entry
    journal_entry = DatabaseSchema.get_journal_entry_schema(
        uid="user123",
        entry_text="Today was a great day!"
    )
    print("📝 Journal Entry Schema:")
    print(f"   Fields: {list(journal_entry.keys())}")
    print(f"   Valid: {DatabaseSchema.validate_journal_entry(journal_entry)}")
    
    # Example entry analysis
    entry_analysis = DatabaseSchema.get_entry_analysis_schema(
        entry_id="entry123",
        summary="Positive day with good energy",
        mood={"happy": 0.8, "sad": 0.1, "angry": 0.05, "fear": 0.02, "surprise": 0.02, "disgust": 0.01, "neutral": 0.0}
    )
    print("\n🔍 Entry Analysis Schema:")
    print(f"   Fields: {list(entry_analysis.keys())}")
    print(f"   Valid: {DatabaseSchema.validate_entry_analysis(entry_analysis)}")
    
    # Example insight
    insight = DatabaseSchema.get_insight_schema(
        uid="user123",
        start_date="2025-01-01",
        end_date="2025-01-07",
        goals=[{"title": "Exercise", "description": "Daily morning runs"}],
        progress="Good progress on exercise routine",
        negative_behaviors="None identified",
        remedies="Continue current routine",
        appreciation="Consistent with health goals",
        conflicts="None identified",
        raw_response='{"goals": [...]}'
    )
    print("\n💡 Insight Schema:")
    print(f"   Fields: {list(insight.keys())}")
    print(f"   Valid: {DatabaseSchema.validate_insight(insight)}")
    
    print("\n✅ Schema validation complete!")
