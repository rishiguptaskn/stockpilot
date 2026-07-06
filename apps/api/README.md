# StockPilot API

FastAPI service hosting the rule engine, technical indicators, pattern detectors, and yfinance ingestion.

## Setup

```powershell
cd apps\api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Run

```powershell
uvicorn stockpilot_api.main:app --reload
```

## Test

```powershell
pytest -v
```

## Layout

```
src/stockpilot_api/
├── main.py                 FastAPI app entry
├── models.py               Pydantic types matching packages/types
├── engine/                 10 rule modules (M1..M10)
│   └── module_1_market.py  Market Environment — 15 rules
├── indicators/             SMA, EMA, ATR, RSI
├── patterns/               8 pattern detectors (VCP, Cup & Handle, …)
├── ingestion/              yfinance data sync → Supabase
└── scoring/                Aggregator + verdict logic
```

Every rule cites its book source per `docs/RULEBOOK.md`.
