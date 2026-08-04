# pyrefly: ignore [missing-import]
from transformers import pipeline

class SentimentAnalyzer:
    def __init__(self):
        # Using ProsusAI/finbert, a popular model for financial sentiment analysis
        self.pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")

    def analyze_text(self, text: str) -> dict:
        """
        Analyzes the financial sentiment of a given text.

        Returns a dict with:
            ok:              True if the model produced a real score.
            sentiment_score: -1.0 to 1.0, or None when ok is False.
            raw_scores:      per-class probabilities (empty when ok is False).
            error:           reason string, only present when ok is False.

        Callers MUST check `ok` and exclude failures from any average. A failed
        analysis is not neutral sentiment — averaging 0.0 for it would read as
        "confidently neutral coverage" when in fact nothing was measured.
        """
        if not text or not text.strip():
            return {
                "ok": False,
                "sentiment_score": None,
                "raw_scores": {},
                "error": "empty_text",
            }

        try:
            # Let the tokenizer enforce FinBERT's real 512-token limit.
            # A character cap cannot do this: text dense with numbers, tickers
            # and punctuation tokenizes far worse than prose, so a "safe" slice
            # can still overflow and raise.
            results = self.pipeline(
                text,
                top_k=None,
                truncation=True,
                max_length=512,
            )

            # Handle list structure depending on transformers version
            scores = results[0] if isinstance(results[0], list) else results

            raw_scores = {item['label']: item['score'] for item in scores}

            pos = raw_scores.get('positive', 0.0)
            neg = raw_scores.get('negative', 0.0)

            return {
                "ok": True,
                "sentiment_score": round(pos - neg, 4),
                "raw_scores": raw_scores,
            }
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {
                "ok": False,
                "sentiment_score": None,
                "raw_scores": {},
                "error": str(e),
            }
