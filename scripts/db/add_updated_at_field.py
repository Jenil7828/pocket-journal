#!/usr/bin/env python3
"""
Migration script to add updated_at field to existing journal_entries
This script will add updated_at = created_at for all existing entries
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz

def add_updated_at_field():
    """Add updated_at field to all existing journal entries"""
    
    # Initialize Firebase
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    IST = pytz.timezone("Asia/Kolkata")
    
    print("🔄 Starting migration to add updated_at field...")
    
    # Get all journal entries
    entries_ref = db.collection("journal_entries")
    entries = entries_ref.stream()
    
    updated_count = 0
    error_count = 0
    
    for entry in entries:
        try:
            entry_data = entry.to_dict()
            entry_id = entry.id
            
            # Check if updated_at already exists
            if "updated_at" in entry_data:
                print(f"⏭️  Entry {entry_id} already has updated_at field, skipping...")
                continue
            
            # Add updated_at field (set to created_at for existing entries)
            created_at = entry_data.get("created_at")
            if created_at:
                # Use created_at as updated_at for existing entries
                updated_at = created_at
            else:
                # Fallback to current time if created_at is missing
                updated_at = datetime.now(IST)
            
            # Update the document
            entry.reference.update({
                "updated_at": updated_at
            })
            
            updated_count += 1
            print(f"✅ Updated entry {entry_id}")
            
        except Exception as e:
            error_count += 1
            print(f"❌ Error updating entry {entry.id}: {str(e)}")
    
    print(f"\n🎉 Migration completed!")
    print(f"✅ Successfully updated: {updated_count} entries")
    print(f"❌ Errors: {error_count} entries")
    
    if error_count == 0:
        print("🎯 All entries now have updated_at field!")
    else:
        print("⚠️  Some entries failed to update. Check the errors above.")

if __name__ == "__main__":
    add_updated_at_field()
