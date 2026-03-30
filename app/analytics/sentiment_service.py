import os

from newsapi import NewsApiClient


class SentimentAnalyzer:

    def __init__(self):
        key = os.environ.get("NEWSAPI_KEY", "").strip()
        self.newsapi = NewsApiClient(api_key=key) if key else None

    def analyze_sentiment(self, symbol):

        company = symbol

        if not self.newsapi:
            return {
                "symbol": symbol,
                "sentiment_score": 0,
                "signal": "NEUTRAL",
                "headlines": [],
                "error": "NEWSAPI_KEY not configured",
            }

        news = self.newsapi.get_everything(
            q=company,
            language="en",
            sort_by="relevancy",
            page_size=5
        )

        headlines = []

        positive_words = ["gain", "rise", "profit", "growth", "bull"]
        negative_words = ["loss", "fall", "drop", "decline", "bear"]

        score = 0

        for article in news["articles"]:

            title = article["title"]
            headlines.append(title)

            for word in positive_words:
                if word in title.lower():
                    score += 1

            for word in negative_words:
                if word in title.lower():
                    score -= 1

        if score > 1:
            signal = "POSITIVE"
        elif score < -1:
            signal = "NEGATIVE"
        else:
            signal = "NEUTRAL"

        return {
            "symbol": symbol,
            "sentiment_score": score,
            "signal": signal,
            "headlines": headlines
        }