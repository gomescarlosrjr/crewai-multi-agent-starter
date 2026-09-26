"""
Orchestrator of the financial analysis system.

This module centralizes the workflow that serves user requests. It coordinates
the different stages:

* Per-user rate limiting via Redis
* Data ingestion: dispatches work to the ingestion agent
* Metric computation: dispatches work to the metrics agent
* Insight generation via LLM with RAG support
* Final recommendation generation

The orchestrator manages caching: if data or metrics are already available in
Redis, it avoids re-dispatching tasks. It also does simple polling to wait for
the asynchronous stages to complete, with a configurable timeout.

It also records the interaction (user question and system answer) in the vector
database so the RAG mechanism can retrieve relevant context in future
interactions.

Typical usage::

    from agents.orchestrator import analyze
    response = analyze("PETR4", "1y", "Analyze the company PETR4", user_id="alice")
    print(response)

For real applications you can integrate this function with a web framework
(FastAPI, Flask, etc.) or a CLI to receive user requests.
"""
import logging

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None  # type: ignore

from ..utils.cache import check_rate_limit
from ..crew.crew import create_finance_crew, create_multi_ticker_crew


# Load .env variables if the library is available
if load_dotenv:
    load_dotenv()


def analyze(ticker: str, period: str, user_question: str, user_id: str = "anon", llm_provider: str = "gemini") -> str:
    """Run the full analysis for a stock and period using CrewAI.

    This method orchestrates the whole flow through CrewAI: it applies rate
    limiting and delegates all the work (data fetching, metric computation,
    insight generation and recommendation) to the Crew's agents.

    Args:
        ticker (str): asset code (e.g. PETR4).
        period (str): range (e.g. 1y, 6mo, 1mo, etc.).
        user_question (str): the user's original question (for storage in
            vector memory).
        user_id (str): unique user identifier for rate limiting.
        llm_provider (str): "gemini" (default) or "openai" to pick the LLM.

    Returns:
        str: response combining the insights and recommendation produced by the Crew.

    Raises:
        Exception: if the rate limit is exceeded or the Crew fails.
    """
    # Check the request limit
    check_rate_limit(user_id)

    logging.info(f"Processing request for {ticker} over period {period}")
    print(f"Processing request for {ticker} over period {period}")

    # Create and run the Crew - THE AGENTS DO ALL THE WORK
    try:
        crew = create_finance_crew(ticker, period, llm_provider)
        result = crew.kickoff()

        # The result may be a string or a CrewOutput object
        if hasattr(result, 'raw'):
            response = str(result.raw)
        else:
            response = str(result)

    except Exception as e:
        logging.error(f"Error running the Crew: {e}")
        raise Exception(f"CrewAI analysis failed: {e}")

    return response


def analyze_multi_tickers(tickers: list[str], period: str, user_question: str,
                          user_id: str = "anon", llm_provider: str = "gemini") -> str:
    """Run a comparative analysis for multiple tickers using CrewAI.

    This method orchestrates the analysis of multiple tickers, compares their
    dividend yields and generates a PDF with the recommendation ranking.

    Args:
        tickers (list[str]): list of asset codes (e.g. ["PETR4", "VALE3", "ITUB4", "BBDC4"]).
        period (str): range (e.g. 1y, 6mo, 1mo, etc.).
        user_question (str): the user's original question (for storage in
            vector memory).
        user_id (str): unique user identifier for rate limiting.
        llm_provider (str): "gemini" (default) or "openai" to pick the LLM.

    Returns:
        str: response with the ranking and the path of the generated PDF.

    Raises:
        Exception: if the rate limit is exceeded or the Crew fails.
    """
    # Check the request limit
    check_rate_limit(user_id)

    tickers_str = ", ".join(tickers)
    logging.info(f"Processing comparative analysis for {tickers_str} over period {period}")
    print(f"Processing comparative analysis for {tickers_str} over period {period}")

    # Create and run the Crew - THE AGENTS DO ALL THE WORK
    try:
        crew = create_multi_ticker_crew(tickers, period, llm_provider)
        result = crew.kickoff()

        # The result may be a string or a CrewOutput object
        if hasattr(result, 'raw'):
            response = str(result.raw)
        else:
            response = str(result)

    except Exception as e:
        logging.error(f"Error running the multi-ticker Crew: {e}")
        raise Exception(f"CrewAI comparative analysis failed: {e}")

    return response
