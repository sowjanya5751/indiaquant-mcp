from newsapi import NewsApiClient


class SentimentAnalyzer:

    def __init__(self):
        self.newsapi = NewsApiClient(api_key="5fe242b84e4c40cba1786ebf844c26b4")

    def analyze_sentiment(self, symbol):

        company = symbol

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