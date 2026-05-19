import json
import logging
import os
from typing import Dict, List, Any, Optional

logger = logging.getLogger()

class GroundTruthLoader:
    """Loads and validates a manually labeled dataset from a JSON file.
    
    The dataset is used to compare API predictions against human-verified labels.
    """
    
    def __init__(self, ground_truth_path: str):
        self.path = ground_truth_path
        self.ground_truth = {}

    def load(self) -> Dict[str, Dict[str, Any]]:
        """Load and validate the ground truth JSON file."""
        if not self.path:
            logger.debug("[GT] No ground truth path provided.")
            return {}
            
        if not os.path.exists(self.path):
            logger.warning("[GT] Ground truth file not found at %s", self.path)
            return {}

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.error("[GT] Invalid format: Expected a list of records.")
                return {}

            processed_gt = {}
            for i, record in enumerate(data):
                entry_id = record.get("entry_id")
                if not entry_id:
                    logger.warning("[GT] Record %d missing entry_id, skipping.", i)
                    continue
                
                # Basic validation of labels
                if "emotion_labels" in record and not isinstance(record["emotion_labels"], dict):
                    logger.warning("[GT] Record %s has malformed emotion_labels, skipping.", entry_id)
                    continue
                    
                processed_gt[entry_id] = record
            
            self.ground_truth = processed_gt
            logger.info("[GT] Successfully loaded %d ground truth records from %s", 
                        len(self.ground_truth), self.path)
            return self.ground_truth

        except json.JSONDecodeError:
            logger.error("[GT] Failed to decode JSON from %s", self.path)
            return {}
        except Exception as e:
            logger.error("[GT] Unexpected error loading ground truth: %s", str(e))
            return {}

    def get_ground_truth(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve ground truth for a specific entry ID."""
        return self.ground_truth.get(entry_id)
