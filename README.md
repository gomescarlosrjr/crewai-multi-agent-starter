# CrewAI Multi-Agent Starter

An educational **multi-agent system** built with **CrewAI** that performs comparative **dividend analysis of Brazilian stocks (B3)**: it fetches real data, computes metrics, generates insights with an LLM (Gemini or OpenAI), ranks the stocks, and produces a **PDF report**. Web UI in **Streamlit**, caching in **Redis**. Made to **study, fork, and extend**.

> Study project. Not investment advice.

## What you learn here

- **Multi-agent architecture** with CrewAI: `Agent`, `Task`, `Crew`, and tools.
- **Layered design**: `core/` (data and metrics), `crew/` (agents and tools), `utils/` (cache, LLM client).
- **Integration with a real API** (brapi.dev / B3) and **financial metric** computation.
- **Pluggable LLM** (Gemini or OpenAI) behind a single configuration.
- **Caching with Redis** to avoid redundant calls (and rate limiting).
- **PDF generation** with ReportLab and a **UI** with Streamlit.

## Prerequisites

- Python 3.11+ (3.12 recommended)
- **Docker** (for Redis)
- An LLM key: **Gemini** (free at https://aistudio.google.com/app/apikey) **or** OpenAI
- (Optional) a **brapi.dev** token to avoid rate limits

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r financeadvisor/requirements.txt

cp .env.example .env
# edit .env: set GEMINI_API_KEY (or OPENAI_API_KEY) and, optionally, BRAPI_TOKEN
```

## Run

**1. Start Redis** (cache):
```bash
bash run_redis.sh          # uses docker-compose (redis:7 on port 6379)
```

**2a. Web UI (Streamlit):**
```bash
bash run_app.sh            # or: streamlit run streamlit_app.py
```

**2b. Programmatic use (CLI):**
```bash
python -m financeadvisor.main
```

## Structure

```
.
├── streamlit_app.py            # web UI
├── docker-compose.yaml         # Redis
├── run_app.sh / run_redis.sh   # shortcuts
├── .env.example
└── financeadvisor/
    ├── main.py                 # programmatic entry point (example portfolios)
    ├── core/
    │   ├── data_loader.py      # fetches B3 data (brapi.dev)
    │   ├── metrics_calculator.py
    │   └── orchestrator.py     # orchestrates the multi-ticker analysis
    ├── crew/
    │   ├── crew.py             # defines Agents/Tasks/Crew (CrewAI) + LLM choice
    │   └── tools.py            # tools: fetch, metrics, ranking, PDF
    └── utils/
        ├── cache.py            # Redis cache
        └── llm_client.py       # LLM client (Gemini/OpenAI)
```

## How the agents work

`orchestrator` coordinates the flow; the `Crew` (CrewAI) combines specialized agents —
data fetching → metric computation → insight generation → recommendation/ranking —
using the tools in `crew/tools.py`. The LLM is selected in `crew/crew.py` (`get_llm("gemini"|"openai")`).

## Exercises to extend (mentor suggestions)

1. **New agent**: a "risk analyst" that penalizes high volatility in the ranking.
2. **New metric** in `metrics_calculator.py` (e.g. payout ratio) and use it in the insight.
3. **Switch the LLM provider** and compare insight quality/cost.
4. **Persist results** in Qdrant (already scaffolded in `.env.example`) and enable semantic search over past analyses.
5. **Tests**: cover `metrics_calculator` and `cache` with pytest (no real API calls — use mocks).

## Security

Never commit the `.env` (it's already in `.gitignore`). API keys and tokens live only in your environment.
