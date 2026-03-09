import yfinance as yf
import pandas as pd
import numpy as np


class SignalEngine:

    def calculate_rsi(self, data, period=14):
        delta = data.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi


    def calculate_macd(self, data):

        ema12 = data.ewm(span=12, adjust=False).mean()
        ema26 = data.ewm(span=26, adjust=False).mean()

        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()

        return macd, signal


    def calculate_bollinger(self, data):

        sma = data.rolling(window=20).mean()
        std = data.rolling(window=20).std()

        upper = sma + (2 * std)
        lower = sma - (2 * std)

        return upper, lower


    def generate_signal(self, symbol: str):

        ticker_symbol = f"{symbol}.NS"
        ticker = yf.Ticker(ticker_symbol)

        data = ticker.history(period="3mo")

        if data.empty:
            return {"error": "No data available"}

        close = data["Close"]

        data["RSI"] = self.calculate_rsi(close)

        macd, macd_signal = self.calculate_macd(close)
        data["MACD"] = macd
        data["MACD_SIGNAL"] = macd_signal

        upper, lower = self.calculate_bollinger(close)
        data["BB_UPPER"] = upper
        data["BB_LOWER"] = lower

        latest = data.iloc[-1]

        rsi = latest["RSI"]
        macd_val = latest["MACD"]
        macd_sig = latest["MACD_SIGNAL"]
        price = latest["Close"]
        bb_upper = latest["BB_UPPER"]
        bb_lower = latest["BB_LOWER"]

        score = 0

        # RSI logic
        if rsi < 30:
            score += 30
        elif rsi > 70:
            score -= 30

        # MACD logic
        if macd_val > macd_sig:
            score += 40
        else:
            score -= 40

        # Bollinger logic
        if price < bb_lower:
            score += 30
        elif price > bb_upper:
            score -= 30

        if score > 30:
            signal = "BUY"
        elif score < -30:
            signal = "SELL"
        else:
            signal = "HOLD"

        confidence = min(abs(score), 100)

        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "indicators": {
                "RSI": float(round(rsi, 2)),
                "MACD": float(round(macd_val, 4)),
                "MACD_SIGNAL": float(round(macd_sig, 4))
            }
        }