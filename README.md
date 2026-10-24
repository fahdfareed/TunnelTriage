# TunnelTriage

Decides which Massachusetts tunnel repairs to fund first for a fixed budget,
using public FHWA National Tunnel Inventory condition data. Not an engineering assessment.

## Run (backend)

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_data.py            # fetch + cache + process (commit the output)
uvicorn app.main:app --reload          # serves on http://localhost:8000
pytest -q                               # tests must pass
```

`POST /api/plan {"budget": 74000000}` returns the funded repair plan. LLM is optional (`LLM_PROVIDER=none`).
