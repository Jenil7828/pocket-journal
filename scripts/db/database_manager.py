#!/usr/bin/env python3
"""
Database Management Script for Pocket Journal
This script provides easy access to all database operations
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the path so we can import from the project
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

def main():
    """Main database management interface"""
    
    print("🗄️  Pocket Journal Database Manager")
    print("=" * 50)
    print("Available operations:")
    print("1. Reset database (delete all data + run migration)")
    print("2. Add updated_at field to existing entries")
    print("3. Verify database structure")
    print("4. Show database schema")
    print("5. Exit")
    
    while True:
        try:
            choice = input("\nSelect an operation (1-5): ").strip()
            
            if choice == "1":
                print("\n🔄 Running database reset...")
                from reset_database import reset_database
                reset_database()
                break
                
            elif choice == "2":
                print("\n🔄 Adding updated_at field...")
                from add_updated_at_field import add_updated_at_field
                add_updated_at_field()
                break
                
            elif choice == "3":
                print("\n🔍 Verifying database structure...")
                from verify_database import verify_database
                verify_database()
                break
                
            elif choice == "4":
                print("\n📋 Showing database schema...")
                from database_schema import DatabaseSchema
                
                print("\n📝 Journal Entry Schema:")
                sample_entry = DatabaseSchema.get_journal_entry_schema("user123", "Sample entry")
                for key, value in sample_entry.items():
                    print(f"   {key}: {type(value).__name__}")
                
                print("\n🔍 Entry Analysis Schema:")
                sample_analysis = DatabaseSchema.get_entry_analysis_schema(
                    "entry123", "Sample summary", 
                    {"happy": 0.8, "sad": 0.1, "angry": 0.05, "fear": 0.02, "surprise": 0.02, "disgust": 0.01, "neutral": 0.0}
                )
                for key, value in sample_analysis.items():
                    print(f"   {key}: {type(value).__name__}")
                
                print("\n💡 Insight Schema:")
                sample_insight = DatabaseSchema.get_insight_schema(
                    "user123", "2025-01-01", "2025-01-07",
                    [{"title": "Goal 1", "description": "Description 1"}],
                    "Progress description", "Negative behaviors", "Remedies",
                    "Appreciation", "Conflicts", "Raw response"
                )
                for key, value in sample_insight.items():
                    print(f"   {key}: {type(value).__name__}")
                break
                
            elif choice == "5":
                print("\n👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please select 1-5.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please check your Firebase credentials and try again.")

if __name__ == "__main__":
    # Check if Firebase credentials are set
    if not os.getenv("FIREBASE_CREDENTIALS_PATH"):
        print("❌ FIREBASE_CREDENTIALS_PATH not found in .env file!")
        print("Please add FIREBASE_CREDENTIALS_PATH to your .env file")
        print("\nExample .env file:")
        print("FIREBASE_CREDENTIALS_PATH=path/to/your/firebase-credentials.json")
        exit(1)
    
    main()
