"""
benzinga_provider.py — REMOVED.

Benzinga has been replaced by free alternatives:
  - News:            Finnhub company news  →  fmp.get_stock_news()
  - Market news:     finnhub.get_market_news()
  - Analyst ratings: fmp.get_analyst_grades()
  - Earnings:        finnhub.get_earnings_calendar()

See news_service.py for the updated fallback chains.
"""

raise ImportError(
    "benzinga_provider has been removed. "
    "Use finnhub_provider and fmp_provider instead. "
    "See news_service.py for details."
)
