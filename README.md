# Omise Real-Time Fraud Detection

AI-powered fraud detection demo using LangGraph, Isolation Forest, FastAPI, and Streamlit.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI |
| Agent | LangGraph |
| ML Model | scikit-learn Isolation Forest |
| LLM (demo) | Ollama + Qwen 2.5 7B |
| LLM (prod) | OpenAI GPT-4o-mini |
| Database | SQLite |

## Agent Flow

```
New Transaction → Feature Extraction → check_transaction_history (tool)
               → check_fraud_rules (tool) → Isolation Forest Score
               → LLM Reasoning → send_alert (tool) → Dashboard
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set LLM_PROVIDER=ollama or openai
```

### 3. (If using Ollama) Pull the model

```bash
ollama pull qwen2.5:7b
```

### 4. Start the FastAPI backend

```bash
cd omise-fraud-detection
uvicorn backend.main:app --reload --port 8000
```

The backend will:
- Auto-create the SQLite database
- Seed 200 synthetic transactions
- Build the Isolation Forest model (first run only, ~0.5s)

### 5. Start the Streamlit dashboard (new terminal)

```bash
cd omise-fraud-detection
streamlit run frontend/dashboard.py
```

Open http://localhost:8501

### 6. Test with the API directly

```bash
curl -X POST http://localhost:8000/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_test_001",
    "card_id": "card_0001",
    "merchant_id": "mch_retail_002",
    "amount": 15000,
    "currency": "THB",
    "location": "London",
    "timestamp": "2024-03-14T02:30:00"
  }'
```

## Project Structure

```
omise-fraud-detection/
├── backend/
│   ├── main.py          # FastAPI app
│   └── schemas.py       # Pydantic models
├── agent/
│   ├── graph.py         # LangGraph StateGraph
│   ├── nodes.py         # Node functions + LLM setup
│   └── state.py         # AgentState TypedDict
├── tools/
│   ├── history_tool.py  # check_transaction_history()
│   ├── rules_tool.py    # check_fraud_rules()
│   └── alert_tool.py    # send_alert()
├── ml/
│   ├── train.py         # Isolation Forest training
│   └── scorer.py        # Inference utility
├── db/
│   ├── database.py      # SQLite + SQLAlchemy
│   └── seed.py          # Synthetic data seeder
├── frontend/
│   └── dashboard.py     # Streamlit UI
├── requirements.txt
└── .env.example
```

## Switching LLM Provider

Edit `.env`:

```
# For local demo (requires Ollama running)
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b

# For production
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

No code changes needed — the provider is loaded at startup.
