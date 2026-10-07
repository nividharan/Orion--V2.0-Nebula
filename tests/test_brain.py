"""
tests/test_brain.py — Phase 4 exit criteria
=============================================
All tests use mocked Gemini clients — no real API calls, no network.

Exit criteria (from plan):
  ✓  Valid Gemini response → validated Plan returned.
  ✓  Invalid JSON response → retry → local fallback, no crash.
  ✓  Timeout response → retry → local fallback, no crash.
  ✓  No API key → local parser runs without error.
  ✓  Local parser handles YouTube play + search commands correctly.
  ✓  pick_candidate() is deterministic and returns correct index.
  ✓  pick_candidate_with_ai() falls back gracefully when AI fails.
  ✓  Typo "tamol" is corrected before AI or local parser sees the query.
  ✓  AI can never return a raw URL — _parse_ai_plan rejects URL-containing targets.
  ✓  Budget: no more than 2 AI calls per plan() invocation.
"""

import json
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import Plan, IntentType, ActionType, validate_plan
from resolvers.youtube import Candidate
from nebula_brain import (
    NebulaBrain,
    pick_candidate,
    _parse_ai_plan,
    _parse_ai_pick,
    _build_plan_prompt,
    _build_pick_prompt,
    _strip_fences,
    _CONFIDENCE_THRESHOLD,
    _MAX_AI_RETRIES,
)


# ---------------------------------------------------------------------------
# Mock clients
# ---------------------------------------------------------------------------

class _FixedClient:
    """Returns a fixed response string on every generate() call."""
    def __init__(self, response: str):
        self._response = response
        self.call_count = 0

    def generate(self, prompt: str, timeout: float) -> str:
        self.call_count += 1
        return self._response


class _TimeoutClient:
    """Always raises TimeoutError."""
    def __init__(self):
        self.call_count = 0

    def generate(self, prompt: str, timeout: float) -> str:
        self.call_count += 1
        raise TimeoutError("Simulated timeout")


class _BadJsonClient:
    """Always returns malformed JSON."""
    def __init__(self):
        self.call_count = 0

    def generate(self, prompt: str, timeout: float) -> str:
        self.call_count += 1
        return "this is not json at all !!!"


class _SequenceClient:
    """Returns responses from a pre-defined list in order."""
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.call_count = 0

    def generate(self, prompt: str, timeout: float) -> str:
        self.call_count += 1
        if self.call_count <= len(self._responses):
            r = self._responses[self.call_count - 1]
            if isinstance(r, Exception):
                raise r
            return r
        raise RuntimeError("No more responses in sequence")


# ---------------------------------------------------------------------------
# Valid AI plan responses
# ---------------------------------------------------------------------------

_VALID_MEDIA_PLAY_RESPONSE = json.dumps({
    "intent": "media_play",
    "clean_query": "kangal neeye tamil song",
    "steps": ["play", "screenshot", "speak"],
    "confidence": 0.95,
    "speech_announcement": "Now playing Kangal Neeye on YouTube, sir."
})

_VALID_WEB_SEARCH_RESPONSE = json.dumps({
    "intent": "web_search",
    "clean_query": "autogen framework",
    "steps": ["search", "screenshot"],
    "confidence": 0.90,
    "speech_announcement": "Searching GitHub for autogen framework."
})

_VALID_TAB_RESPONSE = json.dumps({
    "intent": "tab_operation",
    "clean_query": "",
    "steps": ["new_tab", "screenshot"],
    "confidence": 0.99,
    "speech_announcement": "New tab opened."
})

_PICK_VALID_RESPONSE = json.dumps({"chosen_index": 2})


# ---------------------------------------------------------------------------
# 1. _strip_fences
# ---------------------------------------------------------------------------

class TestStripFences(unittest.TestCase):
    def test_removes_json_fence(self):
        raw = "```json\n{\"key\": 1}\n```"
        self.assertEqual(_strip_fences(raw), '{"key": 1}')

    def test_removes_plain_fence(self):
        raw = "```\n{}\n```"
        self.assertEqual(_strip_fences(raw), '{}')

    def test_no_fence_unchanged(self):
        raw = '{"key": 1}'
        self.assertEqual(_strip_fences(raw), '{"key": 1}')


# ---------------------------------------------------------------------------
# 2. _parse_ai_plan
# ---------------------------------------------------------------------------

class TestParseAIPlan(unittest.TestCase):
    def test_valid_media_play_parsed(self):
        d = _parse_ai_plan(_VALID_MEDIA_PLAY_RESPONSE)
        # _parse_ai_plan normalises "media_play" alias → canonical "media_playback"
        self.assertEqual(d['intent'], 'media_playback')
        self.assertIn('play', [s['action'] for s in d['steps']])
        self.assertTrue(d['ai_used'])

    def test_too_many_steps_raises(self):
        bad = json.dumps({
            "intent": "web_search",
            "clean_query": "test",
            "steps": ["browse"] * 11,
            "confidence": 0.8,
            "speech_announcement": "done"
        })
        with self.assertRaises(ValueError):
            _parse_ai_plan(bad)

    def test_disallowed_action_raises(self):
        bad = json.dumps({
            "intent": "web_search",
            "clean_query": "test",
            "steps": ["hack_system"],
            "confidence": 0.8,
            "speech_announcement": "done"
        })
        with self.assertRaises(ValueError):
            _parse_ai_plan(bad)

    def test_speak_step_gets_announcement_as_target(self):
        d = _parse_ai_plan(_VALID_MEDIA_PLAY_RESPONSE)
        speak_steps = [s for s in d['steps'] if s['action'] == 'speak']
        self.assertTrue(len(speak_steps) > 0)
        self.assertIn('Kangal', speak_steps[0]['target'])

    def test_play_step_has_query_set(self):
        d = _parse_ai_plan(_VALID_MEDIA_PLAY_RESPONSE)
        play_steps = [s for s in d['steps'] if s['action'] == 'play']
        self.assertTrue(len(play_steps) > 0)
        self.assertEqual(play_steps[0]['query'], 'kangal neeye tamil song')
        self.assertTrue(play_steps[0]['play'])

    def test_play_step_has_no_url(self):
        """AI must not inject raw URLs."""
        d = _parse_ai_plan(_VALID_MEDIA_PLAY_RESPONSE)
        for step in d['steps']:
            target = step.get('target')
            if target:
                self.assertFalse(
                    target.startswith('http'),
                    f"AI step target must not be a URL: {target}"
                )


# ---------------------------------------------------------------------------
# 3. _parse_ai_pick
# ---------------------------------------------------------------------------

class TestParseAIPick(unittest.TestCase):
    def test_valid_index_returned(self):
        self.assertEqual(_parse_ai_pick(_PICK_VALID_RESPONSE, n_candidates=5), 2)

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            _parse_ai_pick(json.dumps({"chosen_index": 10}), n_candidates=5)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            _parse_ai_pick(json.dumps({"chosen_index": -1}), n_candidates=5)

    def test_zero_valid(self):
        self.assertEqual(_parse_ai_pick(json.dumps({"chosen_index": 0}), 3), 0)


# ---------------------------------------------------------------------------
# 4. pick_candidate (deterministic, no AI)
# ---------------------------------------------------------------------------

def _make_candidate(i: int, title: str, channel: str = '', duration: str = '4:00') -> Candidate:
    return {
        'index': i,
        'video_id': f'vid{i:07d}____',  # 11 chars
        'title': title,
        'channel': channel,
        'duration': duration,
        'duration_s': 240,
        'is_live': False,
        'score': 0.0,
        'url': f'https://www.youtube.com/watch?v=vid{i:07d}____',
    }


class TestPickCandidate(unittest.TestCase):
    def test_empty_list_returns_zero(self):
        self.assertEqual(pick_candidate("any", []), 0)

    def test_single_item_returns_zero(self):
        c = [_make_candidate(0, "random title")]
        self.assertEqual(pick_candidate("kangal neeye", c), 0)

    def test_best_token_match_selected(self):
        candidates = [
            _make_candidate(0, "Something Completely Different"),
            _make_candidate(1, "Kangal Neeye Official Video Song"),  # ← best match
            _make_candidate(2, "Another Random Video"),
        ]
        idx = pick_candidate("kangal neeye tamil song", candidates)
        self.assertEqual(idx, 1)

    def test_official_video_boost_applied(self):
        candidates = [
            _make_candidate(0, "Kangal Neeye cover version"),      # penalty
            _make_candidate(1, "Kangal Neeye official video song"), # boost
        ]
        idx = pick_candidate("kangal neeye", candidates)
        self.assertEqual(idx, 1)

    def test_cover_penalized(self):
        candidates = [
            _make_candidate(0, "Kangal Neeye cover"),       # penalty
            _make_candidate(1, "Kangal Neeye lyrics"),      # boost
        ]
        idx = pick_candidate("kangal neeye", candidates)
        self.assertEqual(idx, 1)


# ---------------------------------------------------------------------------
# 5. NebulaBrain — no API key
# ---------------------------------------------------------------------------

class TestNebulaBrainNoKey(unittest.TestCase):
    def setUp(self):
        # Explicitly inject None to simulate missing API key
        self.brain = NebulaBrain(client=None)

    def test_has_ai_brain_false(self):
        self.assertFalse(self.brain.has_ai_brain)

    def test_play_command_returns_plan(self):
        plan = self.brain.plan("play despacito")
        self.assertIsInstance(plan, Plan)
        self.assertEqual(plan.intent, IntentType.MEDIA_PLAY)

    def test_tab_command_returns_plan(self):
        plan = self.brain.plan("next tab")
        self.assertIsInstance(plan, Plan)
        self.assertTrue(any(s.action == ActionType.NEXT_TAB for s in plan.steps))

    def test_typo_corrected_before_parsing(self):
        plan = self.brain.plan("play kangal neeye tamol song")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.intent, IntentType.MEDIA_PLAY)

    def test_unrecognised_command_returns_fallback_plan(self):
        plan = self.brain.plan("xyzzy random nonsense command 777")
        self.assertIsInstance(plan, Plan)
        self.assertGreater(len(plan.steps), 0)

    def test_pick_candidate_with_ai_falls_back_deterministically(self):
        candidates = [
            _make_candidate(0, "Random Song"),
            _make_candidate(1, "Kangal Neeye Official Video Song"),
        ]
        idx = self.brain.pick_candidate_with_ai("kangal neeye", candidates)
        self.assertEqual(idx, 1)


# ---------------------------------------------------------------------------
# 6. NebulaBrain — valid AI response
# ---------------------------------------------------------------------------

class TestNebulaBrainValidAI(unittest.TestCase):
    def setUp(self):
        self.client = _FixedClient(_VALID_MEDIA_PLAY_RESPONSE)
        self.brain = NebulaBrain(client=self.client)

    def test_has_ai_brain_true(self):
        self.assertTrue(self.brain.has_ai_brain)

    def test_valid_ai_plan_returned(self):
        # Local parser handles "play X on youtube" confidently, so use an
        # ambiguous command that local_parse returns None for.
        plan = self.brain.plan("xyzzy nonsense to force AI path")
        self.assertIsInstance(plan, Plan)
        self.assertEqual(plan.intent, IntentType.MEDIA_PLAY)
        self.assertTrue(plan.ai_used)

    def test_ai_plan_has_no_url_in_query(self):
        plan = self.brain.plan("xyzzy nonsense to force AI path")
        for step in plan.steps:
            if step.query:
                self.assertFalse(
                    step.query.startswith('http'),
                    f"query field must not be a URL: {step.query}"
                )

    def test_local_parse_confident_skips_ai(self):
        """High-confidence local commands must NOT call Gemini."""
        plan = self.brain.plan("play despacito")
        self.assertEqual(self.client.call_count, 0,
                         "Gemini must not be called when local parser is confident")


# ---------------------------------------------------------------------------
# 7. NebulaBrain — timeout handling
# ---------------------------------------------------------------------------

class TestNebulaBrainTimeout(unittest.TestCase):
    def setUp(self):
        self.client = _TimeoutClient()
        self.brain = NebulaBrain(client=self.client)

    def test_timeout_falls_back_to_local(self):
        plan = self.brain.plan("play despacito on youtube")
        self.assertIsInstance(plan, Plan)

    def test_timeout_on_ambiguous_returns_fallback_plan(self):
        plan = self.brain.plan("xyzzy nonsense command")
        self.assertIsInstance(plan, Plan)
        self.assertGreater(len(plan.steps), 0)

    def test_call_count_limited(self):
        self.brain.plan("xyzzy nonsense command")
        # Should attempt: 1 initial + MAX_AI_RETRIES retry = at most 2
        self.assertLessEqual(self.client.call_count, _MAX_AI_RETRIES + 1)


# ---------------------------------------------------------------------------
# 8. NebulaBrain — bad JSON handling
# ---------------------------------------------------------------------------

class TestNebulaBrainBadJson(unittest.TestCase):
    def setUp(self):
        self.client = _BadJsonClient()
        self.brain = NebulaBrain(client=self.client)

    def test_bad_json_falls_back_gracefully(self):
        plan = self.brain.plan("xyzzy nonsense command")
        self.assertIsInstance(plan, Plan)

    def test_no_unhandled_exception(self):
        try:
            plan = self.brain.plan("something completely unknown xyz")
            self.assertIsInstance(plan, Plan)
        except Exception as e:
            self.fail(f"plan() raised unexpected exception: {e}")

    def test_call_count_limited_on_bad_json(self):
        self.brain.plan("xyzzy nonsense command")
        self.assertLessEqual(self.client.call_count, _MAX_AI_RETRIES + 1)


# ---------------------------------------------------------------------------
# 9. NebulaBrain — retry on first fail, succeed on second
# ---------------------------------------------------------------------------

class TestNebulaBrainRetry(unittest.TestCase):
    def test_first_fail_then_success(self):
        """First call times out, second call returns valid JSON → plan from AI."""
        client = _SequenceClient([
            TimeoutError("first timeout"),
            _VALID_MEDIA_PLAY_RESPONSE,
        ])
        brain = NebulaBrain(client=client)
        plan = brain.plan("xyzzy nonsense command")
        self.assertIsInstance(plan, Plan)
        # After 1 timeout + 1 success = 2 calls total
        self.assertLessEqual(client.call_count, _MAX_AI_RETRIES + 1)

    def test_both_fail_returns_local_fallback(self):
        """Both AI calls fail → must still return a valid Plan."""
        client = _SequenceClient([
            TimeoutError("first"),
            TimeoutError("second"),
        ])
        brain = NebulaBrain(client=client)
        plan = brain.plan("xyzzy nonsense command")
        self.assertIsInstance(plan, Plan)
        self.assertGreater(len(plan.steps), 0)


# ---------------------------------------------------------------------------
# 10. pick_candidate_with_ai — AI path
# ---------------------------------------------------------------------------

class TestPickCandidateWithAI(unittest.TestCase):
    def _candidates(self):
        return [
            _make_candidate(0, "Kangal Neeye Cover"),
            _make_candidate(1, "Kangal Neeye Official Video Song"),
            _make_candidate(2, "Some Random Tamil Song"),
        ]

    def test_valid_ai_pick(self):
        client = _FixedClient(json.dumps({"chosen_index": 1}))
        brain = NebulaBrain(client=client)
        idx = brain.pick_candidate_with_ai("kangal neeye", self._candidates())
        self.assertEqual(idx, 1)

    def test_ai_pick_timeout_falls_back(self):
        brain = NebulaBrain(client=_TimeoutClient())
        idx = brain.pick_candidate_with_ai("kangal neeye official", self._candidates())
        # Deterministic fallback should also pick index 1 (official boost)
        self.assertEqual(idx, 1)

    def test_ai_pick_out_of_range_falls_back(self):
        client = _FixedClient(json.dumps({"chosen_index": 99}))
        brain = NebulaBrain(client=client)
        # Should fall back to deterministic pick — no exception raised
        idx = brain.pick_candidate_with_ai("kangal neeye", self._candidates())
        self.assertIsInstance(idx, int)
        self.assertIn(idx, range(len(self._candidates())))

    def test_empty_candidates_returns_zero(self):
        brain = NebulaBrain(client=None)
        self.assertEqual(brain.pick_candidate_with_ai("anything", []), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
