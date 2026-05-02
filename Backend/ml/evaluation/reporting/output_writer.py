import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger()

class OutputWriter:
    """Handles streaming and final summary output for the evaluation run.
    
    Writes detailed records to a JSONL file (streaming) and a summary to a JSON file.
    """
    
    def __init__(self, output_dir: str, run_id: str):
        self.output_dir = output_dir
        self.run_id = run_id
        os.makedirs(output_dir, exist_ok=True)
        
        self.records_path = os.path.join(output_dir, f"eval_{run_id}.jsonl")
        self.summary_path = os.path.join(output_dir, f"eval_{run_id}_summary.json")
        
        # Open record file for appending (clears if exists)
        with open(self.records_path, 'w', encoding='utf-8') as f:
            pass
        
        logger.info("[OUTPUT] Initialized results at %s", self.output_dir)

    def write_record(self, record: Dict[str, Any]) -> None:
        """Append a single evaluation record to the JSONL file and flush."""
        try:
            with open(self.records_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.error("[OUTPUT] Failed to write record: %s", str(e))

    def write_summary(self, batch_summary: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Write the final summary JSON file."""
        report = {
            "run_id": self.run_id,
            "evaluation_timestamp": datetime.utcnow().isoformat() + "Z",
            "config": config,
            "batch_summary": batch_summary,
            "output_files": {
                "records_jsonl": self.records_path,
                "summary_json": self.summary_path
            }
        }
        
        try:
            with open(self.summary_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            logger.info("[OUTPUT] Summary report written to %s", self.summary_path)
        except Exception as e:
            logger.error("[OUTPUT] Failed to write summary: %s", str(e))

    def get_records_path(self) -> str:
        return self.records_path

    def get_summary_path(self) -> str:
        return self.summary_path
