"""
TRUE ENRICHMENT SCRIPT - FORCES API CALLS

This script ACTUALLY enriches media by calling external providers.

CRITICAL RULES:
- DO call the API
- DO NOT skip silently
- DO log every action
- DO update the DB
- DO use rate limiting

This is the REAL enrichment system that actually makes API calls.
"""

import os
import sys
import logging
import time
import argparse
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s | %(message)s",
)
logger = logging.getLogger()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_admin import credentials, initialize_app, firestore
import firebase_admin
from services.media.true_provider_enricher import TMDbAPIEnricher, needs_enrichment


def init_firestore():
    """Initialize Firestore."""
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not cred_path:
        raise Exception("FIREBASE_CREDENTIALS_PATH not set")
    
    if not os.path.exists(cred_path):
        raise Exception(f"Firebase credentials not found: {cred_path}")
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
    
    return firestore.client()


class TrueEnricher:
    """Enriches media by ACTUALLY calling external APIs."""
    
    def __init__(self, dry_run: bool = False):
        self.db = init_firestore()
        self.dry_run = dry_run
        self.enricher = TMDbAPIEnricher()
        
        self.stats = {
            "processed": 0,
            "enriched": 0,
            "already_complete": 0,
            "api_errors": 0,
            "db_errors": 0,
            "fields_updated": Counter(),
            "api_calls": 0,
        }
    
    def enrich_movies(self):
        """Enrich all movies by calling TMDb API."""
        logger.info(f"\n{'='*80}")
        logger.info("TRUE ENRICHMENT - MOVIES (Calling TMDb API)")
        logger.info(f"{'='*80}\n")
        
        collection = "media_cache_movies"
        docs = self.db.collection(collection).stream()
        
        for doc in docs:
            if doc.id == "_metadata":
                continue
            
            self.stats["processed"] += 1
            doc_id = doc.id
            doc_data = doc.to_dict() or {}
            title = doc_data.get("title", "UNKNOWN")
            
            # Check if enrichment needed
            needs_it, missing = needs_enrichment(doc_data)
            
            if not needs_it:
                logger.debug(f"✓ {title}: Already complete")
                self.stats["already_complete"] += 1
                continue
            
            logger.info(f"\n[{self.stats['processed']}] ENRICHING: {title}")
            logger.info(f"    Doc ID: {doc_id}")
            logger.info(f"    Missing fields: {missing}")
            
            # Call API with correct doc_id
            self.stats["api_calls"] += 1
            patch = self.enricher.enrich_movie(doc_data, doc_id=doc_id)
            
            if not patch:
                logger.warning(f"    ⚠️  No valid fields in patch")
                self.stats["api_errors"] += 1
                continue
            
            logger.info(f"    ✓ Got {len(patch)} fields from API")
            
            # Update DB
            if self.dry_run:
                logger.info(f"    [DRY RUN] Would update: {list(patch.keys())}")
            else:
                try:
                    self.db.collection(collection).document(doc_id).update(patch)
                    logger.info(f"    ✅ DB updated: {list(patch.keys())}")
                    self.stats["enriched"] += 1
                    
                    for field in patch.keys():
                        self.stats["fields_updated"][field] += 1
                
                except Exception as e:
                    logger.error(f"    ❌ DB update failed: {e}")
                    self.stats["db_errors"] += 1
    
    def print_summary(self):
        """Print enrichment summary."""
        logger.info(f"\n\n{'='*80}")
        logger.info("ENRICHMENT SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Processed:          {self.stats['processed']}")
        logger.info(f"Enriched:           {self.stats['enriched']}")
        logger.info(f"Already complete:   {self.stats['already_complete']}")
        logger.info(f"API errors:         {self.stats['api_errors']}")
        logger.info(f"DB errors:          {self.stats['db_errors']}")
        logger.info(f"API calls made:     {self.stats['api_calls']}")
        
        if self.stats["fields_updated"]:
            logger.info(f"\nFields updated:")
            for field, count in self.stats["fields_updated"].items():
                logger.info(f"  • {field}: {count} documents")
        
        if self.dry_run:
            logger.warning(f"\n[DRY RUN] No database changes were made")
        
        logger.info(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="TRUE Enrichment - FORCES API calls to fill missing media data",
        epilog="""
Examples:
  python scripts/true_enrich_media.py --dry-run
  python scripts/true_enrich_media.py
  python scripts/true_enrich_media.py --tmdb-key YOUR_KEY
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing to DB"
    )
    
    parser.add_argument(
        "--tmdb-key",
        help="TMDb API key (overrides env var)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.tmdb_key:
        os.environ["TMDB_API_KEY"] = args.tmdb_key
    
    # Check for API key
    if not os.getenv("TMDB_API_KEY"):
        logger.error("\n" + "="*80)
        logger.error("❌ TMDB_API_KEY NOT SET")
        logger.error("="*80)
        logger.error("Cannot enrich without TMDb API key.\n")
        logger.error("Set with:")
        logger.error("  export TMDB_API_KEY='your_key'")
        logger.error("\nOr pass via command line:")
        logger.error("  python scripts/true_enrich_media.py --tmdb-key YOUR_KEY")
        logger.error("="*80 + "\n")
        sys.exit(1)
    
    try:
        logger.info("🔧 Initializing enricher...")
        enricher = TrueEnricher(dry_run=args.dry_run)
        
        if args.dry_run:
            logger.warning("⚠️  DRY RUN MODE - No changes will be written\n")
        
        # Enrich movies
        enricher.enrich_movies()
        
        # Print summary
        enricher.print_summary()
        
        logger.info("✅ Enrichment complete")
    
    except Exception as e:
        logger.error(f"❌ Enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


