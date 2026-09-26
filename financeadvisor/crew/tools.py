"""
CrewAI tools that wrap the existing integrations (Redis cache and LLM).
These tools are called by CrewAI Agents/Tasks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..utils.cache import get_or_set_cache, get_redis_connection
from ..utils.llm_client import generate_content

try:
    # Optional imports in case CrewAI is not installed in the reader's environment
    from crewai.tools import tool
except Exception:  # pragma: no cover - fallback in environments without crewai
    def tool(*dargs, **dkwargs):  # type: ignore
        # Supports @tool and @tool("description")
        if dargs and callable(dargs[0]) and len(dargs) == 1 and not dkwargs:
            func = dargs[0]
            return _make_fake_tool(func)
        def decorator(func):
            return _make_fake_tool(func)
        return decorator

    def _make_fake_tool(func):  # type: ignore
        class FakeTool:
            def __init__(self, f):
                self._f = f
            def run(self, *args, **kwargs):
                return self._f(*args, **kwargs)
            def __call__(self, *args, **kwargs):
                return self._f(*args, **kwargs)
        return FakeTool(func)


@tool("Get a value from Redis or compute and store it with a TTL")
def cache_get_or_compute(key: str, compute_prompt: str = "") -> str:
    """
    Implements the cache-aside pattern. When `compute_prompt` is provided,
    it generates the content via the LLM and stores it; otherwise it returns
    the raw value.
    """
    def _compute() -> Any:
        if not compute_prompt:
            return ""
        return generate_content(compute_prompt)

    result = get_or_set_cache(key, _compute)
    if isinstance(result, (dict, list)):
        import json as _json
        return _json.dumps(result)
    return str(result)


@tool("Read a raw string from a Redis key (no JSON)")
def redis_get(key: str) -> str:
    """Return the raw (string) value of a Redis key without deserializing JSON."""
    r = get_redis_connection()
    result = r.get(key)
    return result if result else ""


@tool("Fetch data from the brapi.dev API and save it to the cache")
def fetch_brapi_data_tool(ticker: str, period: str) -> str:
    """Fetch raw data from brapi.dev and save it to Redis. Returns a success message."""
    from ..core.data_loader import fetch_brapi_data
    import json

    data = fetch_brapi_data(ticker, period)

    # Save to Redis
    r = get_redis_connection()
    cache_key = f"rawdata:{ticker}:{period}"
    r.set(cache_key, json.dumps(data, ensure_ascii=False), ex=86400)

    return f"Data for {ticker} ({period}) saved to the cache successfully. Use the key: {cache_key}"


@tool("Compute dividend metrics by reading from the cache")
def calc_dividend_metrics_tool(ticker: str, period: str) -> str:
    """Read data from the cache and compute the dividend yield and other dividend metrics."""
    from ..core.metrics_calculator import calc_metrics_from_raw
    import json

    # Read from Redis
    r = get_redis_connection()
    cache_key = f"rawdata:{ticker}:{period}"
    cached_data = r.get(cache_key)

    if not cached_data:
        return json.dumps({"error": f"Data not found in cache for {ticker} {period}"})

    data = json.loads(cached_data)
    metrics = calc_metrics_from_raw(data)

    # Save metrics to the cache too
    metrics_key = f"metrics:{ticker}:{period}"
    r.set(metrics_key, json.dumps(metrics, ensure_ascii=False), ex=86400)

    return json.dumps(metrics, ensure_ascii=False)


@tool("Read dividend metrics from the cache")
def get_metrics_from_cache(ticker: str, period: str) -> str:
    """Retrieve already-computed dividend metrics from the cache."""
    import json

    r = get_redis_connection()
    metrics_key = f"metrics:{ticker}:{period}"
    cached_metrics = r.get(metrics_key)

    if not cached_metrics:
        return json.dumps({"error": f"Metrics not found in cache for {ticker} {period}"})

    return cached_metrics


@tool("Compare and rank tickers by dividend yield")
def rank_tickers_by_dividend_yield(tickers_list: str, period: str) -> str:
    """
    Compare multiple tickers and return a ranking ordered by dividend yield.

    Args:
        tickers_list: String with comma-separated tickers (e.g. "PETR4,VALE3,ITUB4,BBDC4")
        period: Analysis period

    Returns:
        JSON string with a ranking ordered by dividend yield (highest to lowest)
    """
    import json

    tickers = [t.strip() for t in tickers_list.split(",")]
    r = get_redis_connection()

    ranking = []
    for ticker in tickers:
        metrics_key = f"metrics:{ticker}:{period}"
        cached_metrics = r.get(metrics_key)

        if cached_metrics:
            metrics = json.loads(cached_metrics)
            ranking.append({
                "ticker": ticker,
                "dividend_yield": metrics.get("dividend_yield", 0),
                "current_price": metrics.get("current_price", 0),
                "dividends_12m": metrics.get("dividends_12m", 0),
                "payment_count": int(metrics.get("payment_count", 0)),
                "recommendation": "BUY" if metrics.get("dividend_yield", 0) > 7.0 else "HOLD"
            })

    # Sort by dividend yield (highest first)
    ranking.sort(key=lambda x: x["dividend_yield"], reverse=True)

    return json.dumps(ranking, ensure_ascii=False, indent=2)


@tool("Generate a PDF with the dividend analysis")
def generate_dividend_pdf(content: str, output_filename: str = "dividend_analysis.pdf") -> str:
    """
    Generate a professional PDF with the dividend analysis.

    Args:
        content: Text content to include in the PDF
        output_filename: Name of the PDF file to generate

    Returns:
        Full path of the generated PDF file
    """
    import json
    import os
    from datetime import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

    # Create the output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, output_filename)

    # Create the document
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=12,
        spaceBefore=12
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )

    # Document elements
    story = []

    # Title
    story.append(Paragraph("Dividend Analysis", title_style))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                          styles['Normal']))
    story.append(Spacer(1, 0.5*cm))

    # Try to parse the content as JSON (ranking)
    try:
        ranking = json.loads(content)
        if isinstance(ranking, list) and ranking:
            # Build a table with the ranking
            story.append(Paragraph("Stock Ranking by Dividend Yield", heading_style))
            story.append(Spacer(1, 0.3*cm))

            # Table header
            table_data = [[
                "Rank", "Ticker", "Dividend Yield", "Current Price",
                "Dividends 12M", "Payments", "Recommendation"
            ]]

            # Table rows
            for idx, item in enumerate(ranking, 1):
                table_data.append([
                    str(idx),
                    item.get("ticker", ""),
                    f"{item.get('dividend_yield', 0):.2f}%",
                    f"R$ {item.get('current_price', 0):.2f}",
                    f"R$ {item.get('dividends_12m', 0):.2f}",
                    str(item.get('payment_count', 0)),
                    item.get('recommendation', '')
                ])

            # Create and style the table
            t = Table(table_data, colWidths=[1.5*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm, 2.5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))

            story.append(t)
            story.append(Spacer(1, 0.5*cm))

            # Highlight the best option
            best = ranking[0]
            story.append(Paragraph("🏆 Best Opportunity", heading_style))
            best_text = f"""
            The ticker <b>{best.get('ticker', '')}</b> has the best dividend yield
            of <b>{best.get('dividend_yield', 0):.2f}%</b> per year, with a current price of
            R$ {best.get('current_price', 0):.2f} and {best.get('payment_count', 0)}
            payments over the last 12 months, totaling R$ {best.get('dividends_12m', 0):.2f}
            in dividends.
            """
            story.append(Paragraph(best_text, normal_style))

    except json.JSONDecodeError:
        # If it's not JSON, treat it as free text
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), normal_style))
                story.append(Spacer(1, 0.3*cm))

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "<i>Report generated automatically by Finance Advisor - Dividend Analyst</i>",
        styles['Normal']
    ))

    # Build the PDF
    doc.build(story)

    return f"PDF generated successfully: {output_path}"
