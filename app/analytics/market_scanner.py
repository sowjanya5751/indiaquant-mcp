import yfinance as yf
import pandas as pd


class MarketScanner:

    def scan_market(self, symbols):

        results = []

        for symbol in symbols:

            ticker = yf.Ticker(symbol)
            data = ticker.history(period="3mo")

            if data.empty:
                continue

            close = data["Close"]
            rsi = self.calculate_rsi(close)

            latest_rsi = rsi.iloc[-1]

            if latest_rsi < 30:
                results.append({
                    "symbol": symbol,
                    "RSI": float(round(latest_rsi, 2)),
                    "signal": "OVERSOLD"
                })

        return results


    def calculate_rsi(self, data, period=14):

        delta = data.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss

        rsi = 100 - (100 / (1 + rs))

        return rsi