"""
Finance Advisor - Dividend Analyst
Multi-ticker dividend analysis with PDF generation
"""
from .core.orchestrator import analyze_multi_tickers


def main():
    """Run comparative dividend analyses for different portfolios."""

    # Configuration
    period = "1y"
    llm_provider = "openai"  # or "gemini"

    # Analysis combinations
    portfolios = [
        {
            "name": "Blue Chips",
            "tickers": ["PETR4", "VALE3", "ITUB4", "BBDC4"]
        },
        {
            "name": "Utilities + Energy",
            "tickers": ["ELET3", "ENBR3", "TAEE11", "CPLE6"]
        },
        {
            "name": "Top Dividends",
            "tickers": ["PETR4", "VALE3", "BBAS3"]
        }
    ]

    # Run analyses
    for portfolio in portfolios:
        print(f"\n{'='*80}")
        print(f"📊 ANALYSIS: {portfolio['name']}")
        print(f"{'='*80}\n")

        try:
            pdf_path = analyze_multi_tickers(
                tickers=portfolio["tickers"],
                period=period,
                user_question=f"Dividend analysis - {portfolio['name']}",
                user_id="batch_analysis",
                llm_provider=llm_provider
            )
            print(f"\n✅ Analysis complete!")
            print(f"📄 PDF: {pdf_path}\n")

        except Exception as e:
            print(f"\n❌ Error analyzing {portfolio['name']}: {e}\n")


if __name__ == "__main__":
    main()
