#!/usr/bin/env python3
"""
Database verification script for Pocket Journal
This script checks if the database structure is correct after reset
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz

def verify_database():
    """Verify the database structure and data integrity"""
    
    # Initialize Firebase
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    IST = pytz.timezone("Asia/Kolkata")
    
    print("🔍 Pocket Journal Database Verification")
    print("=" * 50)
    
    # Check each collection
    collections = {
        "journal_entries": {
            "required_fields": ["uid", "entry_text", "created_at", "updated_at"],
            "description": "User journal entries"
        },
        "entry_analysis": {
            "required_fields": ["entry_id", "summary", "mood", "created_at"],
            "description": "AI analysis of journal entries"
        },
        "insights": {
            "required_fields": ["uid", "start_date", "end_date", "goals", "progress", 
                              "negative_behaviors", "remedies", "appreciation", 
                              "conflicts", "raw_response", "created_at"],
            "description": "AI-generated insights"
        },
        "insight_entry_mapping": {
            "required_fields": ["insight_id", "entry_id"],
            "description": "Links insights to entries"
        }
    }
    
    total_docs = 0
    issues_found = []
    
    for collection_name, config in collections.items():
        print(f"\n📄 Checking {collection_name}...")
        print(f"   Description: {config['description']}")
        
        try:
            docs = list(db.collection(collection_name).stream())
            doc_count = len(docs)
            total_docs += doc_count
            print(f"   Documents: {doc_count}")
            
            if doc_count > 0:
                # Check first document structure
                sample_doc = docs[0].to_dict()
                sample_fields = list(sample_doc.keys())
                print(f"   Sample fields: {sample_fields}")
                
                # Check for required fields
                missing_fields = [field for field in config['required_fields'] 
                                if field not in sample_doc]
                
                if missing_fields:
                    issues_found.append(f"{collection_name}: Missing fields {missing_fields}")
                    print(f"   ❌ Missing required fields: {missing_fields}")
                else:
                    print(f"   ✅ All required fields present")
                
                # Special validation for mood field in entry_analysis
                if collection_name == "entry_analysis" and "mood" in sample_doc:
                    mood = sample_doc["mood"]
                    required_moods = ["happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"]
                    missing_moods = [m for m in required_moods if m not in mood]
                    if missing_moods:
                        issues_found.append(f"{collection_name}: Missing mood keys {missing_moods}")
                        print(f"   ❌ Missing mood keys: {missing_moods}")
                    else:
                        print(f"   ✅ All mood keys present")
                
                # Check for updated_at field in journal_entries
                if collection_name == "journal_entries":
                    if "updated_at" not in sample_doc:
                        issues_found.append(f"{collection_name}: Missing updated_at field")
                        print(f"   ❌ Missing updated_at field")
                    else:
                        print(f"   ✅ updated_at field present")
            else:
                print(f"   ℹ️  Collection is empty")
                
        except Exception as e:
            issues_found.append(f"{collection_name}: Error - {str(e)}")
            print(f"   ❌ Error accessing collection: {str(e)}")
    
    # Check data relationships
    print(f"\n🔗 Checking data relationships...")
    
    try:
        # Check if entry_analysis entries have valid journal_entries references
        analysis_docs = list(db.collection("entry_analysis").stream())
        journal_docs = list(db.collection("journal_entries").stream())
        journal_ids = {doc.id for doc in journal_docs}
        
        orphaned_analysis = 0
        for analysis_doc in analysis_docs:
            analysis_data = analysis_doc.to_dict()
            entry_id = analysis_data.get("entry_id")
            if entry_id not in journal_ids:
                orphaned_analysis += 1
        
        if orphaned_analysis > 0:
            issues_found.append(f"entry_analysis: {orphaned_analysis} orphaned analysis documents")
            print(f"   ❌ {orphaned_analysis} orphaned analysis documents found")
        else:
            print(f"   ✅ All analysis documents have valid entry references")
        
        # Check insight mappings
        mapping_docs = list(db.collection("insight_entry_mapping").stream())
        insight_docs = list(db.collection("insights").stream())
        insight_ids = {doc.id for doc in insight_docs}
        
        orphaned_mappings = 0
        for mapping_doc in mapping_docs:
            mapping_data = mapping_doc.to_dict()
            insight_id = mapping_data.get("insight_id")
            entry_id = mapping_data.get("entry_id")
            if insight_id not in insight_ids or entry_id not in journal_ids:
                orphaned_mappings += 1
        
        if orphaned_mappings > 0:
            issues_found.append(f"insight_entry_mapping: {orphaned_mappings} orphaned mapping documents")
            print(f"   ❌ {orphaned_mappings} orphaned mapping documents found")
        else:
            print(f"   ✅ All mapping documents have valid references")
            
    except Exception as e:
        issues_found.append(f"Relationship check: Error - {str(e)}")
        print(f"   ❌ Error checking relationships: {str(e)}")
    
    # Summary
    print(f"\n📊 Verification Summary")
    print("=" * 30)
    print(f"Total documents: {total_docs}")
    print(f"Issues found: {len(issues_found)}")
    
    if issues_found:
        print(f"\n❌ Issues found:")
        for issue in issues_found:
            print(f"   • {issue}")
        print(f"\n💡 Run the reset script to fix these issues:")
        print(f"   python Mood_Detection/database/reset_database.py")
    else:
        print(f"\n✅ Database structure is correct!")
        print(f"🎉 All collections have proper structure and relationships!")
    
    return len(issues_found) == 0

if __name__ == "__main__":
    print("🔍 Pocket Journal Database Verification Tool")
    print("=" * 50)
    
    # Check if Firebase credentials are set
    if not os.getenv("FIREBASE_CREDENTIALS_PATH"):
        print("❌ FIREBASE_CREDENTIALS_PATH environment variable not set!")
        print("Please set it to your Firebase service account JSON file path.")
        exit(1)
    
    try:
        success = verify_database()
        if success:
            print("\n🎉 Database verification passed!")
        else:
            print("\n⚠️  Database verification found issues.")
    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")
        print("Please check your Firebase credentials and try again.")
