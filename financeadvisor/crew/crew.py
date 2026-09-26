"""CrewAI definition for the Finance Advisor flow.

Turns the manual agents (`insight_generator`, `advisor`, etc.) into CrewAI
Agents/Tasks while keeping the existing integrations (cache, LLM).
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Any

# Fix for old SQLite - CrewAI depends on ChromaDB, which needs SQLite 3.35+
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

try:
    from crewai import Agent, Task, Crew, LLM
except Exception:  # pragma: no cover - fallback in environments without crewai
    Agent = object  # type: ignore
    Task = object  # type: ignore
    Crew = object  # type: ignore
    LLM = object  # type: ignore

from .tools import (
    fetch_brapi_data_tool, calc_dividend_metrics_tool, redis_get, get_metrics_from_cache,
    rank_tickers_by_dividend_yield, generate_dividend_pdf
)


def get_llm(provider: str = "gemini"):
    """Configure the LLM to use Gemini or OpenAI.

    Args:
        provider: "gemini" (default) or "openai"
    """
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY is not set in .env")

        return LLM(
            model="gemini/gemini-2.0-flash-exp",
            api_key=api_key,
            temperature=0.7,
        )

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set in .env")

        return LLM(
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0.7,
        )

    else:
        raise ValueError(f"Provider '{provider}' not supported. Use 'gemini' or 'openai'.")


def build_insight_prompt(metrics: Dict[str, float], ticker: str, context: list[str]) -> str:
    lines: list[str] = []
    lines.append(
        f"You are a specialized dividend analyst. Analyze the dividend data of the company {ticker}."
    )
    if context:
        lines.append("Relevant context from previous conversations:\n" + "\n".join(context))

    # Format the metrics in a more readable way
    dividend_yield = metrics.get("dividend_yield", 0)
    current_price = metrics.get("current_price", 0)
    dividends_12m = metrics.get("dividends_12m", 0)
    payment_count = int(metrics.get("payment_count", 0))

    lines.append("\n=== DIVIDEND METRICS ===")
    lines.append(f"• Dividend Yield (last 12 months): {dividend_yield:.2f}%")
    lines.append(f"• Current Price: R$ {current_price:.2f}")
    lines.append(f"• Total Dividends (12 months): R$ {dividends_12m:.2f}")
    lines.append(f"• Number of Payments: {payment_count}")
    lines.append("")
    lines.append("Based on these dividend figures, provide insights about:")
    lines.append("1. The consistency of the dividend payments")
    lines.append("2. The attractiveness of the current dividend yield")
    lines.append("3. The regularity and frequency of the payments")
    lines.append("\nRespond in English, concisely and objectively.")
    return "\n".join(lines)


def build_advisor_prompt(ticker: str, period: str, metrics: Dict[str, float], insights: str, context: list[str]) -> str:
    lines: list[str] = []
    lines.append(
        f"You act as a senior dividend analyst. Analyze the company {ticker} over period {period}."
    )
    if context:
        lines.append("Context from previous conversations:\n" + "\n".join(context))

    lines.append("\n=== DIVIDEND INSIGHTS ===")
    lines.append(insights)

    # Format the metrics
    dividend_yield = metrics.get("dividend_yield", 0)
    current_price = metrics.get("current_price", 0)
    dividends_12m = metrics.get("dividends_12m", 0)
    payment_count = int(metrics.get("payment_count", 0))

    lines.append("\n=== DIVIDEND METRICS ===")
    lines.append(f"• Dividend Yield (last 12 months): {dividend_yield:.2f}%")
    lines.append(f"• Current Price: R$ {current_price:.2f}")
    lines.append(f"• Total Dividends (12 months): R$ {dividends_12m:.2f}")
    lines.append(f"• Number of Payments: {payment_count}")

    lines.append("\n=== RECOMMENDATION CRITERION ===")
    lines.append("Rule: If the Dividend Yield is ABOVE 7% per year, RECOMMEND BUY.")
    lines.append("      If it is BELOW 7% per year, do NOT recommend buying.")
    lines.append("")

    # Clearly indicate whether it is above or below the threshold
    if dividend_yield > 7.0:
        lines.append(f"✓ The dividend yield of {dividend_yield:.2f}% is ABOVE 7%. Recommend BUY.")
    else:
        lines.append(f"✗ The dividend yield of {dividend_yield:.2f}% is BELOW 7%. Do NOT recommend buying.")

    lines.append("")
    lines.append("Based on these figures, write a clear recommendation (BUY, HOLD or SELL) in English.")
    lines.append("Justify your decision concisely, focusing on the dividend yield and the quality of the payments.")
    return "\n".join(lines)


def create_finance_crew(ticker: str, period: str, llm_provider: str = "gemini") -> Crew:
    """Create the Crew with four agents: Data, Metrics, Insight and Advisor.

    Args:
        ticker: Stock code
        period: Analysis period
        llm_provider: "gemini" (default) or "openai"
    """
    llm = get_llm(llm_provider)

    data_agent = Agent(
        role="Data Ingestor",
        goal=f"Fetch brapi.dev data for {ticker} over period {period}",
        backstory="A professional focused on robust, resilient data collection.",
        tools=[fetch_brapi_data_tool, redis_get],
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    metrics_agent = Agent(
        role="Dividend Metrics Calculator",
        goal="Compute dividend yield and related dividend metrics from the data",
        backstory="A quantitative analyst specialized in dividend analysis who computes the dividend yield of the last 12 months.",
        tools=[calc_dividend_metrics_tool],
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    insight_agent = Agent(
        role="Dividend Analyst",
        goal="Generate dividend insights based on metrics",
        backstory=(
            "A specialist in dividend analysis who evaluates the consistency,"
            " regularity and attractiveness of dividend payments."
        ),
        tools=[get_metrics_from_cache],
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    advisor_agent = Agent(
        role="Dividend Advisor",
        goal="Recommend buying if the dividend yield > 7% per year",
        backstory=(
            "An advisor specialized in dividend-focused investing."
            " Recommends BUY when the dividend yield exceeds 7% per year,"
            " also considering the consistency of the payments."
        ),
        tools=[get_metrics_from_cache],
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    data_task = Task(
        description=f"Use the fetch_brapi_data_tool passing ticker='{ticker}' and period='{period}' to fetch and save the data in the cache.",
        expected_output=f"A message confirming that the data for {ticker} was saved to the cache",
        agent=data_agent,
    )

    metrics_task = Task(
        description=(
            f"Use the calc_dividend_metrics_tool passing ticker='{ticker}' and period='{period}' "
            f"to read the data from cache and compute the dividend yield and other metrics. Return the metrics JSON."
        ),
        expected_output="A JSON string with metrics: dividend_yield, current_price, dividends_12m, payment_count",
        agent=metrics_agent,
        context=[data_task],
    )

    insight_task = Task(
        description=(
            f"1. Use get_metrics_from_cache(ticker='{ticker}', period='{period}') to get the dividend metrics. "
            f"2. Analyze: dividend_yield, payment consistency, regularity. "
            f"3. Write an analysis in English about the dividend quality."
        ),
        expected_output="An English text analyzing the company's dividends",
        agent=insight_agent,
        context=[metrics_task],
    )

    advisor_task = Task(
        description=(
            f"1. Use get_metrics_from_cache(ticker='{ticker}', period='{period}') to get the metrics. "
            f"2. CRITICAL RULE: If dividend_yield > 7%, recommend BUY. Otherwise, do NOT recommend buying. "
            f"3. Write a clear recommendation (BUY/HOLD/SELL) in English, "
            f"justifying it based on the dividend yield and payment quality."
        ),
        expected_output="A final recommendation in English (BUY if DY > 7%)",
        agent=advisor_agent,
        context=[metrics_task, insight_task],
    )

    crew = Crew(
        agents=[data_agent, metrics_agent, insight_agent, advisor_agent],
        tasks=[data_task, metrics_task, insight_task, advisor_task],
        verbose=True,
    )
    return crew


def run_insights(ticker: str, period: str, metrics: Dict[str, float]) -> str:
    """Run only the insights task using the cache-backed tools."""
    cache_key = f"insights:{ticker}:{period}"
    prompt = build_insight_prompt(metrics, ticker, [])
    insights = cache_get_or_compute.run(cache_key, compute_prompt=prompt)  # type: ignore[attr-defined]
    return str(insights)


def run_recommendation(ticker: str, period: str, metrics: Dict[str, float], insights: str) -> str:
    """Run only the recommendation task using the cache-backed tools."""
    cache_key = f"recommendation:{ticker}:{period}"
    prompt = build_advisor_prompt(ticker, period, metrics, insights, [])
    text = cache_get_or_compute.run(cache_key, compute_prompt=prompt)  # type: ignore[attr-defined]
    return str(text)


def create_multi_ticker_crew(tickers: list[str], period: str, llm_provider: str = "gemini") -> Crew:
    """
    Create a Crew that analyzes multiple tickers, compares them and generates a PDF.

    Flow:
    1. For each ticker: Data -> Metrics
    2. Comparator: builds a ranking by dividend yield
    3. PDF generator: creates a professional report

    Args:
        tickers: List of tickers to analyze (e.g. ["PETR4", "VALE3", "ITUB4", "BBDC4"])
        period: Analysis period
        llm_provider: "gemini" (default) or "openai"
    """
    llm = get_llm(llm_provider)

    all_agents = []
    all_tasks = []

    # Create data and metrics agents for each ticker
    for ticker in tickers:
        data_agent = Agent(
            role=f"Data Ingestor - {ticker}",
            goal=f"Fetch brapi.dev data for {ticker} over period {period}",
            backstory=f"A specialist in collecting {ticker} data.",
            tools=[fetch_brapi_data_tool],
            verbose=True,
            allow_delegation=False,
            llm=llm,
        )

        metrics_agent = Agent(
            role=f"Metrics Calculator - {ticker}",
            goal=f"Compute the dividend yield for {ticker}",
            backstory=f"A quantitative analyst specialized in {ticker} dividends.",
            tools=[calc_dividend_metrics_tool],
            verbose=True,
            allow_delegation=False,
            llm=llm,
        )

        data_task = Task(
            description=f"Use fetch_brapi_data_tool with ticker='{ticker}' and period='{period}'",
            expected_output=f"Confirmation that {ticker} data was saved",
            agent=data_agent,
        )

        metrics_task = Task(
            description=f"Use calc_dividend_metrics_tool with ticker='{ticker}' and period='{period}'",
            expected_output=f"JSON with dividend metrics for {ticker}",
            agent=metrics_agent,
            context=[data_task],
        )

        all_agents.extend([data_agent, metrics_agent])
        all_tasks.extend([data_task, metrics_task])

    # Comparator agent
    comparator_agent = Agent(
        role="Dividend Comparator",
        goal="Compare dividend yields and build a recommendation ranking",
        backstory=(
            "A specialist in comparative stock analysis who identifies the best "
            "dividend-focused investment opportunities."
        ),
        tools=[rank_tickers_by_dividend_yield],
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    tickers_str = ",".join(tickers)
    comparator_task = Task(
        description=(
            f"1. Use rank_tickers_by_dividend_yield with tickers_list='{tickers_str}' and period='{period}' "
            f"2. Analyze the returned ranking and identify the best opportunities "
            f"3. Return the full ranking JSON"
        ),
        expected_output="JSON with a ranking ordered by dividend yield",
        agent=comparator_agent,
        context=all_tasks,  # Depends on all metrics tasks
    )

    # PDF generator agent
    pdf_agent = Agent(
        role="Report Generator",
        goal="Create a professional PDF report with the comparative analysis",
        backstory=(
            "A specialist in financial communication who turns technical analyses "
            "into clear, professional visual reports."
        ),
        tools=[generate_dividend_pdf],
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    pdf_task = Task(
        description=(
            f"1. Receive the ranking JSON from the previous task "
            f"2. Use generate_dividend_pdf passing the ranking as 'content' "
            f"3. Use the file name 'ranking_dividends_{period}.pdf' "
            f"4. Return the success message with the file path"
        ),
        expected_output="Path of the generated PDF file",
        agent=pdf_agent,
        context=[comparator_task],
    )

    all_agents.extend([comparator_agent, pdf_agent])
    all_tasks.extend([comparator_task, pdf_task])

    crew = Crew(
        agents=all_agents,
        tasks=all_tasks,
        verbose=True,
    )

    return crew
