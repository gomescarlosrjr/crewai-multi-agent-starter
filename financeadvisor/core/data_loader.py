"""
Data ingestion agent (DataLoader).

This module contains functions for fetching data from the brapi.dev API.
In the simplified flow, ingestion is synchronous: we fetch the brapi JSON
and may store it in Redis under the key `rawdata:ticker:period` for reuse.

For local testing, call `fetch_brapi_data` directly.
"""
import os
from typing import Any, Dict

import requests
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

from ..utils.cache import get_redis_connection

if load_dotenv:
    load_dotenv()


def build_brapi_url(ticker: str, period: str) -> str:
    """Build the brapi.dev API URL with the parameters of interest.

    We use the `range`, `fundamental=true` and `dividends=true` parameters to
    fetch price data, fundamental data and dividends, respectively. Adjust as
    needed for your project (e.g. add modules via the `modules` parameter).
    """
    base_url = f"https://brapi.dev/api/quote/{ticker}"
    params = {
        "range": period,
        "fundamental": "true",
        "dividends": "true",
    }
    token = os.getenv("BRAPI_TOKEN")
    if token:
        params["token"] = token
    # Concatenate parameters into the URL
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query}"


def build_brapi_history_url(ticker: str, period: str) -> str:
    """Build the URL for brapi.dev's daily-history endpoint.

    E.g.: https://brapi.dev/api/quote/PETR4?range=1y
    """
    base_url = f"https://brapi.dev/api/quote/{ticker}"
    params = {
        "range": period,
    }
    token = os.getenv("BRAPI_TOKEN")
    if token:
        params["token"] = token
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query}"


def fetch_brapi_data(ticker: str, period: str) -> Dict[str, Any]:
    """Make an HTTP request to brapi.dev and return the JSON.

    This function is used by the ingestion worker. If you prefer to run local
    tests without queues, you can call it directly.

    Args:
        ticker (str): asset code (e.g. 'PETR4').
        period (str): range (e.g. '1mo', '1y').

    Returns:
        dict: brapi's JSON response
    """
    # Fake mode for bootcamp/offline testing
    if os.getenv("FAKE_DATA") == "1":
        return {
            "results": [
                {
                    "historicalDataPrice": [
                        {"close": 10.0},
                        {"close": 10.2},
                        {"close": 10.1},
                        {"close": 10.5},
                    ]
                }
            ]
        }
    url = build_brapi_url(ticker, period)
    # Headers to avoid error 417 (Expectation Failed)
    headers = {
        'User-Agent': 'FinanceAdvisor/1.0',
        'Accept': 'application/json',
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    # If the response has no time series, try the /history endpoint and inject into results[0]
    try:
        result0 = data.get("results", [])[0]
    except Exception:
        result0 = None
    has_history = False
    if isinstance(result0, dict):
        series = result0.get("historicalDataPrice") or result0.get("historicalData") or result0.get("prices")
        has_history = isinstance(series, list) and len(series) > 0
    if not has_history:
        hurl = build_brapi_history_url(ticker, period)
        hresp = requests.get(hurl, headers=headers)
        hresp.raise_for_status()
        hjson = hresp.json() or {}
        prices = hjson.get("prices") or hjson.get("historicalDataPrice") or []
        if isinstance(result0, dict):
            result0["prices"] = prices
        elif isinstance(data.get("results"), list) and data["results"]:
            data["results"][0] = {"prices": prices}
        else:
            data = {"results": [{"prices": prices}]}
    return data


def enqueue_ingestion(ticker: str, period: str) -> None:
    """Kept for compatibility: does nothing in the synchronous flow."""
    return None


def get_rawdata_from_cache(ticker: str, period: str):
    """Retrieve raw data from Redis if cached.

    Args:
        ticker (str): asset code.
        period (str): range.

    Returns:
        dict or None: JSON if present in cache, otherwise None.
    """
    r = get_redis_connection()
    key = f"rawdata:{ticker}:{period}"
    data = r.get(key)
    if data:
        import json
        return json.loads(data)
    return None
