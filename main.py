from app.market_data.market_data_service import MarketDataService
from app.signals.signal_service import SignalEngine
from app.options.options_service import OptionsAnalyzer
from app.analytics.greeks_calculator import GreeksCalculator
from app.portfolio.portfolio_service import PortfolioService

if __name__ == "__main__":

    market = MarketDataService()
    signal_engine = SignalEngine()

    print("Live Price:")
    print(market.get_live_price("RELIANCE"))

    print("\nTrade Signal:")
    print(signal_engine.generate_signal("RELIANCE"))

    options = OptionsAnalyzer()

    print("\nOptions Chain:")
    print(options.get_options_chain("TSLA"))

    print("\nMax Pain:")
    print(options.calculate_max_pain("TSLA"))
    greeks = GreeksCalculator()

    print("\nGreeks Calculation:")
    print(
        greeks.calculate_greeks(
            S=200,
            K=210,
            T=30/365,
            r=0.05,
            sigma=0.2
        )
    )
    portfolio = PortfolioService()

    print("\nPlacing Virtual Trade:")
    print(portfolio.place_virtual_trade("RELIANCE", 5))

    print("\nPortfolio PnL:")
    print(portfolio.get_portfolio_pnl())
