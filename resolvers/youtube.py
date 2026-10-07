"""
resolvers/youtube.py — Phase 2: Real Media Resolver
============================================================
Principle: Code does the work. AI only decides (via pick_candidate).
This module never calls any AI. It fetches real YouTube search results,
parses the embedded ytInitialData JSON, filters junk, scores candidates,
and caches results with a TTL.

Public API
----------
search(query: str) -> list[Candidate]
    Returns up to 10 filtered, scored candidates.

Candidate (TypedDict)
    index     : int          position in the candidate list
    video_id  : str          11-char YouTube video ID
    title     : str
    channel   : str
    duration  : str          human-readable "m:ss"
    duration_s: int          seconds (0 if live/unknown)
    is_live   : bool
    score     : float        token-overlap + boost score
    url       : str          watch URL (no autoplay param — caller adds)
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from typing import TypedDict, Optional

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class Candidate(TypedDict):
    index: int
    video_id: str
    title: str
    channel: str
    duration: str
    duration_s: int
    is_live: bool
    score: float
    url: str


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_PHONETIC_FIXES: list[tuple[str, str]] = [
    (r'\btamol\b',     'tamil'),
    (r'\btelgu\b',     'telugu'),
    (r'\bmalaylam\b',  'malayalam'),
    (r'\bhinid\b',     'hindi'),
    (r'\benglsih\b',   'english'),
    (r'\byt\b',        'youtube'),
]

def normalize_query(query: str) -> str:
    """Correct typos and strip command boilerplate."""
    s = query.strip().lower()
    for pattern, replacement in _PHONETIC_FIXES:
        s = re.sub(pattern, replacement, s, flags=re.I)
    # Strip command noise so the scorer sees only the song/topic words
    s = re.sub(
        r'\b(open|launch|go to|youtube|search|for|a|an|the|'
        r'play it|play|listen to|start it|start|and)\b',
        ' ', s, flags=re.I
    )
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _duration_to_seconds(dur: str) -> int:
    """'4:32' → 272, '1:02:45' → 3765, '' → 0."""
    if not dur:
        return 0
    parts = dur.split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return 0


# ---------------------------------------------------------------------------
# ytInitialData parser
# ---------------------------------------------------------------------------

def _extract_candidates_from_data(data: dict) -> list[Candidate]:
    """Walk ytInitialData and extract raw videoRenderer items."""
    raw: list[Candidate] = []
    try:
        sections = (
            data.get('contents', {})
            .get('twoColumnSearchResultsRenderer', {})
            .get('primaryContents', {})
            .get('sectionListRenderer', {})
            .get('contents', [])
        )
    except AttributeError:
        return raw

    for section in sections:
        items = section.get('itemSectionRenderer', {}).get('contents', [])
        for item in items:
            vr = item.get('videoRenderer')
            if not vr:
                continue

            video_id: str = vr.get('videoId', '')
            if not video_id or len(video_id) != 11:
                continue

            title: str = ''.join(
                r.get('text', '') for r in vr.get('title', {}).get('runs', [])
            )
            channel: str = ''.join(
                r.get('text', '') for r in vr.get('ownerText', {}).get('runs', [])
            )
            duration_str: str = vr.get('lengthText', {}).get('simpleText', '')

            # Live-stream detection: no duration or explicit badge
            badges = vr.get('badges', [])
            is_live = (
                not duration_str or
                any('LIVE' in json.dumps(b).upper() for b in badges)
            )

            raw.append({
                'index':      len(raw),
                'video_id':   video_id,
                'title':      title,
                'channel':    channel,
                'duration':   duration_str,
                'duration_s': _duration_to_seconds(duration_str),
                'is_live':    is_live,
                'score':      0.0,
                'url':        f'https://www.youtube.com/watch?v={video_id}',
            })

    return raw


def _extract_from_html(html: str) -> list[Candidate]:
    """Parse ytInitialData from raw HTML.  Falls back to regex if JSON fails."""
    m = re.search(r'var ytInitialData = ({.*?});</script>', html)
    if m:
        try:
            data = json.loads(m.group(1))
            candidates = _extract_candidates_from_data(data)
            if candidates:
                return candidates
        except (json.JSONDecodeError, KeyError):
            pass

    # Regex fallback: deduplicated watch IDs with no metadata
    seen: set[str] = set()
    fallback: list[Candidate] = []
    for vid in re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html):
        if vid in seen:
            continue
        seen.add(vid)
        fallback.append({
            'index':      len(fallback),
            'video_id':   vid,
            'title':      '',
            'channel':    '',
            'duration':   '',
            'duration_s': 0,
            'is_live':    False,
            'score':      0.0,
            'url':        f'https://www.youtube.com/watch?v={vid}',
        })
        if len(fallback) >= 10:
            break

    return fallback


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

_MIN_SONG_SECONDS = 60    # ignore clips under 1 minute (Shorts, teasers)
_MAX_SONG_SECONDS = 3600  # ignore anything over 1 hour


def _filter(candidates: list[Candidate], allow_live: bool = False) -> list[Candidate]:
    """Remove Shorts, live streams, and overly long clips."""
    result = []
    for c in candidates:
        if c['is_live'] and not allow_live:
            continue
        dur = c['duration_s']
        if dur > 0 and (dur < _MIN_SONG_SECONDS or dur > _MAX_SONG_SECONDS):
            continue
        result.append(c)
    return result


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_BOOST_KEYWORDS = frozenset({
    'video song', 'official', 'audio', 'lyrics', 'full song', 'hd', '4k', '8k'
})

_PENALTY_KEYWORDS = frozenset({
    'cover', 'reaction', 'karaoke', 'remix', 'mashup', 'trailer',
    'review', 'piano', 'guitar', 'instrumental'
})


def _score(query_normalized: str, candidates: list[Candidate]) -> list[Candidate]:
    """Score each candidate by token overlap against the normalized query."""
    q_tokens = set(re.findall(r'[a-zA-Z0-9\u0B80-\u0BFF]+', query_normalized.lower()))

    for c in candidates:
        title_lower = c['title'].lower()
        title_tokens = set(re.findall(r'[a-zA-Z0-9\u0B80-\u0BFF]+', title_lower))

        overlap = len(q_tokens & title_tokens)
        score = float(overlap)

        for kw in _BOOST_KEYWORDS:
            if kw in title_lower:
                score += 0.5

        for kw in _PENALTY_KEYWORDS:
            if kw in title_lower:
                score -= 1.0

        c['score'] = score

    candidates.sort(key=lambda c: c['score'], reverse=True)
    for i, c in enumerate(candidates):
        c['index'] = i

    return candidates


# ---------------------------------------------------------------------------
# TTL Cache
# ---------------------------------------------------------------------------

class _TTLCache:
    def __init__(self, ttl_seconds: int = 600):
        self._store: dict[str, tuple[float, list[Candidate]]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[list[Candidate]]:
        entry = self._store.get(key)
        if entry and time.time() - entry[0] < self._ttl:
            return entry[1]
        return None

    def set(self, key: str, value: list[Candidate]) -> None:
        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        self._store.clear()


_cache = _TTLCache(ttl_seconds=600)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/122.0.0.0 Safari/537.36'
)


def search(query: str, max_results: int = 10, allow_live: bool = False) -> list[Candidate]:
    """
    Search YouTube and return up to max_results scored, filtered candidates.
    Results are cached for 10 minutes per normalized query.

    Args:
        query:       Raw user query (typos allowed).
        max_results: Maximum candidates to return (default 10).
        allow_live:  If True, include live streams.

    Returns:
        Sorted list of Candidate dicts, best match first.
    """
    norm_q = normalize_query(query)
    cache_key = f'{norm_q}|live={allow_live}'

    cached = _cache.get(cache_key)
    if cached is not None:
        return cached[:max_results]

    encoded = urllib.parse.quote_plus(norm_q)
    url = f'https://www.youtube.com/results?search_query={encoded}'

    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': _USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9',
        }
    )
    try:
        html = urllib.request.urlopen(req, timeout=8).read().decode('utf-8', errors='ignore')
    except Exception as exc:
        raise RuntimeError(f'YouTube search request failed: {exc}') from exc

    raw = _extract_from_html(html)
    filtered = _filter(raw, allow_live=allow_live)
    scored = _score(norm_q, filtered)

    _cache.set(cache_key, scored)
    return scored[:max_results]


def search_from_fixture(fixture_data: dict, query: str, max_results: int = 10) -> list[Candidate]:
    """
    Parse candidates from a pre-saved ytInitialData dict (for offline tests).
    Does not hit the network.
    """
    norm_q = normalize_query(query)
    raw = _extract_candidates_from_data(fixture_data)
    filtered = _filter(raw)
    scored = _score(norm_q, filtered)
    return scored[:max_results]
