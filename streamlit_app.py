"""
🏦 Finance Advisor - Dividend Analyst
Comparative dividend analysis with a multi-agent AI system
"""
import streamlit as st
import os
from pathlib import Path

# Import the orchestrator
from financeadvisor.core.orchestrator import analyze_multi_tickers

# Page configuration
st.set_page_config(
    page_title="Dividend Analyst",
    page_icon="💰",
    layout="wide"
)

# Title
st.title("💰 Dividend Analyst")
st.markdown("### Comparative dividend analysis with a multi-agent AI system")
st.divider()

# Available stocks (main B3 tickers)
AVAILABLE_STOCKS = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3",
    "ABEV3", "B3SA3", "RENT3", "ELET3", "ENBR3",
    "WEGE3", "SUZB3", "RAIL3", "JBSS3", "EMBR3",
    "CPLE6", "TAEE11", "CMIG4", "CSAN3", "VIVT3"
]

# Sidebar - Settings
with st.sidebar:
    st.header("⚙️ Settings")

    # Stock selection
    st.subheader("📊 Stocks to Analyze")
    selected_tickers = st.multiselect(
        "Pick 2 to 6 stocks:",
        options=sorted(AVAILABLE_STOCKS),
        default=["PETR4", "VALE3", "ITUB4"],
        max_selections=6
    )

    # Analysis period
    st.subheader("📅 Period")
    period = st.selectbox(
        "Analysis period:",
        options=["1y", "6mo", "3mo", "2y"],
        index=0,
        format_func=lambda x: {
            "1y": "1 year",
            "6mo": "6 months",
            "3mo": "3 months",
            "2y": "2 years"
        }[x]
    )

    # Model selection
    st.subheader("🤖 AI Model")
    llm_provider = st.radio(
        "Pick the model:",
        options=["openai", "gemini"],
        index=0,
        format_func=lambda x: {
            "openai": "🟢 OpenAI (GPT-4o-mini)",
            "gemini": "🔵 Google Gemini Flash"
        }[x]
    )

    st.divider()

    # API info
    with st.expander("ℹ️ Information"):
        st.caption("""
        **Required APIs:**
        - OpenAI: set `OPENAI_API_KEY`
        - Gemini: set `GEMINI_API_KEY`

        **What the system does:**
        1. Fetches dividend data
        2. Computes dividend yield
        3. Compares and ranks the stocks
        4. Generates a professional PDF report
        """)

# Main area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎯 Selected Stocks")
    if len(selected_tickers) >= 2:
        # Show the selected stocks
        cols = st.columns(min(len(selected_tickers), 4))
        for idx, ticker in enumerate(selected_tickers):
            with cols[idx % 4]:
                st.info(f"**{ticker}**")
    elif len(selected_tickers) == 1:
        st.warning("⚠️ Select at least 2 stocks to compare")
    else:
        st.info("👈 Select the stocks in the sidebar")

with col2:
    st.subheader("🚀 Run")

    # Validation
    can_run = len(selected_tickers) >= 2

    if st.button(
        "▶️ Analyze Dividends",
        type="primary",
        disabled=not can_run,
        use_container_width=True
    ):
        # Run the analysis
        with st.spinner(f"🔄 Analyzing {len(selected_tickers)} stocks..."):
            try:
                # Progress placeholder
                progress_text = st.empty()
                progress_bar = st.progress(0)

                progress_text.text("📊 Fetching stock data...")
                progress_bar.progress(20)

                # Run analysis
                result = analyze_multi_tickers(
                    tickers=selected_tickers,
                    period=period,
                    user_question=f"Comparative analysis of {', '.join(selected_tickers)}",
                    user_id="streamlit_user",
                    llm_provider=llm_provider
                )

                progress_bar.progress(100)
                progress_text.empty()
                progress_bar.empty()

                # Success!
                st.success("✅ Analysis completed successfully!")

                # Extract the PDF path
                pdf_path = result.strip()

                # Show information
                st.subheader("📄 Generated Report")
                st.code(pdf_path, language=None)

                # Button to download the PDF
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()

                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"dividend_analysis_{'_'.join(selected_tickers)}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"❌ Analysis error: {str(e)}")
                with st.expander("🔍 Error details"):
                    st.code(str(e))

# Footer
st.divider()
st.caption("💡 **Tip:** a dividend yield above 7% automatically triggers a BUY recommendation.")
st.caption("🤖 Powered by CrewAI + OpenAI/Gemini + Brapi.dev")
