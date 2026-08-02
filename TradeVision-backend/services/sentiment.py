# pyrefly: ignore [missing-import]
from transformers import pipeline

class SentimentAnalyzer:
    def __init__(self):
        # Using ProsusAI/finbert, a popular model for financial sentiment analysis
        self.pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")

    def analyze_text(self, text: str) -> dict:
        """
        Analyzes the financial sentiment of a given text.
        Returns a dictionary with the sentiment_score (-1.0 to 1.0) and raw_scores.
        """
        if not text or not text.strip():
            return {"sentiment_score": 0.0, "raw_scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0}}

        try:
            # FinBERT processes max 512 tokens. We truncate the text roughly by characters to avoid errors.
            truncated_text = text[:1500] 
            
            # top_k=None returns probabilities for all classes (positive, negative, neutral)
            results = self.pipeline(truncated_text, top_k=None)
            
            # Handle list structure depending on transformers version
            scores = results[0] if isinstance(results[0], list) else results
            
            raw_scores = {item['label']: item['score'] for item in scores}
            
            # Calculate a final score between -1.0 and 1.0
            pos = raw_scores.get('positive', 0.0)
            neg = raw_scores.get('negative', 0.0)
            
            sentiment_score = pos - neg
            
            return {
                "sentiment_score": round(sentiment_score, 4),
                "raw_scores": raw_scores
            }
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {"sentiment_score": 0.0, "raw_scores": {"error": str(e)}}
