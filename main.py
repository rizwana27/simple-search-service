from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Base URL of the assignment API
SOURCE_API_BASE_URL = os.getenv(
    "SOURCE_API_BASE_URL",
    "https://november7-730026606190.europe-west1.run.app",
)

# Full URL for /messages
MESSAGES_URL = f"{SOURCE_API_BASE_URL}/messages"


class SearchItem(BaseModel):
    message: Dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    items: List[SearchItem]


app = FastAPI(
    title="Simple Search Service",
    description="Search on top of the November 7 /messages endpoint.",
    version="1.0.0",
)

# This will store:
# [
#   { "raw": <original message dict>, "search_text": "<lowercase searchable text>" },
#   ...
# ]
MESSAGE_INDEX: List[Dict[str, Any]] = []


def extract_searchable_text(msg: Dict[str, Any]) -> str:
    """
    Build a string that includes the fields we want to search on.

    For this API, each message looks like:
      {
        "id": "...",
        "user_id": "...",
        "user_name": "Sophia Al-Farsi",
        "timestamp": "2025-05-05T07:47:20.159073+00:00",
        "message": "Please book a private jet to Paris for this Friday."
      }

    We'll search across:
      - user_name (so you can search by person)
      - message (so you can search by text content)
    """
    parts: List[str] = []

    # Include the user name
    parts.append(str(msg.get("user_name", "")))

    # Include the actual message text
    parts.append(str(msg.get("message", "")))

    # Join and lowercase for case-insensitive search
    return " ".join(parts).lower()


async def load_messages_into_index() -> None:
    global MESSAGE_INDEX

    # follow_redirects=True tells httpx to automatically handle 307 -> new URL
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(MESSAGES_URL)
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, list):
        raw_messages = data
    elif isinstance(data, dict) and "items" in data:
        raw_messages = data["items"]
    else:
        raise RuntimeError(f"Unexpected /messages response shape: {type(data)}, data={data}")

    MESSAGE_INDEX = [
        {
            "raw": msg,
            "search_text": extract_searchable_text(msg),
        }
        for msg in raw_messages
    ]
    print(f"[startup] Indexed {len(MESSAGE_INDEX)} messages")


def search_messages(query: str) -> List[Dict[str, Any]]:
    """
    Very simple search:
    - convert query to lower-case
    - split into tokens by space
    - keep messages where ALL tokens appear in search_text
    """
    q = query.strip().lower()
    if not q:
        return []

    tokens = [t for t in q.split() if t]

    results: List[Dict[str, Any]] = []
    for entry in MESSAGE_INDEX:
        text = entry["search_text"]
        if all(token in text for token in tokens):
            results.append(entry["raw"])

    return results


@app.on_event("startup")
async def startup_event() -> None:
    await load_messages_into_index()


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "indexed_messages": len(MESSAGE_INDEX),
    }


@app.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> SearchResponse:
    if not MESSAGE_INDEX:
        raise HTTPException(status_code=503, detail="Index not ready. Try again shortly.")

    all_results = search_messages(q)
    total = len(all_results)

    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_results[start:end]

    return SearchResponse(
        query=q,
        total=total,
        page=page,
        page_size=page_size,
        items=[SearchItem(message=item) for item in page_items],
    )
@app.get("/")
def root():
    return {
        "message": "Simple Search Service is running. Try /health or /docs."
    }
