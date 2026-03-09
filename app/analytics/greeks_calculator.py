import math


class GreeksCalculator:

    def _norm_pdf(self, x):
        return (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x ** 2)

    def _norm_cdf(self, x):
        return (1 + math.erf(x / math.sqrt(2))) / 2

    def calculate_greeks(self, S, K, T, r, sigma, option_type="call"):
        """
        Black-Scholes Greeks

        S = current stock price
        K = strike price
        T = time to expiry (years)
        r = risk-free rate
        sigma = volatility
        """

        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        if option_type == "call":
            delta = self._norm_cdf(d1)
        else:
            delta = self._norm_cdf(d1) - 1

        gamma = self._norm_pdf(d1) / (S * sigma * math.sqrt(T))

        vega = S * self._norm_pdf(d1) * math.sqrt(T) / 100

        if option_type == "call":
            theta = (
                -(S * self._norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
                - r * K * math.exp(-r * T) * self._norm_cdf(d2)
            ) / 365
        else:
            theta = (
                -(S * self._norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
                + r * K * math.exp(-r * T) * self._norm_cdf(-d2)
            ) / 365

        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 6),
            "vega": round(vega, 6)
        }