# Simple Search Service

A small Python web service that exposes a '/search' API on top of the November 7 '/messages' endpoint.

- **Source data**: 'GET https://november7-730026606190.europe-west1.run.app/messages'
- **Tech stack**: Python 3.12, FastAPI, httpx, Uvicorn
- **Goal**: Accept a query string and return a paginated list of matching messages in under 100ms.


## How it works

1. On startup, the service calls the upstream '/messages' endpoint once and reads:
   '''json
   {
     "total": 3349,
     "items": [ { "id": "...", "user_name": "...", "message": "...", ... }, ... ]
   }

2. It builds an in-memory index of messages. For each message it concatenates:

-user_name

-message

3. /search:

-lowercases and tokenizes the query q

-returns all messages whose combined text contains all query tokens

-applies pagination using page and page_size

There are no upstream calls per search, so latency is dominated by in-memory lookups and JSON serialization.

# API

## GET /search
Search messages.

### Query parameters

-q (string, required) – search term, case-insensitive

-page (int, default: 1, min: 1)

-page_size (int, default: 10, min: 1, max: 100)

Example:

GET /search?q=Paris&page=1&page_size=5

Example response

{
  "query": "Paris",
  "total": 2,
  "page": 1,
  "page_size": 5,
  "items": [
    {
      "message": {
        "id": "b1e9bb83-18be-4b90-bbb8-83b7428e8e21",
        "user_id": "cd3a350e-dbd2-408f-afa0-16a072f56d23",
        "user_name": "Sophia Al-Farsi",
        "timestamp": "2025-05-05T07:47:20.159073+00:00",
        "message": "Please book a private jet to Paris for this Friday."
      }
    },
    {
      "message": {
        "id": "9f279410-c039-41c2-9e62-938d6b6f1ec7",
        "user_id": "23103ae5-38a8-4d82-af82-e9942aa4aefb",
        "user_name": "Armand Dupont",
        "timestamp": "2025-06-12T07:38:26.159476+00:00",
        "message": "I'd love a personal recommendation for an art collector in Paris."
      }
    }
  ]
}

GET /health
Simple health check and index size:

{
  "status": "ok",
  "indexed_messages": 100
}

GET /docs
Interactive Swagger UI for trying the endpoints.

# Running locally
## Requirements

Python 3.12+

pip


# Steps

# create and activate virtualenv (Windows example)
python -m venv myenv
myenv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# run the app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Then open:

Swagger: http://localhost:8000/docs

Health: http://localhost:8000/health

Example search: http://localhost:8000/search?q=Paris&page=1&page_size=5

# Deployment
The app is containerised with Docker and can run on any container platform.

Docker

docker build -t simple-search-service .
docker run -p 8080:8080 simple-search-service
The service will then be available at http://localhost:8080.

# Hosted instance
Deployed at:

https://simple-search-service-rhxo.onrender.com/

Useful paths:

Health: https://simple-search-service-rhxo.onrender.com/health

Docs: https://simple-search-service-rhxo.onrender.com/docs

Example search:
https://simple-search-service-rhxo.onrender.com/search?q=Paris&page=1&page_size=5

# Design notes:

Messages are fetched once from the upstream /messages endpoint at startup and cached in memory.

Search is a simple case-insensitive token match over user_name + message.

This avoids extra infrastructure like databases or Elasticsearch and is sufficient for a few thousand records.

# Latency and potential improvements:

Current design is already fast because all data lives in memory and there are no upstream calls in the request path.

To push latency toward ~30ms:

-Build an inverted index (token -> list of message IDs) at startup so queries only touch matching messages instead of scanning all.

-Keep all search data in RAM and return only needed fields to reduce JSON size.

-Deploy close to users and run multiple Uvicorn workers to keep p95 latency low under concurrent load.
