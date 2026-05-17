"""
providers/ — Raw API call modules, one file per data source.

Each provider module is responsible for:
  - Making HTTP requests to one external API
  - Returning raw, lightly cleaned data (dicts/lists)
  - Logging every call and every error
  - Never catching exceptions silently — let services handle fallbacks

Providers do NOT:
  - Cache data (that's the service layer's job)
  - Combine data from multiple sources (that's the service layer's job)
  - Format data for display (that's the UI layer's job)

Modules in this package:
  polygon_provider.py   — live prices, candles, indices, ETFs
  fmp_provider.py       — fundamentals, ratios, estimates, news, analyst grades
  finnhub_provider.py   — market news, company news, earnings calendar, backup prices
  sec_edgar_provider.py — official SEC filings
  fred_provider.py      — macro data (rates, inflation, unemployment)
  gdelt_provider.py     — global event detection
"""
