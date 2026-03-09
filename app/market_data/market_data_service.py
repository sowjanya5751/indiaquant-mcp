import yfinance as yf


class MarketDataService:

    def get_live_price(self, symbol: str):
        """
        Fetch live NSE stock price using Yahoo Finance
        """

        ticker_symbol = f"{symbol}.NS"

        ticker = yf.Ticker(ticker_symbol)

        info = ticker.history(period="1d", interval="1m")

        if info.empty:
            return {
                "error": "No data found for symbol"
            }

        latest = info.iloc[-1]

        open_price = info.iloc[0]["Open"]
        current_price = latest["Close"]

        change_percent = ((current_price - open_price) / open_price) * 100

        volume = int(latest["Volume"])

        return {
            "symbol": symbol,
            "price": float(round(current_price, 2)),
            "change_percent": float(round(change_percent, 2)),
            "volume": int(volume)
        }