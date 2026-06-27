"""
api.py

FastAPI layer exposing the same DataExtractor as an HTTP API.

Flow (matches Session 2 notes):
    User -> FastAPI -> External API (GitHub) -> FastAPI -> User

Run with:
    uvicorn api:app --reload

Then visit:
    http://127.0.0.1:8000/docs        (interactive API docs)
    http://127.0.0.1:8000/extract/torvalds
"""

from fastapi import FastAPI, HTTPException, Query

from extractor import DataExtractor, ExtractionError, UserData

app = FastAPI(
    title="GitHub Data Extractor API",
    description="Fetches and caches a GitHub user's profile and top repositories.",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Data Extractor API is running. See /docs for usage."}


@app.get("/extract/{username}", response_model=None)
async def extract_user(
    username: str,
    top: int = Query(default=5, ge=1, le=20, description="number of top repos to return"),
    refresh: bool = Query(default=False, description="force a fresh fetch, bypassing cache"),
) -> UserData:
    extractor = DataExtractor(top_n_repos=top)

    try:
        data = await extractor.extract_async(username, force_refresh=refresh)
    except ExtractionError as e:
        # map our domain error onto an honest HTTP status code
        message = str(e)
        if "not found" in message:
            raise HTTPException(status_code=404, detail=message)
        if "rate limit" in message:
            raise HTTPException(status_code=429, detail=message)
        raise HTTPException(status_code=502, detail=message)

    return data
