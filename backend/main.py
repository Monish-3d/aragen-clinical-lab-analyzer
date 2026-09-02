import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent import analyze_labs
from models import AnalyzeRequest, AnalyzeResponse

# The Windows console is cp1252 and cannot encode Turkish test names like
# İnsülin. Without this, logging a failed result raises UnicodeEncodeError and
# turns a handled fallback into a 500 - the log line crashes the request it was
# meant to explain.
sys.stdout.reconfigure(errors="replace")

app = FastAPI(title="Clinical Lab Results Analyzer")

# The React dev server runs on a different port than FastAPI, so the browser
# blocks the API calls unless we allow that origin here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Used by the frontend to show whether the backend is running."""
    return {"status": "ok"}


@app.post("/analyze_labs", response_model=AnalyzeResponse)
async def analyze_labs_endpoint(request: AnalyzeRequest):
    """Classify, sort and explain a list of lab results.

    Pydantic has already rejected malformed input by this point, so anything
    caught here is an unexpected failure.
    """
    try:
        return await analyze_labs(request.labs)
    except Exception as error:
        # Logged for us, but the user gets a plain message rather than a
        # Python traceback.
        print(f"Analysis failed: {error}")
        raise HTTPException(
            status_code=500, detail="Could not analyse these results. Please try again."
        )
