import matplotlib.pyplot as plt

class EmotionVisualizer:
    @staticmethod
    def plot_emotions(predictions):
        labels = list(predictions.keys())
        values = list(predictions.values())

        plt.figure(figsize=(8,5))
        plt.bar(labels, values)
        plt.title("Emotion Probabilities")
        plt.ylabel("Probability")
        plt.xticks(rotation=45)
        plt.show()
