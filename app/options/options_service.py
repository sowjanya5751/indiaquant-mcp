import yfinance as yf
import pandas as pd


class OptionsAnalyzer:

    def get_options_chain(self, symbol: str):

        if symbol.endswith(".NS") or symbol.startswith("^"):
            ticker_symbol = symbol
        else:
            ticker_symbol = symbol
        ticker = yf.Ticker(ticker_symbol)

        expiries = ticker.options

        if not expiries:
            return {
                "error": f"No options data available for {symbol}"
            }

        expiry = expiries[0]

        chain = ticker.option_chain(expiry)

        calls = chain.calls
        puts = chain.puts

        data = []

        for i in range(len(calls)):

            strike = calls.iloc[i]["strike"]

            call_oi = calls.iloc[i]["openInterest"]
            put_oi = puts.iloc[i]["openInterest"]

            data.append({
                "strike": strike,
                "call_oi": int(call_oi),
                "put_oi": int(put_oi)
            })

        return {
            "symbol": symbol,
            "expiry": expiry,
            "options": data[:10]   # limit output
        }

    def calculate_max_pain(self, symbol: str):

        if symbol.endswith(".NS") or symbol.startswith("^"):
            ticker_symbol = symbol
        else:
            ticker_symbol = symbol
        ticker = yf.Ticker(ticker_symbol)

        expiries = ticker.options

        if not expiries:
            return {
                "error": f"No options data available for {symbol}"
            }

        expiry = expiries[0]

        chain = ticker.option_chain(expiry)

        calls = chain.calls
        puts = chain.puts

        strikes = calls["strike"].values

        pain = {}

        for strike in strikes:

            total_loss = 0

            for i in range(len(strikes)):

                call_oi = calls.iloc[i]["openInterest"]
                put_oi = puts.iloc[i]["openInterest"]

                call_loss = max(0, strike - strikes[i]) * call_oi
                put_loss = max(0, strikes[i] - strike) * put_oi

                total_loss += call_loss + put_loss

            pain[strike] = total_loss

        max_pain = min(pain, key=pain.get)

        return {
            "symbol": symbol,
            "expiry": expiry,
            "max_pain": float(max_pain)
        }

    def detect_unusual_activity(self, symbol: str):

        if symbol.startswith("^") or "." in symbol:
            ticker_symbol = symbol
        else:
            ticker_symbol = f"{symbol}.NS"

        ticker = yf.Ticker(ticker_symbol)

        expiries = ticker.options

        if not expiries:
            return {"error": "No options data"}

        expiry = expiries[0]

        chain = ticker.option_chain(expiry)

        calls = chain.calls
        puts = chain.puts

        unusual = []

        for i in range(len(calls)):

            strike = calls.iloc[i]["strike"]

            call_vol = calls.iloc[i]["volume"]
            call_oi = calls.iloc[i]["openInterest"]

            put_vol = puts.iloc[i]["volume"]
            put_oi = puts.iloc[i]["openInterest"]

            if call_vol > call_oi * 2:
                unusual.append({
                    "type": "CALL",
                    "strike": float(strike),
                    "volume": int(call_vol),
                    "open_interest": int(call_oi)
                })

            if put_vol > put_oi * 2:
                unusual.append({
                    "type": "PUT",
                    "strike": float(strike),
                    "volume": int(put_vol),
                    "open_interest": int(put_oi)
                })

        return {
            "symbol": symbol,
            "expiry": expiry,
            "alerts": unusual[:10]
        }