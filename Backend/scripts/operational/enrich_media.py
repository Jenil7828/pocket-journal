"""
Pocket Journal — One-Time Media Enrichment & Normalization Script

This script processes all existing media in the cache collections and enriches them:
1. Fills missing fields from provider metadata
2. Normalizes schema across all media types
3. Preserves existing valid data (never overwrites)
4. Leaves embeddings untouched

CRITICAL RULES:
- DO NOT delete any data
- DO NOT overwrite valid existing fields
- ONLY update missing, null, empty, or zero-value fields
- DO NOT modify embeddings field
- Script is idempotent (safe to run multiple times)
- Uses partial updates (update, NOT set/overwrite)

Usage:
    python scripts/enrich_media.py                      # Full run (all collections)
    python scripts/enrich_media.py movies               # Specific collection
    python scripts/enrich_media.py --dry-run            # Preview without writing
    python scripts/enrich_media.py --dry-run --verbose  # Detailed output
"""

import argparse
import logging
import sys
import time
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple

# Setup logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("pocket_journal.enrich_media")

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_loader import get_config
from persistence.db_manager import DBManager
from services.media.media_normalizer import normalize_media, build_patch, log_patch_summary, _is_missing
from services.media.media_provider_enricher import enrich_from_providers, should_enrich


class MediaEnricher:
    """Enriches and normalizes all media in cache collections."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        # Try to initialize Firestore client - it may already be initialized
        try:
            self.db_manager = DBManager(firebase_json_path=None)
            self.db = self.db_manager.db
        except ValueError as e:
            # If Firebase initialization fails, try to get the Firestore client directly
            if "Invalid certificate argument" in str(e):
                logger.warning("Firebase initialization failed, attempting direct Firestore client setup")
                import firebase_admin
                from firebase_admin import firestore
                
                # Check if already initialized
                if not firebase_admin._apps:
                    raise Exception(
                        "Firebase credentials not found. Set FIREBASE_CREDENTIALS_PATH environment variable "
                        "or run this script in an environment with Firebase already initialized."
                    )
                
                self.db = firestore.client()
                self.db_manager = None
            else:
                raise
        
        self.dry_run = dry_run
        self.verbose = verbose
        
        if verbose:
            logging.getLogger("pocket_journal").setLevel(logging.DEBUG)
    
    def collection_name(self, media_type: str) -> str:
        """Get Firestore collection name for media type."""
        return f"media_cache_{media_type}"
    
    def enrich_collection(self, media_type: str) -> Dict[str, Any]:
        """
        Enrich and normalize all documents in a media collection.
        
        Returns:
            Stats dict with items_processed, items_updated, items_skipped, errors, etc.
        """
        media_type = media_type.lower().strip()
        col_name = self.collection_name(media_type)
        
        logger.info(f"Starting enrichment: collection={col_name}")
        
        start_time = time.time()
        stats = {
            "media_type": media_type,
            "collection": col_name,
            "items_processed": 0,
            "items_updated": 0,
            "items_unchanged": 0,
            "items_skipped": 0,
            "items_enriched_from_providers": 0,
            "provider_calls": 0,
            "provider_errors": 0,
            "errors": [],
            "fields_updated_count": Counter(),
            "provider_fields_added": Counter(),
            "duration_ms": 0,
        }
        
        try:
            col_ref = self.db.collection(col_name)
            docs = col_ref.stream()
            
            for doc in docs:
                doc_id = doc.id
                
                # Skip metadata doc
                if doc_id == "_metadata":
                    logger.debug(f"Skipping metadata document: {col_name}/{doc_id}")
                    continue
                
                stats["items_processed"] += 1
                
                try:
                    original_data = doc.to_dict() or {}
                    
                    # Step 1: Enrich from external providers if missing critical fields
                    if should_enrich(original_data, media_type):
                        logger.debug(f"Fetching from providers for {media_type}/{doc_id}")
                        stats["provider_calls"] += 1
                        enriched_data = enrich_from_providers(original_data, media_type)
                        
                        # Log enriched data for debugging
                        logger.info(f"\n📦 ENRICHED DATA ({media_type}/{doc_id}):")
                        for key, val in enriched_data.items():
                            if key != "embedding":
                                if isinstance(val, list):
                                    logger.info(f"   {key}: {len(val)} items")
                                else:
                                    logger.info(f"   {key}: {str(val)[:60]}")
                        
                        # Track which fields were added from providers
                        for key in enriched_data:
                            if key not in original_data or _is_missing(original_data.get(key)):
                                if not _is_missing(enriched_data.get(key)):
                                    stats["provider_fields_added"][key] += 1
                        
                        stats["items_enriched_from_providers"] += 1
                    else:
                        enriched_data = original_data
                    
                    # Step 2: Normalize the data
                    normalized_data = normalize_media(enriched_data, media_type)
                    
                    # Step 3: Build patch (only changed fields)
                    patch = build_patch(original_data, normalized_data)
                    
                    logger.info(f"📝 PATCH FOR {media_type}/{doc_id}: {len(patch)} fields")
                    if patch:
                        for field, value in patch.items():
                            if isinstance(value, list):
                                logger.info(f"   {field}: {len(value)} items")
                            else:
                                logger.info(f"   {field}: {str(value)[:60]}")
                    
                    # Count which fields were updated
                    for field in patch.keys():
                        stats["fields_updated_count"][field] += 1
                    
                    if patch:
                        stats["items_updated"] += 1
                        
                        # Log what's being updated
                        log_patch_summary(doc_id, col_name, patch, status="enriching")
                        
                        if self.verbose:
                            logger.debug(f"Patch for {col_name}/{doc_id}: {patch}")
                        
                        # Apply patch (partial update)
                        if not self.dry_run:
                            doc.reference.update(patch)
                            logger.debug(f"Updated {col_name}/{doc_id}")
                        else:
                            logger.debug(f"[DRY RUN] Would update {col_name}/{doc_id}")
                    else:
                        stats["items_unchanged"] += 1
                        logger.debug(f"No changes needed: {col_name}/{doc_id}")
                
                except Exception as e:
                    stats["items_skipped"] += 1
                    error_msg = f"Failed to enrich {col_name}/{doc_id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
        
        except Exception as e:
            logger.exception(f"Failed to read collection {col_name}: {str(e)}")
            stats["errors"].append(f"Collection read error: {str(e)}")
        
        stats["duration_ms"] = int((time.time() - start_time) * 1000)
        
        # Log summary
        logger.info(
            f"Collection enrichment completed: collection={col_name} "
            f"processed={stats['items_processed']} updated={stats['items_updated']} "
            f"unchanged={stats['items_unchanged']} skipped={stats['items_skipped']} "
            f"provider_calls={stats['provider_calls']} enriched_from_providers={stats['items_enriched_from_providers']} "
            f"errors={len(stats['errors'])} duration_ms={stats['duration_ms']}"
        )
        
        if stats['provider_fields_added']:
            logger.info(
                f"Provider fields added: {dict(stats['provider_fields_added'])}"
            )
        
        return stats
    
    def enrich_all_collections(self, media_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Enrich all media collections or specific ones.
        
        Args:
            media_types: List of media types to enrich. If None, enriches all.
            
        Returns:
            Overall results dict
        """
        if media_types is None:
            media_types = ["movies", "songs", "books", "podcasts"]
        else:
            media_types = [mt.lower().strip() for mt in media_types]
        
        logger.info(f"Starting enrichment for media types: {media_types}")
        
        all_start = time.time()
        results = {
            "status": "started",
            "media_types": media_types,
            "dry_run": self.dry_run,
            "results": {},
        }
        
        for media_type in media_types:
            try:
                stats = self.enrich_collection(media_type)
                results["results"][media_type] = stats
            except Exception as e:
                logger.exception(f"Failed to enrich {media_type}: {str(e)}")
                results["results"][media_type] = {
                    "media_type": media_type,
                    "status": "failed",
                    "error": str(e),
                }
        
        results["status"] = "completed"
        results["total_duration_ms"] = int((time.time() - all_start) * 1000)
        
        # Print summary
        logger.info("=" * 80)
        logger.info("ENRICHMENT SUMMARY")
        logger.info("=" * 80)
        
        total_processed = 0
        total_updated = 0
        total_unchanged = 0
        total_skipped = 0
        total_errors = 0
        total_provider_calls = 0
        total_enriched_from_providers = 0
        
        for media_type, stats in results["results"].items():
            if "items_processed" in stats:
                logger.info(
                    f"{media_type:12} | Processed: {stats['items_processed']:5} | "
                    f"Updated: {stats['items_updated']:5} | "
                    f"Provider-enriched: {stats.get('items_enriched_from_providers', 0):5} | "
                    f"Errors: {len(stats['errors']):3}"
                )
                total_processed += stats["items_processed"]
                total_updated += stats["items_updated"]
                total_unchanged += stats["items_unchanged"]
                total_skipped += stats["items_skipped"]
                total_errors += len(stats["errors"])
                total_provider_calls += stats.get("provider_calls", 0)
                total_enriched_from_providers += stats.get("items_enriched_from_providers", 0)
                
                if stats["fields_updated_count"]:
                    logger.info(f"  Fields normalized: {dict(stats['fields_updated_count'])}")
                if stats.get("provider_fields_added"):
                    logger.info(f"  Fields from providers: {dict(stats['provider_fields_added'])}")
            else:
                logger.warning(f"{media_type:12} | FAILED: {stats.get('error', 'Unknown error')}")
                total_errors += 1
        
        logger.info("=" * 80)
        logger.info(
            f"TOTALS | Processed: {total_processed} | Updated: {total_updated} | "
            f"Provider calls: {total_provider_calls} | Enriched: {total_enriched_from_providers} | "
            f"Errors: {total_errors}"
        )
        logger.info(f"Total duration: {results['total_duration_ms']} ms")
        if self.dry_run:
            logger.warning("DRY RUN MODE - No changes were written to database")
        logger.info("=" * 80)
        
        return results


def main():
    """CLI interface for enrichment."""
    parser = argparse.ArgumentParser(
        description="Enrich and normalize Pocket Journal media cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/enrich_media.py                    # Enrich all collections
  python scripts/enrich_media.py movies             # Enrich specific type
  python scripts/enrich_media.py movies songs       # Enrich multiple types
  python scripts/enrich_media.py --dry-run          # Preview without writing
  python scripts/enrich_media.py --dry-run --verbose # Detailed preview
        """,
    )
    
    parser.add_argument(
        "media_types",
        nargs="*",
        default=None,
        help="Media types to enrich (movies|songs|books|podcasts). If not provided, enriches all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to Firestore",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (debug level)",
    )
    
    args = parser.parse_args()
    
    try:
        enricher = MediaEnricher(dry_run=args.dry_run, verbose=args.verbose)
        media_types = args.media_types if args.media_types else None
        result = enricher.enrich_all_collections(media_types=media_types)
        
        # Exit with error if there were critical failures
        if result.get("status") != "completed":
            sys.exit(1)
    
    except Exception as e:
        logger.exception(f"Enrichment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()











