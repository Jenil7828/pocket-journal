"""
Media Cache Export Utility

Exports all media cache collections (movies, books, songs, podcasts) from 
Firestore to JSON for backup, analysis, or validation purposes.

Usage:
    python scripts/export_media_cache.py
    python scripts/export_media_cache.py --output custom_filename.json
    python scripts/export_media_cache.py --collection movies
    python scripts/export_media_cache.py --stats
"""

import json
import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("pocket_journal.export_media_cache")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_admin import credentials, initialize_app, firestore
import firebase_admin

# Configuration
DEFAULT_OUTPUT_FILE = "media_cache_export.json"

COLLECTIONS = {
    "movies": "media_cache_movies",
    "books": "media_cache_books",
    "songs": "media_cache_songs",
    "podcasts": "media_cache_podcasts",
}


def init_firestore():
    """Initialize Firestore connection from environment credentials."""
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not cred_path:
        raise Exception(
            "FIREBASE_CREDENTIALS_PATH environment variable not set. "
            "Set it to the path of your Firebase service account JSON file."
        )

    if not os.path.exists(cred_path):
        raise Exception(f"Firebase credentials file not found: {cred_path}")

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)
        
        return firestore.client()
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        raise


def serialize(obj: Any) -> Any:
    """Serialize special types for JSON export."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return str(obj)
    return obj


def export_collection(db: firestore.Client, collection_name: str) -> List[Dict[str, Any]]:
    """
    Export all documents from a Firestore collection.
    
    Args:
        db: Firestore client
        collection_name: Name of collection to export
        
    Returns:
        List of documents with doc_id included
    """
    logger.info(f"Exporting {collection_name}...")
    
    collection_ref = db.collection(collection_name)
    docs = collection_ref.stream()
    
    data = []
    error_count = 0
    
    for doc in docs:
        try:
            doc_data = doc.to_dict() or {}
            
            # Add document ID for reference
            doc_data["doc_id"] = doc.id
            
            data.append(doc_data)
        
        except Exception as e:
            logger.error(f"Failed to export document {doc.id}: {e}")
            error_count += 1
    
    logger.info(f"{collection_name}: {len(data)} records exported, {error_count} errors")
    return data


def export_collections(
    db: firestore.Client,
    collections: List[str] = None,
) -> tuple:
    """
    Export multiple collections.
    
    Args:
        db: Firestore client
        collections: List of collection keys to export (None = all)
        
    Returns:
        Tuple of (export_data dict, total_records count)
    """
    if collections is None:
        collections = list(COLLECTIONS.keys())
    
    export_data = {}
    total_records = 0
    
    for collection_key in collections:
        if collection_key not in COLLECTIONS:
            logger.warning(f"Unknown collection: {collection_key}")
            continue
        
        collection_name = COLLECTIONS[collection_key]
        docs = export_collection(db, collection_name)
        export_data[collection_name] = docs
        total_records += len(docs)
    
    return export_data, total_records


def write_export(export_data: Dict[str, List[Dict]], output_file: str) -> None:
    """
    Write export data to JSON file.
    
    Args:
        export_data: Dictionary of collections and documents
        output_file: Path to output file
    """
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=serialize)
        
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        logger.info(f"✅ Export complete: {output_file} ({file_size_mb:.2f} MB)")
    
    except Exception as e:
        logger.error(f"Failed to write export file: {e}")
        raise


def calculate_stats(export_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """
    Calculate statistics about exported data including enrichment coverage.
    
    Args:
        export_data: Exported collections data
        
    Returns:
        Dictionary of statistics
    """
    stats = {
        "total_collections": len(export_data),
        "total_documents": 0,
        "collections": {},
        "enrichment_stats": {
            "with_image_url": 0,
            "with_external_url": 0,
            "with_contributors": 0,
            "with_creator": 0,
            "with_genres": 0,
            "with_duration": 0,
            "with_embedding": 0,
        }
    }
    
    for collection_name, docs in export_data.items():
        collection_stats = {
            "document_count": len(docs),
            "fields_stats": {}
        }
        
        # Analyze fields
        if docs:
            first_doc = docs[0]
            collection_stats["sample_fields"] = list(first_doc.keys())
        
        stats["collections"][collection_name] = collection_stats
        stats["total_documents"] += len(docs)
        
        # Count enrichment fields
        for doc in docs:
            if doc.get("image_url"):
                stats["enrichment_stats"]["with_image_url"] += 1
            if doc.get("external_url"):
                stats["enrichment_stats"]["with_external_url"] += 1
            if doc.get("contributors"):
                stats["enrichment_stats"]["with_contributors"] += 1
            if doc.get("creator"):
                stats["enrichment_stats"]["with_creator"] += 1
            if doc.get("genres"):
                stats["enrichment_stats"]["with_genres"] += 1
            if doc.get("duration"):
                stats["enrichment_stats"]["with_duration"] += 1
            if doc.get("embedding"):
                stats["enrichment_stats"]["with_embedding"] += 1
    
    return stats


def print_stats(stats: Dict[str, Any]) -> None:
    """Print statistics in human-readable format."""
    print("\n" + "=" * 80)
    print("EXPORT STATISTICS")
    print("=" * 80)
    print(f"Total collections: {stats['total_collections']}")
    print(f"Total documents: {stats['total_documents']}")
    
    print("\nCollection breakdown:")
    for col_name, col_stats in stats["collections"].items():
        print(f"  {col_name}: {col_stats['document_count']} documents")
    
    print("\nEnrichment field coverage:")
    total_docs = stats["total_documents"]
    if total_docs > 0:
        for field, count in stats["enrichment_stats"].items():
            pct = (count / total_docs) * 100
            print(f"  {field}: {count}/{total_docs} ({pct:.1f}%)")
    
    print("=" * 80 + "\n")


def main():
    """Main export function."""
    parser = argparse.ArgumentParser(
        description="Export media cache collections to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/export_media_cache.py
  python scripts/export_media_cache.py --output backup.json
  python scripts/export_media_cache.py --collection movies
  python scripts/export_media_cache.py --stats
        """
    )
    
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output file path (default: {DEFAULT_OUTPUT_FILE})"
    )
    
    parser.add_argument(
        "--collection",
        choices=list(COLLECTIONS.keys()),
        nargs="+",
        help="Specific collections to export (default: all)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics after export"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize Firestore
        logger.info("Initializing Firestore...")
        db = init_firestore()
        
        # Export collections
        logger.info(f"Starting export to {args.output}...")
        export_data, total_records = export_collections(
            db,
            collections=args.collection
        )
        
        # Write to file
        write_export(export_data, args.output)
        
        # Calculate and display stats if requested
        if args.stats:
            stats = calculate_stats(export_data)
            print_stats(stats)
        
        logger.info(f"✅ Export successful! Total records: {total_records}")
    
    except Exception as e:
        logger.error(f"❌ Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()