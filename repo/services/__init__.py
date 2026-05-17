"""
services/ — Data service modules that pages call directly.

Common helper used by every service module:
  _try_providers(providers_and_fns, label) → (data, source_name, fallback_used)

This keeps the fallback logic identical across all services — try each provider
in order, log warnings on failure, return the first success.
"""

from utils.logging_utils import get_logger, log_fallback

_log = get_logger("services")


def _try_providers(providers_and_fns: list, label: str = "") -> tuple:
    """
    Try a list of (provider_name, callable) pairs in order.
    Returns the first successful result.

    Args:
        providers_and_fns: List of ("polygon", lambda: polygon.get_snapshot("MSFT"))
        label:             Human-readable description for log messages, e.g. "MSFT price"

    Returns:
        (data, provider_name, fallback_used)
        data is None if every provider failed.
    """
    for i, (name, fn) in enumerate(providers_and_fns):
        try:
            result = fn()
            if result is not None:
                fallback_used = (i > 0)
                if fallback_used:
                    _log.info(f"  {label}: using fallback provider '{name}'")
                return result, name, fallback_used
        except Exception as e:
            if i < len(providers_and_fns) - 1:
                next_name = providers_and_fns[i + 1][0]
                log_fallback(_log, name, next_name, str(e)[:80])
            else:
                _log.error(f"All providers failed for {label}: {e}")

    return None, "none", True
