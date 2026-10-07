"""
nebula_brain.py — Phase 4: Nebula Brain, Hybrid Mode
======================================================
Architecture (from plan):

  command → local parser → confident? ─yes→ execute
                                │ no
                                ▼
                        Gemini (JSON schema) → validate → execute
                                │ fail (invalid JSON / timeout / no key)
                                ▼
                        retry once → local fallback

Constraints:
  • AI outputs clean query + intent + steps only. NEVER raw URLs, IDs, or credentials.
  • pick_candidate(query, candidates) returns an integer index from a real candidate list.
  • Typo correction ("tamol" → "tamil") happens here via resolvers.youtube.normalize_query.
  • Budget: max 2 Gemini calls per command (1 plan + 1 recovery). Token cap per call.
  • Works fully with no GEMINI_API_KEY — local fallback always runs.

Public API
----------
NebulaBrain(use_voice=True)
    .plan(goal: str) -> Plan
        Full hybrid pipeline. Returns a validated Plan.

pick_candidate(query: str, candidates: list[Candidate]) -> int
    Selects best candidate index using token scoring (no AI).
    AI calls pick_candidate ONLY with a query string, never choosing a URL itself.

GeminiClient (replaceable for testing via dependency injection)
"""

from __future__ import annotations

import json
import os
import re
import time
import threading
from typing import Optional, Protocol

# Load .env if present (GEMINI_API_KEY, etc.)
try:
    import dotenv
    dotenv.load_dotenv(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        override=True
    )
except Exception:
    pass

from schemas import (
    Plan, IntentType, ActionType, Step,
    validate_plan, local_parse, ALLOWED_ACTIONS,
)
from resolvers.youtube import Candidate


# Lightweight typo-correction only (does NOT strip command words like the
# resolver's normalize_query does — the brain needs the full command intact).
_PHONETIC_FIXES: list[tuple[str, str]] = [
    (r'\btamol\b',     'tamil'),
    (r'\btelgu\b',     'telugu'),
    (r'\bmalaylam\b',  'malayalam'),
    (r'\bhinid\b',     'hindi'),
    (r'\benglsih\b',   'english'),
    (r'\byt\b',        'youtube'),
    (r'\bplaystore\b', 'google play'),
]


def _typo_correct(text: str) -> str:
    """Correct phonetic/spelling errors without stripping command structure."""
    import re as _re
    for pattern, replacement in _PHONETIC_FIXES:
        text = _re.sub(pattern, replacement, text, flags=_re.I)
    return text


# Alias used in pick_candidate (full normalizer is OK there — only called on
# the extracted query, not the full command).
def _norm_q(text: str) -> str:
    from resolvers.youtube import normalize_query
    return normalize_query(text)


# ---------------------------------------------------------------------------
# Constants / budget
# ---------------------------------------------------------------------------

_CONFIDENCE_THRESHOLD = 0.85   # local parser below this → escalate to AI
_GEMINI_TIMEOUT_S     = 8.0    # per-call timeout
_MAX_AI_RETRIES       = 1      # 1 retry on JSON / timeout failure, then local fallback
_MAX_CANDIDATES_SHOWN = 5      # titles passed to AI for pick_candidate

# Gemini model preference order (model name is configurable via .env)
_DEFAULT_MODEL = os.environ.get("NEBULA_AI_MODEL", "gemini-2.0-flash")


# ---------------------------------------------------------------------------
# GeminiClient Protocol (duck-typed for easy test mocking)
# ---------------------------------------------------------------------------

class GeminiClient(Protocol):
    """Minimal interface required by NebulaBrain. Mockable in tests."""

    def generate(self, prompt: str, timeout: float) -> str:
        """Returns raw text response. Raises on timeout or API error."""
        ...


class _RealGeminiClient:
    """Production Gemini client backed by google.generativeai."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model,
            system_instruction=(
                "You are Commander Nebula, the cognitive AI brain of the Orion "
                "Desktop Automation System.\n"
                "Rules:\n"
                "1. Correct ALL spelling and phonetic errors in the user query.\n"
                "2. Output ONLY strict JSON — no markdown, no prose.\n"
                "3. NEVER output raw URLs, video IDs, passwords, or API keys.\n"
                "4. The 'clean_query' field holds only the topic/song name — "
                "no command words like 'open', 'search', 'play it'.\n"
                "5. 'steps' is a list of action strings from: "
                + str(sorted(ALLOWED_ACTIONS)) + "\n"
                "6. Maximum 10 steps."
            )
        )

    def generate(self, prompt: str, timeout: float) -> str:
        result = {"text": None, "error": None}

        def _call():
            try:
                resp = self._model.generate_content(prompt)
                result["text"] = resp.text
            except Exception as exc:
                result["error"] = exc

        t = threading.Thread(target=_call, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            raise TimeoutError(f"Gemini call timed out after {timeout}s")
        if result["error"]:
            raise result["error"]
        return result["text"]


# ---------------------------------------------------------------------------
# pick_candidate — deterministic index selection (no AI)
# ---------------------------------------------------------------------------

def pick_candidate(query: str, candidates: list[Candidate]) -> int:
    """
    Return the index (0-based) of the best candidate given a query string.
    Uses token overlap + boost heuristics — identical logic to the resolver scorer.
    This is the ONLY function through which AI can influence candidate selection;
    the AI passes a clean query string, we return an integer.

    Args:
        query:      Normalized query string (AI-cleaned).
        candidates: List of Candidate dicts from resolvers.youtube.search().

    Returns:
        Index of best candidate (0 if list has one element, or all scores tie).
    """
    if not candidates:
        return 0

    norm = _norm_q(query)
    q_tokens = set(re.findall(r'[a-zA-Z0-9\u0B80-\u0BFF]+', norm.lower()))

    _BOOST = frozenset({'video song', 'official', 'audio', 'lyrics', 'full song', 'hd'})
    _PENALTY = frozenset({'cover', 'reaction', 'karaoke', 'remix', 'trailer', 'review'})

    best_idx, best_score = 0, -999.0

    for i, c in enumerate(candidates):
        title_lower = c.get('title', '').lower()
        c_tokens = set(re.findall(r'[a-zA-Z0-9\u0B80-\u0BFF]+', title_lower))
        score = float(len(q_tokens & c_tokens))
        for kw in _BOOST:
            if kw in title_lower:
                score += 0.5
        for kw in _PENALTY:
            if kw in title_lower:
                score -= 1.0

        if score > best_score:
            best_score = score
            best_idx = i

    return best_idx


# ---------------------------------------------------------------------------
# Gemini prompt builders
# ---------------------------------------------------------------------------

_PLAN_SCHEMA = """\
{
  "intent": "<media_play|web_search|tab_operation|desktop_app|voice|unknown>",
  "clean_query": "<corrected topic/song name only, no command words>",
  "steps": ["<action1>", "<action2>", ...],
  "confidence": <0.0-1.0>,
  "speech_announcement": "<short voice line for the user>"
}"""

_PICK_SCHEMA = """\
{
  "chosen_index": <integer 0 to N-1>
}"""


def _build_plan_prompt(goal: str) -> str:
    return (
        f'User command: "{goal}"\n\n'
        f"Analyze the command and return ONLY this JSON structure:\n{_PLAN_SCHEMA}\n\n"
        "Constraints:\n"
        "- clean_query must not contain 'open', 'youtube', 'search for', 'play it', etc.\n"
        "- steps is a list of action strings from ALLOWED_ACTIONS only.\n"
        "- If intent is media_play and portal is youtube, steps must include 'play'.\n"
        "- Output ONLY JSON. No markdown fences, no explanation."
    )


def _build_pick_prompt(query: str, candidates: list[Candidate]) -> str:
    titles = "\n".join(
        f"  {i}: {c['title']} [{c['channel']}] ({c['duration']})"
        for i, c in enumerate(candidates[:_MAX_CANDIDATES_SHOWN])
    )
    return (
        f'Query: "{query}"\n\n'
        f"Candidates:\n{titles}\n\n"
        f"Pick the best match. Return ONLY this JSON:\n{_PICK_SCHEMA}\n\n"
        "- chosen_index must be an integer between 0 and "
        f"{min(len(candidates), _MAX_CANDIDATES_SHOWN) - 1}.\n"
        "- Output ONLY JSON. No markdown fences."
    )


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` markdown fences if present."""
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def _parse_ai_plan(raw_text: str) -> dict:
    """Parse Gemini plan response into a raw dict for validate_plan()."""
    data = json.loads(_strip_fences(raw_text))

    intent   = data.get("intent", "unknown")
    query    = data.get("clean_query", "")
    ai_steps = data.get("steps", [])
    conf     = float(data.get("confidence", 0.7))
    speech   = data.get("speech_announcement", f"Done: {query}.")

    if len(ai_steps) > 10:
        raise ValueError(f"AI returned {len(ai_steps)} steps (max 10)")

    # Map AI step strings → Step dicts (AI never provides targets/URLs)
    built_steps = []
    for act_str in ai_steps:
        act_str = act_str.strip().lower()
        if act_str not in ALLOWED_ACTIONS:
            raise ValueError(f"AI returned disallowed action: {act_str!r}")
        agent = (
            "Perception Inspector" if act_str == "screenshot"
            else "Studio Narrator"  if act_str == "speak"
            else "Chrome Executor"
        )
        step_dict: dict = {"action": act_str, "agent": agent, "desc": f"[AI] {act_str}"}

        if act_str == "speak":
            step_dict["target"] = speech
        if act_str in ("play", "browse", "search"):
            step_dict["query"]  = query
            step_dict["portal"] = "youtube" if intent == "media_play" else None
            step_dict["play"]   = (act_str == "play")

        built_steps.append(step_dict)

    return {
        "intent":     intent,
        "confidence": conf,
        "steps":      built_steps,
        "ai_used":    True,
    }


def _parse_ai_pick(raw_text: str, n_candidates: int) -> int:
    data = json.loads(_strip_fences(raw_text))
    idx = int(data["chosen_index"])
    if not (0 <= idx < n_candidates):
        raise ValueError(f"chosen_index {idx} out of range [0, {n_candidates})")
    return idx


# ---------------------------------------------------------------------------
# NebulaBrain
# ---------------------------------------------------------------------------

class NebulaBrain:
    """
    Hybrid cognitive engine for Orion/Nebula.

    Usage::

        brain = NebulaBrain()
        plan  = brain.plan("open youtube and search for a kangal neeye tamol song and play it")
        # plan is a validated Plan; brain chose local or AI path automatically.

    Inject a mock client for testing::

        brain = NebulaBrain(client=MockGeminiClient())
    """

    def __init__(
        self,
        use_voice: bool = True,
        client: Optional[GeminiClient] = None,
    ):
        self.use_voice = use_voice
        self._client: Optional[GeminiClient] = client or self._build_client()

    # ------------------------------------------------------------------
    @property
    def has_ai_brain(self) -> bool:
        return self._client is not None

    # ------------------------------------------------------------------
    @staticmethod
    def _build_client() -> Optional[GeminiClient]:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return None
        try:
            return _RealGeminiClient(api_key=api_key, model=_DEFAULT_MODEL)
        except Exception:
            return None

    # ------------------------------------------------------------------
    def plan(self, goal: str) -> Plan:
        """
        Full hybrid pipeline.

        1. Normalise query.
        2. Try local_parse.  If confidence ≥ threshold → return.
        3. If AI available, call Gemini.  Validate response.
        4. On failure, retry once.  If still failing → local fallback.
        5. Always return a validated Plan.
        """
        # Typo correction only — keeps command structure intact for local_parse
        corrected_goal = _typo_correct(goal)

        # --- Path A: local parser ---
        local_plan = local_parse(corrected_goal)
        if local_plan is not None and local_plan.confidence >= _CONFIDENCE_THRESHOLD:
            return local_plan

        # --- Path B: AI brain ---
        if self._client is not None:
            for attempt in range(1, _MAX_AI_RETRIES + 2):  # 1 + 1 retry
                try:
                    raw_text = self._client.generate(
                        _build_plan_prompt(corrected_goal),
                        timeout=_GEMINI_TIMEOUT_S,
                    )
                    raw_dict = _parse_ai_plan(raw_text)
                    return validate_plan(raw_dict)
                except (TimeoutError, json.JSONDecodeError, ValueError, Exception):
                    if attempt > _MAX_AI_RETRIES:
                        break   # exhausted retries → fall through to local

        # --- Path C: local fallback (always works) ---
        if local_plan is not None:
            return local_plan

        # Absolute last resort: bare browse step
        return validate_plan({
            "intent": "web_search",
            "confidence": 0.3,
            "steps": [
                {"action": "browse", "agent": "Chrome Executor",
                 "target": None, "query": corrected_goal,
                 "desc": f"[Fallback] Navigate for: {corrected_goal}"},
                {"action": "screenshot", "agent": "Perception Inspector",
                 "desc": "Verify result"},
            ],
        })

    # ------------------------------------------------------------------
    def pick_candidate_with_ai(
        self,
        query: str,
        candidates: list[Candidate],
    ) -> int:
        """
        Use AI to pick the best candidate index from a real list.
        Falls back to deterministic pick_candidate() if AI is unavailable or fails.

        The AI receives only: query string + candidate titles/channels/durations.
        It returns an integer index. URLs are never passed to or from the AI.
        """
        if not candidates:
            return 0

        if self._client is not None:
            for attempt in range(1, _MAX_AI_RETRIES + 2):
                try:
                    raw_text = self._client.generate(
                        _build_pick_prompt(query, candidates),
                        timeout=_GEMINI_TIMEOUT_S,
                    )
                    return _parse_ai_pick(raw_text, n_candidates=len(candidates))
                except Exception:
                    if attempt > _MAX_AI_RETRIES:
                        break

        # Deterministic local fallback
        return pick_candidate(query, candidates)
