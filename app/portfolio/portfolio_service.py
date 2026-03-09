import sqlite3
from app.market_data.market_data_service import MarketDataService


class PortfolioService:

    def __init__(self):

        self.conn = sqlite3.connect("portfolio.db", check_same_thread=False)
        self.cursor = self.conn.cursor()

        self.market = MarketDataService()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            qty INTEGER,
            side TEXT,
            price REAL
        )
        """)

        self.conn.commit()

    def place_trade(self, symbol, qty, side):

        price_data = self.market.get_live_price(symbol)

        price = price_data["price"]

        self.cursor.execute(
            "INSERT INTO positions (symbol, qty, side, price) VALUES (?, ?, ?, ?)",
            (symbol, qty, side, price)
        )

        self.conn.commit()

        return {
            "status": "executed",
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "price": price
        }

    def get_portfolio_pnl(self):

        self.cursor.execute("SELECT symbol, qty, side, price FROM positions")

        rows = self.cursor.fetchall()

        total_pnl = 0
        positions = []

        for symbol, qty, side, entry_price in rows:

            live_price = self.market.get_live_price(symbol)["price"]

            if side == "BUY":
                pnl = (live_price - entry_price) * qty
            else:
                pnl = (entry_price - live_price) * qty

            total_pnl += pnl

            positions.append({
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "entry_price": entry_price,
                "live_price": live_price,
                "pnl": pnl
            })

        return {
            "positions": positions,
            "total_pnl": total_pnl
        }