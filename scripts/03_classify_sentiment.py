"""Point d'entrée CLI pour la classification de sentiment batch.

Délègue à scripts.classify_sentiment_03.classify_sentiment().
"""

from scripts.classify_sentiment_03 import classify_sentiment

if __name__ == "__main__":
    classify_sentiment()
