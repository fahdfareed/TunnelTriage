# TunnelTriage

Decides which Massachusetts tunnel repairs to fund first for a fixed budget,
using public FHWA National Tunnel Inventory condition data. Not an engineering assessment.

## Run

Backend (http://localhost:8000):

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_data.py            # fetch + cache + process (data is committed)
uvicorn app.main:app --reload
pytest -q                               # 28 tests
```

Frontend (http://localhost:5173, proxies /api to the backend):

```
cd frontend
npm install
npm run dev
```

`POST /api/plan {"budget": 25000000}` returns the funded repair plan. LLM is optional
(`LLM_PROVIDER=none` by default; set `anthropic` or `bedrock` to enable the AI memo and
free-text finding parsing — both have deterministic fallbacks).
