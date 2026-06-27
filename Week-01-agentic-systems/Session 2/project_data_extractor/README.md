# Data Extractor — GitHub User & Repo Extractor

A Python project that fetches a GitHub user's public profile and top
repositories from the real GitHub REST API, caches the result locally as
JSON, and exposes itself two ways: a command-line tool and a FastAPI
HTTP endpoint.

Built as part of Week 1, Session 2 (API clients, CLI tools, JSON
handling) of an Agentic AI Systems course — combined with a few Session 1
concepts (typing, decorators, context managers) where they genuinely fit.

## What it does

```
User -> CLI or FastAPI -> GitHub API -> local JSON cache -> User
```

1. Given a GitHub username, fetches their profile and repositories
2. Sorts repositories by star count, keeps the top N
3. Caches the result as a local JSON file so repeated lookups don't hit
   the API again
4. Returns the data either as CLI output or as a JSON HTTP response

## Concepts used

### Session 2 (core)
- `requests` — GET requests, query params, timeouts
- HTTP status codes (200, 404, 403) mapped to meaningful errors
- `requests` exceptions (`Timeout`, `ConnectionError`, `HTTPError`)
- `json.dump` / `json.load` for the local file cache
- `json.dumps(..., indent=4)` for pretty CLI output
- `argparse` — positional argument, optional flags, type conversion, defaults
- `main()` + `if __name__ == "__main__"` + `SystemExit` pattern
- FastAPI (`@app.get`, path/query parameters, `HTTPException`)
- `httpx.AsyncClient` with `async`/`await`, used specifically inside the
  FastAPI route so the server isn't blocked while waiting on GitHub

### Session 1 (used only where they fit naturally)
- `TypedDict` — fixed shape for the extracted data (`UserData`, `RepoInfo`)
- Context managers (`with open(...) as f`) for safe cache file reads/writes
- A decorator (`@timed_log`) for timing the sync extraction path
- `__repr__` on `DataExtractor` for clean debug printing
- List comprehension for building the top-N repo list

## Project structure

```
project_data_extractor/
├── extractor.py    # core DataExtractor class: fetch, cache, parse (sync + async)
├── cli.py          # argparse-based command-line interface
├── api.py          # FastAPI app exposing the same extractor over HTTP
├── cache/          # local JSON cache, created automatically at runtime
└── README.md
```

## Setup

```bash
pip install requests httpx fastapi uvicorn
```

## Running the CLI

```bash
python cli.py torvalds
python cli.py torvalds --top 3
python cli.py torvalds --no-cache
python cli.py torvalds --refresh
```

| Flag | Effect |
|---|---|
| `--top N` | show top N repos by stars (default 5) |
| `--no-cache` | skip reading/writing the cache entirely |
| `--refresh` | ignore any existing cache and fetch fresh data |

## Running the API

```bash
uvicorn api:app --reload
```

Then visit:
- `http://127.0.0.1:8000/docs` — interactive API documentation
- `http://127.0.0.1:8000/extract/torvalds?top=3`

## Error handling

Real network/API failures are caught and turned into clear messages
instead of raw stack traces:

| Situation | CLI behavior | API behavior |
|---|---|---|
| User not found | prints error, exits with code 1 | `404 Not Found` |
| Rate limit exceeded | prints error, exits with code 1 | `429 Too Many Requests` |
| Timeout / connection error | prints error, exits with code 1 | `502 Bad Gateway` |

## Notes on caching

The cache lives in `cache/<username>.json`. Once a user has been fetched
once, subsequent calls (CLI or API) return instantly from disk instead of
hitting GitHub's API again — until `--refresh` / `refresh=true` is used.

GitHub's public API allows 60 unauthenticated requests per hour per IP;
the cache exists specifically to avoid burning through that limit during
repeated testing.

## What this is not

This is a learning project focused on practicing real HTTP/JSON/CLI/API
concepts together. It is intentionally scoped to one external API
(GitHub) and does not include authentication tokens, pagination beyond
100 repos, or production-grade rate-limit backoff strategies.
