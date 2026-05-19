import argparse
import logging
import sys
import os
from datetime import datetime

# Ensure Backend is in path
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_HERE))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config_loader import get_config
from persistence.db_manager import DBManager
from ml.evaluation.orchestrator.auth_client import AuthClient
from ml.evaluation.orchestrator.api_client import APIClient
from ml.evaluation.orchestrator.firestore_fetcher import FirestoreFetcher
from ml.evaluation.orchestrator.ground_truth_loader import GroundTruthLoader
from ml.evaluation.ground_truth.gemini_generator import GeminiGTGenerator
from ml.evaluation.pipeline.entry_processor import EntryProcessor
from ml.evaluation.pipeline.batch_processor import BatchProcessor
from ml.evaluation.reporting.output_writer import OutputWriter

# Use root logger
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

def print_banner(run_id, base_url, uid, limit, gt_file, cleanup):
    banner = f"""
╔══════════════════════════════════════════════════╗
║     Pocket Journal — System Evaluation Run       ║
╠══════════════════════════════════════════════════╣
║ Run ID:     {run_id:<36} ║
║ Base URL:   {base_url:<36} ║
║ UID:        {uid:<36} ║
║ Entries:    {limit:<36} ║
║ GT File:    {str(gt_file):<36} ║
║ Cleanup:    {str(cleanup):<36} ║
╚══════════════════════════════════════════════════╝
"""
    print(banner)

def main():
    parser = argparse.ArgumentParser(description="Pocket Journal System-Level API Evaluation")
    parser.add_argument("--base-url", default="http://localhost:5000", help="API base URL")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--uid", required=True, help="Firestore user UID to fetch entries for")
    parser.add_argument("--ground-truth", help="Path to ground truth JSON file")
    parser.add_argument("--limit", type=int, default=50, help="Max entries to evaluate (ignored if --entry-ids is used)")
    parser.add_argument("--entry-ids", help="Comma-separated Firestore document IDs to evaluate")
    parser.add_argument("--start-date", help="Filter entries from date YYYY-MM-DD")
    parser.add_argument("--end-date", help="Filter entries to date YYYY-MM-DD")
    parser.add_argument("--output-dir", default="ml/evaluation/results", help="Output directory")
    parser.add_argument("--rec-limit", type=int, default=5, help="Recommendations per type")
    parser.add_argument("--cleanup", action="store_true", help="Delete created journal entries after evaluation")
    parser.add_argument("--use-gemini-gt", action="store_true", help="Use Gemini to generate automated ground truth labels")
    parser.add_argument(
        "--dataset-file",
        help="Path to dataset JSON from generate_dataset.py. "
             "If set, overrides --uid / --entry-ids Firestore fetch."
    )
    parser.add_argument("--delay-ms", type=int, default=500, help="Delay between entries in ms")
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Parse entry IDs if provided
    entry_ids = []
    if args.entry_ids:
        entry_ids = [eid.strip() for eid in args.entry_ids.split(",") if eid.strip()]
        if args.limit != 50: # Check if user manually set a limit
             logger.warning("[CONFIG] Both --limit and --entry-ids provided. --limit will be ignored.")

    display_limit = f"Specific ({len(entry_ids)})" if entry_ids else args.limit
    print_banner(run_id, args.base_url, args.uid, display_limit, args.ground_truth, args.cleanup)

    # 1. Auth Init
    try:
        auth_client = AuthClient(args.base_url, args.email, args.password)
        auth_client.login()
    except Exception as e:
        logger.error("Authentication failed: %s", str(e))
        sys.exit(1)

    # 2. Database & Fetcher Init
    try:
        db_manager = DBManager()
        fetcher = FirestoreFetcher(db_manager)
        gt_loader = GroundTruthLoader(args.ground_truth)
        
        if args.dataset_file:
            logger.info("[CONFIG] Loading entries from dataset file: %s", args.dataset_file)
            with open(args.dataset_file, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            
            entries = []
            for record in dataset:
                # Map to EntryProcessor format
                entries.append({
                    "entry_id": record["entry_id"],
                    "entry_text": record["entry_text"],
                    "created_at": record["created_at"],
                    "title": record.get("title")
                })
                
                # Inject ground truth directly
                if "ground_truth" in record:
                    gt_loader.ground_truth[record["entry_id"]] = record["ground_truth"]
            
            logger.info("[CONFIG] Successfully loaded %d entries from dataset file", len(entries))
        
        elif entry_ids:
            logger.info("[EVAL] Evaluating %d specific entry IDs from Firestore", len(entry_ids))
            entries = fetcher.fetch_entries_by_ids(args.uid, entry_ids)
        else:
            entries = fetcher.fetch_entries_for_uid(
                args.uid, limit=args.limit, start_date=args.start_date, end_date=args.end_date
            )
    except Exception as e:
        logger.error("Failed to initialize data: %s", str(e))
        sys.exit(1)

    if not entries:
        logger.error("No entries found. Cannot proceed with evaluation.")
        sys.exit(1)

    # 3. Ground Truth Init (for manual file if provided, will be merged with dataset GT)
    if args.ground_truth:
        gt_loader.load()

    # 4. Pipeline & Reporting Init
    api_client = APIClient(args.base_url, auth_client)
    
    gemini_generator = None
    if args.use_gemini_gt:
        gemini_generator = GeminiGTGenerator()
        
    entry_processor = EntryProcessor(
        api_client, 
        gt_loader, 
        gemini_generator=gemini_generator,
        rec_limit=args.rec_limit, 
        cleanup_after=args.cleanup
    )
    output_writer = OutputWriter(args.output_dir, run_id)
    batch_processor = BatchProcessor(entry_processor, output_writer, delay_between_entries_ms=args.delay_ms)

    # 5. Execute Evaluation
    config_summary = {
        "base_url": args.base_url,
        "uid": args.uid,
        "limit": args.limit,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "rec_limit": args.rec_limit,
        "cleanup": args.cleanup,
        "delay_ms": args.delay_ms
    }
    
    batch_summary = batch_processor.process_batch(entries)
    
    # 6. Finalize
    output_writer.write_summary(batch_summary, config_summary)
    
    print("\n" + "═"*50)
    print(" ✓ Evaluation complete")
    print(f" ✓ Records: {batch_summary['successful']}/{batch_summary['total_entries']}")
    print(f" ✓ Output:  {output_writer.get_records_path()}")
    print(f" ✓ Summary: {output_writer.get_summary_path()}")
    print("═"*50 + "\n")

if __name__ == "__main__":
    main()
