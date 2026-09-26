# CrewAI Multi-Agent Starter

Exemplo didático de um **sistema multi-agente** com **CrewAI**, que faz análise comparativa de **dividendos de ações brasileiras (B3)**: coleta dados reais, calcula métricas, gera insights com LLM (Gemini ou OpenAI), ranqueia as ações e produz um **relatório PDF**. Interface web em **Streamlit** e cache em **Redis**. Feito para **estudar, forkar e estender**.

> Projeto de estudo. Não é recomendação de investimento.

## O que você aprende aqui

- **Arquitetura multi-agente** com CrewAI: `Agent`, `Task`, `Crew` e ferramentas (tools).
- **Separação de camadas**: `core/` (dados e métricas), `crew/` (agentes e tools), `utils/` (cache, cliente LLM).
- **Integração com API real** (brapi.dev / B3) e **cálculo de métricas** financeiras.
- **LLM plugável** (Gemini ou OpenAI) atrás de uma única configuração.
- **Cache com Redis** para evitar chamadas redundantes (e rate limiting).
- **Geração de PDF** com ReportLab e **UI** com Streamlit.

## Pré-requisitos

- Python 3.11+ (recomendado 3.12)
- **Docker** (para o Redis)
- Uma chave de LLM: **Gemini** (grátis em https://aistudio.google.com/app/apikey) **ou** OpenAI
- (Opcional) Token da **brapi.dev** para evitar limites

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r financeadvisor/requirements.txt

cp .env.example .env
# edite .env: coloque GEMINI_API_KEY (ou OPENAI_API_KEY) e, opcionalmente, BRAPI_TOKEN
```

## Rodar

**1. Suba o Redis** (cache):
```bash
bash run_redis.sh          # usa docker-compose (redis:7 na porta 6379)
```

**2a. Interface web (Streamlit):**
```bash
bash run_app.sh            # ou: streamlit run streamlit_app.py
```

**2b. Uso programático (CLI):**
```bash
python -m financeadvisor.main
```

## Estrutura

```
.
├── streamlit_app.py            # interface web
├── docker-compose.yaml         # Redis
├── run_app.sh / run_redis.sh   # atalhos
├── .env.example
└── financeadvisor/
    ├── main.py                 # entrada programática (carteiras de exemplo)
    ├── core/
    │   ├── data_loader.py      # coleta dados da B3 (brapi.dev)
    │   ├── metrics_calculator.py
    │   └── orchestrator.py     # orquestra a análise multi-ticker
    ├── crew/
    │   ├── crew.py             # define Agents/Tasks/Crew (CrewAI) + escolha do LLM
    │   └── tools.py            # ferramentas: fetch, métricas, ranking, PDF
    └── utils/
        ├── cache.py            # cache Redis
        └── llm_client.py       # cliente LLM (Gemini/OpenAI)
```

## Como os agentes trabalham

`orchestrator` coordena o fluxo; a `Crew` (CrewAI) combina agentes especializados —
coleta de dados → cálculo de métricas → geração de insights → recomendação/ranking —
usando as tools de `crew/tools.py`. O LLM é escolhido em `crew/crew.py` (`get_llm("gemini"|"openai")`).

## Exercícios para estender (sugestões do mentor)

1. **Novo agente**: um "analista de risco" que penaliza volatilidade alta no ranking.
2. **Nova métrica** em `metrics_calculator.py` (ex.: payout ratio) e use-a no insight.
3. **Trocar o provider** de LLM e comparar qualidade/custo dos insights.
4. **Persistir resultados** no Qdrant (já previsto no `.env.example`) e permitir busca semântica de análises passadas.
5. **Testes**: cobrir `metrics_calculator` e `cache` com pytest (sem chamar a API real — use mocks).

## Segurança

Nunca faça commit do `.env` (já está no `.gitignore`). Chaves de API e tokens ficam só no seu ambiente.
