from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
