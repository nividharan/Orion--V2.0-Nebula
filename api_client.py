"""
api_client.py — Phase 6: API Integration Layer
==============================================
Principle:
  - Strict domain allow-list to prevent SSRF and unauthorised exfiltration.
  - Token-bucket rate limiting to prevent spamming and rate-limit penalties.
  - 429 / 503 backoff parsing Retry-After headers with exponential backoff.
  - Session handoff: Browser cookies in .cache/storage_state.json shared into httpx.
  - Resolution Hierarchy: Official API -> Discovered endpoint -> DOM -> Vision.
"""

from __future__ import annotations

import os
import json
import time
import asyncio
import logging
import urllib.parse
from enum import Enum
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field

import httpx

from resolvers.youtube import Candidate, search, search_from_fixture

logger = logging.getLogger("Orion.ApiClient")

# Domain allow-list for external HTTP API calls
ALLOWED_API_DOMAINS: frozenset[str] = frozenset({
    "youtube.com",
    "www.youtube.com",
    "googleapis.com",
    "www.googleapis.com",
    "youtube.googleapis.com",
    "google.com",
    "www.google.com",
    "github.com",
    "api.github.com",
    "wikipedia.org",
    "en.wikipedia.org",
    "127.0.0.1",
    "localhost",
})


class DomainNotAllowedError(ValueError):
    """Raised when an HTTP request targets a domain not in ALLOWED_API_DOMAINS."""
    pass


class RateLimitExceededError(RuntimeError):
    """Raised when 429 persists after all backoff retries."""
    pass


class TokenBucketRateLimiter:
    """Simple thread-safe token bucket rate limiter."""

    def __init__(self, requests_per_second: float = 5.0, burst: int = 10):
        self.rate = requests_per_second
        self.capacity = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens < 1.0:
                needed = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(needed)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


def load_cookies_from_storage(storage_state_path: Optional[str] = None) -> httpx.Cookies:
    """
    Reads Playwright storage_state.json and converts stored cookies into httpx.Cookies.
    Enables session handoff from browser to API client.
    """
    cookies = httpx.Cookies()
    if not storage_state_path:
        storage_state_path = os.path.abspath(".cache/storage_state.json")

    if not os.path.exists(storage_state_path):
        return cookies

    try:
        with open(storage_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            stored_cookies = data.get("cookies", [])
            for c in stored_cookies:
                name = c.get("name")
                value = c.get("value")
                domain = c.get("domain", "")
                path = c.get("path", "/")
                if name and value:
                    cookies.set(name, value, domain=domain, path=path)
    except Exception as e:
        logger.warning("Failed to load cookies from storage state: %s", e)

    return cookies


class ApiClient:
    """
    Hardened async HTTP client featuring:
    - Domain allow-list validation on all outgoing URLs.
    - Token-bucket rate limiting.
    - Automatic 429 Retry-After header parsing and exponential backoff.
    - Playwright session handoff via storage_state.json cookies.
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 10.0,
        requests_per_second: float = 5.0,
        storage_state_path: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.limiter = TokenBucketRateLimiter(requests_per_second=requests_per_second)
        self.storage_state_path = storage_state_path
        self.cookies = load_cookies_from_storage(storage_state_path)
        self._transport = transport

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            cookies=self.cookies,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
            transport=self._transport,
        )

    def _validate_domain(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            if self.base_url:
                parsed_base = urllib.parse.urlparse(self.base_url)
                host = (parsed_base.hostname or "").lower()

        if not host:
            raise DomainNotAllowedError(f"URL has no host: '{url}'")

        if host not in ALLOWED_API_DOMAINS:
            # Check wildcard / subdomain match
            matched = any(host == d or host.endswith("." + d) for d in ALLOWED_API_DOMAINS)
            if not matched:
                raise DomainNotAllowedError(
                    f"Domain '{host}' is not in ALLOWED_API_DOMAINS: {sorted(ALLOWED_API_DOMAINS)}"
                )

    async def request(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        base_backoff: float = 0.5,
        **kwargs
    ) -> httpx.Response:
        self._validate_domain(url)
        await self.limiter.acquire()

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)

                if response.status_code == 429:
                    if attempt == max_retries:
                        raise RateLimitExceededError(
                            f"HTTP 429 rate limit exceeded after {max_retries} retries on {url}"
                        )
                    # Parse Retry-After header
                    retry_after_str = response.headers.get("Retry-After")
                    delay = base_backoff * (2 ** attempt)
                    if retry_after_str:
                        try:
                            delay = float(retry_after_str)
                        except ValueError:
                            pass
                    logger.warning(
                        "Received 429 on %s, backing off %.2fs (attempt %d/%d)",
                        url, delay, attempt + 1, max_retries
                    )
                    await asyncio.sleep(delay)
                    continue

                return response

            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                if attempt == max_retries:
                    raise
                delay = base_backoff * (2 ** attempt)
                logger.warning("Network glitch %s on %s, retry in %.2fs", exc, url, delay)
                await asyncio.sleep(delay)

        raise RuntimeError(f"Unexpected request loop termination for {url}")

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> ApiClient:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# Resolution Hierarchy
# ---------------------------------------------------------------------------

class ResolutionTier(str, Enum):
    OFFICIAL_API = "OFFICIAL_API"
    DISCOVERED_ENDPOINT = "DISCOVERED_ENDPOINT"
    DOM = "DOM"
    VISION = "VISION"


@dataclass
class ResolutionResult:
    tier: ResolutionTier
    query: str
    candidates: List[Candidate] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "query": self.query,
            "count": len(self.candidates),
            "top_candidate": dict(self.candidates[0]) if self.candidates else None,
            "success": self.success,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 2),
        }


class ResolutionHierarchyRouter:
    """
    Resolution Hierarchy (from plan):
      Official API -> Discovered endpoint -> DOM -> Vision.
      
    1. Tier 1: Official API (YouTube Data API v3 if YOUTUBE_API_KEY present).
    2. Tier 2: Discovered Endpoint (structured ytInitialData resolver without keys).
    3. Tier 3: DOM (Playwright DOM locator extraction).
    4. Tier 4: Vision (Cropped screenshot perception).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[ApiClient] = None,
        fixture_path: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.client = client
        self.fixture_path = fixture_path

    async def resolve_official_api(self, query: str) -> List[Candidate]:
        """Tier 1: Official YouTube Data API v3."""
        if not self.api_key:
            raise ValueError("No YOUTUBE_API_KEY configured for Official API tier")

        url = "https://youtube.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 10,
            "key": self.api_key,
        }

        async with ApiClient() if not self.client else self.client as c:
            resp = await c.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        candidates: List[Candidate] = []
        for i, item in enumerate(data.get("items", [])):
            id_info = item.get("id", {})
            snippet = item.get("snippet", {})
            vid = id_info.get("videoId")
            if not vid:
                continue
            candidates.append(Candidate(
                index=i,
                video_id=vid,
                title=snippet.get("title", ""),
                channel=snippet.get("channelTitle", ""),
                duration="0:00",
                duration_s=0,
                is_live=False,
                score=1.0,
                url=f"https://www.youtube.com/watch?v={vid}",
            ))
        return candidates

    def resolve_discovered_endpoint(self, query: str) -> List[Candidate]:
        """Tier 2: Discovered endpoint (embedded ytInitialData search)."""
        if self.fixture_path and os.path.exists(self.fixture_path):
            with open(self.fixture_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return search_from_fixture(data, query, max_results=10)
        return search(query, max_results=10)

    def resolve_dom(self, page, query: str) -> List[Candidate]:
        """Tier 3: DOM inspection using Playwright page."""
        if not page:
            raise ValueError("No active Playwright page provided for DOM tier")

        encoded = urllib.parse.quote_plus(query)
        page.goto(f"https://www.youtube.com/results?search_query={encoded}")

        # Extract items from DOM
        data = page.evaluate("""
            () => {
                const results = [];
                const items = document.querySelectorAll('ytd-video-renderer, #video-title');
                items.forEach((item, idx) => {
                    const titleEl = item.querySelector('#video-title') || item;
                    const href = titleEl.getAttribute('href') || '';
                    const title = (titleEl.textContent || '').trim();
                    if (href && href.includes('/watch?v=')) {
                        const vid = href.split('v=')[1].split('&')[0];
                        results.push({
                            index: idx,
                            video_id: vid,
                            title: title,
                            channel: '',
                            duration: '0:00',
                            duration_s: 0,
                            is_live: false,
                            score: 1.0,
                            url: 'https://www.youtube.com/watch?v=' + vid
                        });
                    }
                });
                return results;
            }
        """)

        return [Candidate(**item) for item in data[:10]]

    async def resolve(
        self,
        query: str,
        page=None,
        force_tier: Optional[ResolutionTier] = None
    ) -> ResolutionResult:
        """
        Executes Resolution Hierarchy in waterfall order.
        """
        start = time.perf_counter()

        # Tier 1: Official API
        if force_tier == ResolutionTier.OFFICIAL_API or (force_tier is None and self.api_key):
            try:
                candidates = await self.resolve_official_api(query)
                if candidates:
                    return ResolutionResult(
                        tier=ResolutionTier.OFFICIAL_API,
                        query=query,
                        candidates=candidates,
                        success=True,
                        latency_ms=(time.perf_counter() - start) * 1000,
                    )
            except Exception as e:
                logger.info("Tier 1 (Official API) failed or bypassed: %s", e)
                if force_tier == ResolutionTier.OFFICIAL_API:
                    return ResolutionResult(
                        tier=ResolutionTier.OFFICIAL_API,
                        query=query,
                        success=False,
                        error=str(e),
                        latency_ms=(time.perf_counter() - start) * 1000,
                    )

        # Tier 2: Discovered Endpoint
        if force_tier in (None, ResolutionTier.DISCOVERED_ENDPOINT):
            try:
                candidates = self.resolve_discovered_endpoint(query)
                if candidates:
                    return ResolutionResult(
                        tier=ResolutionTier.DISCOVERED_ENDPOINT,
                        query=query,
                        candidates=candidates,
                        success=True,
                        latency_ms=(time.perf_counter() - start) * 1000,
                    )
            except Exception as e:
                logger.info("Tier 2 (Discovered Endpoint) failed: %s", e)
                if force_tier == ResolutionTier.DISCOVERED_ENDPOINT:
                    return ResolutionResult(
                        tier=ResolutionTier.DISCOVERED_ENDPOINT,
                        query=query,
                        success=False,
                        error=str(e),
                        latency_ms=(time.perf_counter() - start) * 1000,
                    )

        # Tier 3: DOM
        if (force_tier in (None, ResolutionTier.DOM)) and page is not None:
            try:
                candidates = self.resolve_dom(page, query)
                if candidates:
                    return ResolutionResult(
                        tier=ResolutionTier.DOM,
                        query=query,
                        candidates=candidates,
                        success=True,
                        latency_ms=(time.perf_counter() - start) * 1000,
                    )
            except Exception as e:
                logger.info("Tier 3 (DOM) failed: %s", e)

        # Tier 4: Vision
        return ResolutionResult(
            tier=ResolutionTier.VISION,
            query=query,
            success=False,
            error="Fallback reached Vision tier; DOM and API yielded no candidates",
            latency_ms=(time.perf_counter() - start) * 1000,
        )
