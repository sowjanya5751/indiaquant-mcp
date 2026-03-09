import yfinance as yf


class SectorHeatmap:

    sectors = {
        "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS"],
        "BANKING": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
        "ENERGY": ["RELIANCE.NS", "ONGC.NS"],
        "AUTO": ["TATAMOTORS.NS", "MARUTI.NS"]
    }

    def get_sector_heatmap(self):

        heatmap = []

        for sector, stocks in self.sectors.items():

            changes = []

            for stock in stocks:

                ticker = yf.Ticker(stock)

                data = ticker.history(period="2d")

                if len(data) < 2:
                    continue

                prev = data["Close"].iloc[-2]
                latest = data["Close"].iloc[-1]

                change = ((latest - prev) / prev) * 100

                changes.append(change)

            if changes:

                avg_change = sum(changes) / len(changes)

                heatmap.append({
                    "sector": sector,
                    "change_percent": round(avg_change, 2)
                })

        return heatmap