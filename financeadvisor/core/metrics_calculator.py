"""
Financial metrics computation agent.

This module defines functions to compute quantitative indicators from the raw
data fetched from brapi.dev. In the proposed architecture these functions are
used by the metrics worker (`workers/metrics_worker.py`), but they can be
called in other contexts (for example, for manual testing).

The implemented metrics are illustrative: dividend yield and related figures
over a series of dividend payments. You can add other metrics (CAGR, gross
margin, ROE, etc.) as needed. The result is stored in Redis for reuse.
"""
from typing import Any, Dict, List
from datetime import datetime, timedelta

try:
    import numpy as np  # type: ignore
    import pandas as pd  # type: ignore
except Exception:
    np = None  # type: ignore
    pd = None  # type: ignore

from ..utils.cache import get_redis_connection


def _extract_dividends(brapi_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract dividend data from the brapi result.

    Args:
        brapi_result: brapi API result containing dividendsData

    Returns:
        List of paid dividends (cashDividends)
    """
    dividends_data = brapi_result.get("dividendsData", {})
    cash_dividends = dividends_data.get("cashDividends", [])
    return cash_dividends if isinstance(cash_dividends, list) else []


def _calculate_dividend_yield(brapi_result: Dict[str, Any]) -> float:
    """Compute the annual dividend yield based on the last 12 months.

    Args:
        brapi_result: brapi API result

    Returns:
        Annual dividend yield as a percentage (e.g. 7.5 for 7.5%)
    """
    from datetime import timezone

    # Get the current price
    current_price = brapi_result.get("regularMarketPrice")
    if not current_price or current_price <= 0:
        return 0.0

    # Get the dividends
    dividends = _extract_dividends(brapi_result)
    if not dividends:
        return 0.0

    # Filter dividends from the last 12 months (timezone-aware)
    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)

    total_dividends = 0.0
    for div in dividends:
        payment_date_str = div.get("paymentDate")
        if not payment_date_str:
            continue

        try:
            # Parse ISO format: "2025-09-22T00:00:00.000Z"
            payment_date = datetime.fromisoformat(payment_date_str.replace("Z", "+00:00"))

            # If the payment was within the last 12 months
            if payment_date >= one_year_ago and payment_date <= now:
                rate = div.get("rate", 0)
                if rate:
                    total_dividends += float(rate)
        except Exception:
            # Ignore dividends with an invalid date
            continue

    # Compute dividend yield: (annual dividends / price) * 100
    dividend_yield = (total_dividends / current_price) * 100
    return round(dividend_yield, 2)


def calc_metrics_from_raw(data_json: Dict[str, Any]) -> Dict[str, float]:
    """Compute simple metrics from the brapi JSON.

    Args:
        data_json (dict): brapi JSON response containing `results[0]` with a
            `historicalDataPrice` field (list of objects with 'close') and
            dividend data.

    Returns:
        dict: dictionary with computed metrics, including dividend_yield.
    """
    # Extract the first returned stock
    try:
        result0 = data_json["results"][0]
    except (KeyError, IndexError):
        raise ValueError("Unexpected brapi.dev data format: 'results[0]' field missing")

    import os as _os
    if _os.getenv("DEBUG_METRICS") == "1":
        print(data_json)

    # Compute dividend yield (main metric for a dividend analyst)
    dividend_yield = _calculate_dividend_yield(result0)

    # Compute current price and basic info
    current_price = result0.get("regularMarketPrice", 0.0)
    ticker = result0.get("symbol", "N/A")
    company_name = result0.get("shortName", "N/A")

    # Compute total dividends over the last 12 months
    from datetime import timezone

    dividends = _extract_dividends(result0)
    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)

    total_dividends_12m = 0.0
    dividend_count = 0

    for div in dividends:
        payment_date_str = div.get("paymentDate")
        if not payment_date_str:
            continue

        try:
            payment_date = datetime.fromisoformat(payment_date_str.replace("Z", "+00:00"))
            if payment_date >= one_year_ago and payment_date <= now:
                rate = div.get("rate", 0)
                if rate:
                    total_dividends_12m += float(rate)
                    dividend_count += 1
        except Exception:
            continue

    return {
        "dividend_yield": dividend_yield,
        "current_price": float(current_price),
        "dividends_12m": round(total_dividends_12m, 2),
        "payment_count": float(dividend_count),
    }


def store_metrics_in_cache(ticker: str, period: str, metrics: Dict[str, float], ttl: int = 86400) -> None:
    """Store metrics in Redis for future use.

    Args:
        ticker (str): asset code.
        period (str): analyzed range.
        metrics (dict): dictionary with computed metrics.
        ttl (int): time to live in seconds (default 24h).
    """
    import json
    r = get_redis_connection()
    key = f"metrics:{ticker}:{period}"
    r.set(key, json.dumps(metrics), ex=ttl)


def enqueue_metrics_calculation(ticker: str, period: str) -> None:
    """Kept for compatibility: does nothing in the synchronous flow."""
    return None
