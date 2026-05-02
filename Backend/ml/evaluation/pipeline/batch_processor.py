import time
import logging
from typing import List, Dict, Any
from ml.evaluation.pipeline.entry_processor import EntryProcessor
from ml.evaluation.reporting.output_writer import OutputWriter

logger = logging.getLogger()

class BatchProcessor:
    """Handles the sequential execution of evaluation tasks for a batch of entries.
    
    Ensures rate limits are respected by processing entries one-by-one with a delay.
    """
    
    def __init__(self, entry_processor: EntryProcessor, output_writer: OutputWriter, 
                 delay_between_entries_ms: int = 500):
        self.entry_processor = entry_processor
        self.output_writer = output_writer
        self.delay = delay_between_entries_ms / 1000.0

    def process_batch(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a list of entries sequentially and stream results to the output writer."""
        total = len(entries)
        successful = 0
        failed = 0
        failed_entry_ids = []
        
        start_time = time.time()
        
        logger.info("[BATCH] Starting evaluation of %d entries...", total)
        
        for i, entry in enumerate(entries, 1):
            entry_id = entry.get("entry_id")
            logger.info(self.get_progress_string(i, total))
            
            try:
                result = self.entry_processor.process_entry(entry)
                
                # Check for critical failures in metadata.errors
                if not result.get("created_entry_id"):
                    failed += 1
                    failed_entry_ids.append(entry_id)
                else:
                    successful += 1
                
                # Stream result to file
                self.output_writer.write_record(result)
                
            except Exception as e:
                failed += 1
                failed_entry_ids.append(entry_id)
                logger.error("[BATCH] Unhandled error processing entry %s: %s", entry_id, str(e))
            
            # Rate limiting delay
            if i < total:
                time.sleep(self.delay)
                
        duration = time.time() - start_time
        logger.info("[BATCH] Evaluation complete. Duration: %.2fs", duration)
        
        return {
            "total_entries": total,
            "successful": successful,
            "failed": failed,
            "failed_entry_ids": failed_entry_ids,
            "total_duration_seconds": duration
        }

    def get_progress_string(self, current: int, total: int) -> str:
        """Return a formatted progress string."""
        return f"[{current}/{total}] Processing entry {current}..."
