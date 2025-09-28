# embeddings/trainer.py

import os
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, losses, InputExample
from .config import EmbeddingConfig

class EmbeddingTrainer:
    def __init__(self):
        self.model = SentenceTransformer(EmbeddingConfig.MODEL_NAME)

    def load_dataset_from_folders(self, root_dir="data"):
        """
        Loads dataset from folder structure:
        root/
          ├── happy/*.txt
          ├── sad/*.txt
          ├── anger/*.txt
        """
        label_map = {}   # Map mood -> integer
        examples = []
        current_label = 0

        for mood in os.listdir(root_dir):
            mood_path = os.path.join(root_dir, mood)
            if not os.path.isdir(mood_path):
                continue

            # assign numeric label
            if mood not in label_map:
                label_map[mood] = current_label
                current_label += 1

            # iterate text files
            for fname in os.listdir(mood_path):
                if fname.endswith(".txt"):
                    fpath = os.path.join(mood_path, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                        if text:
                            examples.append(InputExample(texts=[text], label=label_map[mood]))

        print(f"Loaded {len(examples)} samples from {len(label_map)} moods: {label_map}")
        return examples, label_map

    def train(self, train_examples):
        train_dataloader = DataLoader(train_examples, shuffle=True,
                                      batch_size=EmbeddingConfig.TRAIN_BATCH_SIZE)

        train_loss = losses.SoftmaxLoss(
            model=self.model,
            sentence_embedding_dimension=self.model.get_sentence_embedding_dimension(),
            num_labels=len(set([ex.label for ex in train_examples]))
        )

        self.model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=EmbeddingConfig.NUM_EPOCHS,
            warmup_steps=100,
            output_path=EmbeddingConfig.OUTPUT_DIR
        )
        print(f"✅ Model saved at {EmbeddingConfig.OUTPUT_DIR}")


if __name__ == "__main__":
    trainer = EmbeddingTrainer()
    train_examples, label_map = trainer.load_dataset_from_folders("data")
    trainer.train(train_examples)


# # embeddings/trainer.py
#
# import os
# from torch.utils.data import DataLoader
# from sentence_transformers import SentenceTransformer, losses, InputExample
# from .config import EmbeddingConfig
#
# class EmbeddingTrainer:
#     def __init__(self):
#         self.model = SentenceTransformer(EmbeddingConfig.MODEL_NAME)
#
#     def load_dataset(self, dataset):
#         """
#         dataset should be a HuggingFace Dataset or list of dicts like:
#         [{"text": "I feel happy", "label": "happy"}, ...]
#         """
#         examples = []
#         for row in dataset:
#             examples.append(InputExample(texts=[row["text"]], label=row["label"]))
#         return examples
#
#     def train(self, train_examples):
#         # Convert to dataloader
#         train_dataloader = DataLoader(train_examples, shuffle=True,
#                                       batch_size=EmbeddingConfig.TRAIN_BATCH_SIZE)
#
#         # Loss: classification / softmax loss
#         train_loss = losses.SoftmaxLoss(
#             model=self.model,
#             sentence_embedding_dimension=self.model.get_sentence_embedding_dimension(),
#             num_labels=len(set([ex.label for ex in train_examples]))
#         )
#
#         # Train
#         self.model.fit(
#             train_objectives=[(train_dataloader, train_loss)],
#             epochs=EmbeddingConfig.NUM_EPOCHS,
#             warmup_steps=100,
#             output_path=EmbeddingConfig.OUTPUT_DIR
#         )
#         print(f"Model saved at {EmbeddingConfig.OUTPUT_DIR}")
#
# # Example run
# if __name__ == "__main__":
#     # Fake dataset example
#     dataset = [
#         {"text": "I feel happy today", "label": 0},
#         {"text": "I am very sad", "label": 1},
#         {"text": "I am angry at my friend", "label": 2}
#     ]
#
#     trainer = EmbeddingTrainer()
#     examples = trainer.load_dataset(dataset)
#     trainer.train(examples)
