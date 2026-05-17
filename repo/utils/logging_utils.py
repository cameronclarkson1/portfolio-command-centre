"""
logging_utils.py — Structured logging for providers and services.

Every time a provider is called, a fallback is triggered, or a cache is
hit/missed, it gets logged here. This gives you an audit trail of exactly
where each piece of data came from.

Usage:
    from utils.logging_utils import get_logger
    log = get_logger(__name__)
    log.info("fetching price for MSFT")
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with consistent formatting."""
    logger = logging.getLogger(name)

    # Only add handler once — prevents duplicate log lines in Streamlit
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


# ─── Convenience log helpers used by providers and services ──────────────────

def log_provider_call(logger: logging.Logger, provider: str, endpoint: str, ticker: str = ""):
    tag = f" [{ticker}]" if ticker else ""
    logger.info(f"→ {provider}{tag}  {endpoint}")


def log_fallback(logger: logging.Logger, failed: str, next_up: str, reason: str = ""):
    note = f" ({reason})" if reason else ""
    logger.warning(f"  {failed} failed{note} — trying {next_up}")


def log_cache_hit(logger: logging.Logger, key: str):
    logger.debug(f"  cache HIT  {key}")


def log_cache_miss(logger: logging.Logger, key: str):
    logger.debug(f"  cache MISS {key}")


def log_confidence(logger: logging.Logger, ticker: str, score: float, source: str):
    logger.info(f"  confidence {score:.0f}%  [{ticker}]  source={source}")
