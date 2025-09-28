import os
import glob
from datasets import Dataset
from .config_sentence import Config

class SentenceDatasetLoader:
    def __init__(self, root_dir="data"):
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
