# Clinical Lab Results Analyzer

Full-stack app for the GenAI + Full-Stack assignment. It takes laboratory test
results, classifies each one as Normal / Warning / Critical against its
reference range, and uses an LLM to explain why it was flagged and what the
suggested next step is.

## Stack

- Backend: Python + FastAPI
- Frontend: React (Vite)
- LLM: Google Gemini (free tier)

## Running it

Backend (from `backend/`):

```
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend (from `frontend/`):

```
npm install
npm run dev
```

The frontend expects the backend on http://localhost:8000.

Copy `.env.example` to `.env` and add your Gemini API key before running the
explanation step.
