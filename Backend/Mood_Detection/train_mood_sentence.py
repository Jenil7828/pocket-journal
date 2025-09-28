from mood_detection_sentence.trainer_sentence import SentenceTrainer
from mood_detection_sentence.predictor_sentence_level import SentencePredictor
from mood_detection_sentence.visualizer import EmotionVisualizer

if __name__ == "__main__":
    # trainer = SentenceTrainer()
    # trainer.train()
    predictor = SentencePredictor()
    input_text1 = """
   Today was awful. The cafeteria served food that looked half-cooked and smelled rotten, which immediately made me feel sick to my stomach. I pushed the tray away in disgust, but the sight of others eating it only made me queasier. To make matters worse, the trash bins were overflowing, and the whole place reeked. I felt trapped in that unhygienic environment, and no matter how hard I tried to ignore it, the stench stuck in my head. It ruined my appetite and left me in a foul mood for the rest of the day.
   """
    result = predictor.predict(input_text1)
    print(result, "\n\n\n\n\n\n\n\n")
    EmotionVisualizer.plot_emotions(result)
    input_text2 = """
   What an unexpectedly wonderful day! I met an old friend by chance at the café, and we ended up talking for hours. We laughed so much about our past memories that I completely lost track of time. It felt refreshing to have such genuine joy and connection, especially when I hadn’t planned for it at all. That surprise encounter left me smiling all the way home, feeling lighter than I have in weeks.
    """
    result1 = predictor.predict(input_text2)
    print(result1, "\n\n\n\n\n\n\n\n")
    EmotionVisualizer.plot_emotions(result1)

# from mood_detection_sentence.trainer_sentence import MoodTrainer
# from mood_detection_sentence.predictor_sentence_level import SentenceLevelPredictor
#
# predictor = SentenceLevelPredictor("outputs/mood_model")
#
# text = """I felt really sad when I lost my wallet.
# But later I was relieved and happy when someone returned it."""
#
# labels, probs, sentences = predictor.predict_paragraph(text)
# print("Sentences:", sentences)
# print("Paragraph emotions:", labels)
#
# if __name__ == "__main__":
# 	trainer = MoodTrainer()
# 	trainer.train()
# 	predictor = SentenceLevelPredictor("outputs/mood_model")
# 	text = """I felt really sad when I lost my wallet.
# 	But later I was relieved and happy when someone returned it."""
#
# 	labels, probs, sentences = predictor.predict_paragraph(text)
# 	print("Sentences:", sentences)
# 	print("Paragraph emotions:", labels)
