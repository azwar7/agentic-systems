"""
extractor.py

Core data extraction logic. Fetches a GitHub user's profile and repos
from the real GitHub REST API, caches the result locally as JSON,
and returns it in a typed, predictable shape.

Concepts used (Session 2):
    - requests (GET), status codes, timeout, exceptions
    - json.dump / json.load for local caching

Concepts used (Session 1, only where they fit naturally):
    - TypedDict          -> fixed shape for the extracted data
    - context manager    -> safe file writing for the cache
    - decorator          -> @timed_log for timing/logging the extraction
    - __repr__            -> clean debug printing of the extractor
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypedDict, TypeVar

import httpx
import requests

GITHUB_API_BASE = "https://api.github.com"
CACHE_DIR = Path(__file__).parent / "cache"
#__file__ contains the path of the current file
CACHE_DIR.mkdir(exist_ok=True)

R = TypeVar("R")


# ---------------------------------------------------------------------------
# TypedDict — the fixed shape of every extraction result
# ---------------------------------------------------------------------------
class RepoInfo(TypedDict):
    name: str
    stars: int
    language: str | None
    url: str


class UserData(TypedDict):
    username: str
    name: str | None
    bio: str | None
    public_repos: int
    followers: int
    top_repos: list[RepoInfo]
    source: str   # "api" or "cache"


# ---------------------------------------------------------------------------
# Custom exceptions — wrap requests' exceptions into something more specific
# ---------------------------------------------------------------------------
class ExtractionError(Exception):
    """Raised when data cannot be extracted, for any reason."""


# ---------------------------------------------------------------------------
# Decorator — logs how long extraction took (reused pattern from Week 1)
# ---------------------------------------------------------------------------
def timed_log(func: Callable[..., R]) -> Callable[..., R]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        start = time.time()
        print(f"[EXTRACT] starting '{func.__name__}'...")
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[EXTRACT] '{func.__name__}' finished in {elapsed:.3f}s")
        return result

    return wrapper


# ---------------------------------------------------------------------------
# DataExtractor — the main class
# ---------------------------------------------------------------------------
@dataclass
class DataExtractor:
    timeout: int = 10
    use_cache: bool = True
    top_n_repos: int = 5

    def __repr__(self) -> str:
        return (
            f"DataExtractor(timeout={self.timeout}, "
            f"use_cache={self.use_cache}, top_n_repos={self.top_n_repos})"
        )

    # ---- caching helpers -------------------------------------------------
    def _cache_path(self, username: str) -> Path:
        return CACHE_DIR / f"{username.lower()}.json"

    def _read_cache(self, username: str) -> UserData | None:
        path = self._cache_path(username)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:   # context manager
                #the encoding converts the bytes to python string
                data: UserData = json.load(f)
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, username: str, data: UserData) -> None:
        path = self._cache_path(username)
        with open(path, "w", encoding="utf-8") as f:        # context manager
            json.dump(data, f, indent=4)

    # ---- the actual API call ---------------------------------------------
    def _fetch_user(self, username: str) -> dict[str, Any]:
        url = f"{GITHUB_API_BASE}/users/{username}"
        try:
            response = requests.get(url, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise ExtractionError(f"request timed out while fetching user '{username}'")
        except requests.exceptions.ConnectionError:
            raise ExtractionError("could not connect to GitHub API")

        if response.status_code == 404:
            raise ExtractionError(f"GitHub user '{username}' not found")
        if response.status_code == 403:
            raise ExtractionError("GitHub API rate limit exceeded, try again later")
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ExtractionError(f"GitHub API returned an error: {e}")

        return response.json()

    def _fetch_repos(self, username: str) -> list[dict[str, Any]]:
        url = f"{GITHUB_API_BASE}/users/{username}/repos"
        try:
            response = requests.get(
                url, params={"sort": "stars", "per_page": 100}, timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise ExtractionError(f"request timed out while fetching repos for '{username}'")
        except requests.exceptions.ConnectionError:
            raise ExtractionError("could not connect to GitHub API")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ExtractionError(f"GitHub API returned an error: {e}")

        return response.json()

    # ---- parsing -----------------------------------------------------------
    def _build_user_data(
        self, username: str, raw_user: dict[str, Any], raw_repos: list[dict[str, Any]], source: str
    ) -> UserData:
        # sort repos by stargazers_count, take the top N -- list comprehension + slicing
        sorted_repos = sorted(raw_repos, key=lambda repo: repo.get("stargazers_count", 0), reverse=True)
        top_repos: list[RepoInfo] = [
            RepoInfo(
                name=repo["name"],
                stars=repo.get("stargazers_count", 0),
                language=repo.get("language"),
                url=repo["html_url"],
            )
            for repo in sorted_repos[: self.top_n_repos]
        ]

        return UserData(
            username=raw_user["login"],
            name=raw_user.get("name"),
            bio=raw_user.get("bio"),
            public_repos=raw_user.get("public_repos", 0),
            followers=raw_user.get("followers", 0),
            top_repos=top_repos,
            source=source,
        )

    # ---- public entrypoint (sync — used by the CLI) -----------------------
    @timed_log
    def extract(self, username: str, force_refresh: bool = False) -> UserData:
        """
        Fetches GitHub user + repo data, using the local cache unless
        force_refresh is True or caching is disabled.
        """
        if self.use_cache and not force_refresh: #first checking local machine
            cached = self._read_cache(username)
            if cached is not None:
                print(f"[EXTRACT] using cached data for '{username}'")
                return cached
        #if not found fetching from the API
        raw_user = self._fetch_user(username)
        raw_repos = self._fetch_repos(username)
        data = self._build_user_data(username, raw_user, raw_repos, source="api")

        #caching to use in the future
        if self.use_cache:
            self._write_cache(username, data)

        return data

    # ---- async versions (used by FastAPI) ---------------------------------
    async def _fetch_user_async(self, client: httpx.AsyncClient, username: str) -> dict[str, Any]:
        url = f"{GITHUB_API_BASE}/users/{username}"
        try:
            response = await client.get(url, timeout=self.timeout)
        except httpx.TimeoutException:
            raise ExtractionError(f"request timed out while fetching user '{username}'")
        except httpx.ConnectError:
            raise ExtractionError("could not connect to GitHub API")

        if response.status_code == 404:
            raise ExtractionError(f"GitHub user '{username}' not found")
        if response.status_code == 403:
            raise ExtractionError("GitHub API rate limit exceeded, try again later")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ExtractionError(f"GitHub API returned an error: {e}")

        return response.json()

    async def _fetch_repos_async(
        self, client: httpx.AsyncClient, username: str
    ) -> list[dict[str, Any]]:
        url = f"{GITHUB_API_BASE}/users/{username}/repos"
        try:
            response = await client.get(
                url, params={"sort": "stars", "per_page": 100}, timeout=self.timeout
            )
        except httpx.TimeoutException:
            raise ExtractionError(f"request timed out while fetching repos for '{username}'")
        except httpx.ConnectError:
            raise ExtractionError("could not connect to GitHub API")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ExtractionError(f"GitHub API returned an error: {e}")

        return response.json()

    async def extract_async(self, username: str, force_refresh: bool = False) -> UserData:
        """
        Async version of extract() -- used by the FastAPI endpoint so the
        server isn't blocked while waiting on GitHub's API.
        """
        if self.use_cache and not force_refresh:
            cached = self._read_cache(username)
            if cached is not None:
                return cached

        async with httpx.AsyncClient() as client:
            raw_user = await self._fetch_user_async(client, username)
            raw_repos = await self._fetch_repos_async(client, username)

        data = self._build_user_data(username, raw_user, raw_repos, source="api")

        if self.use_cache:
            self._write_cache(username, data)

        return data
