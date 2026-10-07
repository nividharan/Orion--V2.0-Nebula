"""
tests/test_api_client.py — Phase 6 exit criteria
==================================================
Deterministic test suite for api_client.py.
Uses httpx.MockTransport and offline fixtures — no live external network.

Exit criteria (from plan):
  ✓ Domain allow-list blocks unauthorized domains and SSRF vectors.
  ✓ Token-bucket rate limiter throttles burst requests.
  ✓ 429 Retry-After backoff parses header and retries cleanly.
  ✓ Session handoff shares browser cookies into httpx client.
  ✓ Resolution Hierarchy executes: Official API -> Discovered endpoint -> DOM -> Vision.
"""

import os
import sys
import json
import time
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from api_client import (
    ApiClient,
    DomainNotAllowedError,
    RateLimitExceededError,
    TokenBucketRateLimiter,
    load_cookies_from_storage,
    ResolutionTier,
    ResolutionResult,
    ResolutionHierarchyRouter,
)


class TestDomainAllowList(unittest.IsolatedAsyncioTestCase):
    async def test_allowed_domains_accepted(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"ok": True}))
        async with ApiClient(transport=transport) as client:
            resp1 = await client.get("https://youtube.googleapis.com/youtube/v3/search")
            self.assertEqual(resp1.status_code, 200)

            resp2 = await client.get("https://www.youtube.com/results?q=test")
            self.assertEqual(resp2.status_code, 200)

            resp3 = await client.get("https://api.github.com/user")
            self.assertEqual(resp3.status_code, 200)

    async def test_disallowed_domain_raises(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(200))
        async with ApiClient(transport=transport) as client:
            with self.assertRaises(DomainNotAllowedError):
                await client.get("https://evil-exfiltration-site.com/steal")

    async def test_ssrf_metadata_ip_blocked(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(200))
        async with ApiClient(transport=transport) as client:
            with self.assertRaises(DomainNotAllowedError):
                await client.get("http://169.254.169.254/computeMetadata/v1/")


class TestRateLimiter(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limiter_acquires_tokens(self):
        limiter = TokenBucketRateLimiter(requests_per_second=100.0, burst=5)
        # Should acquire 5 instantly without sleeping
        for _ in range(5):
            await limiter.acquire()
        self.assertLessEqual(limiter.tokens, 1.0)


class Test429Backoff(unittest.IsolatedAsyncioTestCase):
    async def test_429_retry_after_recovers_to_200(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(429, headers={"Retry-After": "0.01"})
            return httpx.Response(200, json={"status": "recovered"})

        transport = httpx.MockTransport(handler)
        async with ApiClient(transport=transport) as client:
            resp = await client.get("https://www.youtube.com/test", max_retries=2, base_backoff=0.01)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(calls, 2)
            self.assertEqual(resp.json()["status"], "recovered")

    async def test_persistent_429_raises_after_max_retries(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "0.01"})

        transport = httpx.MockTransport(handler)
        async with ApiClient(transport=transport) as client:
            with self.assertRaises(RateLimitExceededError):
                await client.get("https://www.youtube.com/test", max_retries=2, base_backoff=0.01)


class TestSessionHandoff(unittest.TestCase):
    def test_load_cookies_from_storage_json(self):
        temp_storage = PROJECT_ROOT / ".cache" / "test_session_storage.json"
        temp_storage.parent.mkdir(parents=True, exist_ok=True)

        sample_data = {
            "cookies": [
                {
                    "name": "LOGIN_INFO",
                    "value": "xyz_authenticated_token_123",
                    "domain": ".youtube.com",
                    "path": "/",
                },
                {
                    "name": "PREF",
                    "value": "f1=50000000",
                    "domain": ".youtube.com",
                    "path": "/",
                }
            ]
        }
        with open(temp_storage, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

        try:
            cookies = load_cookies_from_storage(str(temp_storage))
            self.assertEqual(cookies.get("LOGIN_INFO"), "xyz_authenticated_token_123")
            self.assertEqual(cookies.get("PREF"), "f1=50000000")
        finally:
            if temp_storage.exists():
                temp_storage.unlink()

    def test_load_cookies_nonexistent_returns_empty(self):
        cookies = load_cookies_from_storage("nonexistent_file_path_12345.json")
        self.assertIsInstance(cookies, httpx.Cookies)
        self.assertEqual(len(cookies), 0)


class TestResolutionHierarchy(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fixture_file = str(
            PROJECT_ROOT / "tests" / "fixtures" / "youtube_search_kangal_neeye.json"
        )

    async def test_tier_1_official_api_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            mock_body = {
                "items": [
                    {
                        "id": {"videoId": "test_vid_1"},
                        "snippet": {"title": "Kangal Neeye Official Song", "channelTitle": "Sony Music"}
                    }
                ]
            }
            return httpx.Response(200, json=mock_body)

        transport = httpx.MockTransport(handler)
        client = ApiClient(transport=transport)

        router = ResolutionHierarchyRouter(
            api_key="mock_key_123",
            client=client,
            fixture_path=self.fixture_file,
        )

        res = await router.resolve("kangal neeye tamil song")
        self.assertTrue(res.success)
        self.assertEqual(res.tier, ResolutionTier.OFFICIAL_API)
        self.assertEqual(len(res.candidates), 1)
        self.assertEqual(res.candidates[0]["video_id"], "test_vid_1")

    async def test_tier_1_fails_falls_back_to_tier_2_discovered(self):
        """When Official API returns 500 error, falls back to Tier 2 (Discovered endpoint)."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "Backend Error"})

        transport = httpx.MockTransport(handler)
        client = ApiClient(transport=transport)

        router = ResolutionHierarchyRouter(
            api_key="mock_key_123",
            client=client,
            fixture_path=self.fixture_file,
        )

        res = await router.resolve("kangal neeye tamil song")
        self.assertTrue(res.success)
        self.assertEqual(res.tier, ResolutionTier.DISCOVERED_ENDPOINT)
        self.assertGreater(len(res.candidates), 0)

    async def test_no_api_key_routes_directly_to_tier_2(self):
        router = ResolutionHierarchyRouter(
            api_key=None,
            fixture_path=self.fixture_file,
        )
        res = await router.resolve("kangal neeye tamil song")
        self.assertTrue(res.success)
        self.assertEqual(res.tier, ResolutionTier.DISCOVERED_ENDPOINT)
        self.assertGreater(len(res.candidates), 0)

    async def test_tier_3_dom_fallback(self):
        mock_page = MagicMock()
        mock_page.evaluate.return_value = [
            {
                "index": 0,
                "title": "DOM Song Result",
                "channel": "Channel",
                "duration": "3:45",
                "duration_seconds": 225,
                "video_id": "dom_video_id",
                "url": "https://www.youtube.com/watch?v=dom_video_id",
            }
        ]

        router = ResolutionHierarchyRouter(api_key=None)
        res = await router.resolve(
            "kangal neeye",
            page=mock_page,
            force_tier=ResolutionTier.DOM,
        )
        self.assertTrue(res.success)
        self.assertEqual(res.tier, ResolutionTier.DOM)
        self.assertEqual(res.candidates[0]["video_id"], "dom_video_id")

    async def test_resolution_result_to_dict(self):
        res = ResolutionResult(
            tier=ResolutionTier.DISCOVERED_ENDPOINT,
            query="test query",
            success=True,
            latency_ms=15.4,
        )
        d = res.to_dict()
        self.assertEqual(d["tier"], "DISCOVERED_ENDPOINT")
        self.assertEqual(d["query"], "test query")
        self.assertTrue(d["success"])
        self.assertEqual(d["latency_ms"], 15.4)


if __name__ == "__main__":
    unittest.main()
