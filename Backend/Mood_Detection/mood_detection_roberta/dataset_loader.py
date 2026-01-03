import os
import glob
import numpy as np
from datasets import Dataset
from .config import Config

class SentenceDatasetLoader:
    def __init__(self, root_dir="../data"):
        self.root_dir = root_dir

    def load_data(self):
        texts, labels = [], []

        label_names = Config.LABELS  # fixed label order
        label_map = {name: i for i, name in enumerate(label_names)}

        for folder in label_names:
            folder_path = os.path.join(self.root_dir, folder)
            if os.path.isdir(folder_path):
                for file_path in glob.glob(os.path.join(folder_path, "*.txt")):
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                        texts.append(text)
                        one_hot = [0.0] * len(label_names)
                        one_hot[label_map[folder]] = 1.0
                        labels.append(one_hot)

        dataset = Dataset.from_dict({"text": texts, "labels": labels})
        return dataset, label_names

    def compute_class_weights(self, labels):
        """Compute class weights for handling imbalanced datasets
        :param labels:
        :return:
        """
        if not Config.USE_CLASS_WEIGHTING:
            return None
            
        labels_array = np.array(labels)
        class_counts = np.sum(labels_array, axis=0)
        total_samples = len(labels_array)
        
        # Compute inverse frequency weights
        weights = total_samples / (len(class_counts) * class_counts)
        weights = weights / np.sum(weights) * len(class_counts)  # Normalize
        
        return weights.tolist()
