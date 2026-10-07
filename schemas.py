"""
schemas.py — Phase 3: Structured Plan and Validation
======================================================
Principle: The AI outputs steps only. This module validates and rejects
any plan that references disallowed actions, disallowed domains, or
exceeds the 10-step limit before any execution occurs.

Public API
----------
IntentType     — enum of recognised intent categories
ActionType     — enum of allowed step actions (ALLOWED_ACTIONS)
Step           — Pydantic model for a single milestone
Plan           — Pydantic model for the full execution plan
validate_plan  — parses and validates a raw dict, raises ValidationError on failure
local_parse    — rule-based parser for common commands (no AI required)
"""

from __future__ import annotations

import re
import urllib.parse
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Security constants
# ---------------------------------------------------------------------------

ALLOWED_DOMAINS: frozenset[str] = frozenset({
    'youtube.com', 'www.youtube.com',
    'google.com', 'www.google.com',
    'github.com', 'www.github.com',
    'wikipedia.org', 'en.wikipedia.org',
    'reddit.com', 'www.reddit.com',
    'amazon.com', 'www.amazon.com',
    'play.google.com',
    'x.com', 'twitter.com',
    'udemy.com', 'www.udemy.com',
    'linkedin.com', 'www.linkedin.com',
    'notepad',   # desktop target, not a URL
    'chrome',
    'explorer',
    'calculator',
    'settings',
})

# Actions that require explicit user approval before execution
SENSITIVE_ACTIONS: frozenset[str] = frozenset({
    'submit_payment', 'delete_account', 'place_order',
    'send_message', 'download_file',
})


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IntentType(str, Enum):
    MEDIA_PLAY    = 'media_play'
    WEB_SEARCH    = 'web_search'
    TAB_OPERATION = 'tab_operation'
    DESKTOP_APP   = 'desktop_app'
    VOICE         = 'voice'
    UNKNOWN       = 'unknown'


class ActionType(str, Enum):
    BROWSE         = 'browse'
    SEARCH         = 'search'
    PLAY           = 'play'
    OPEN_APP       = 'open_app'
    CLOSE          = 'close'
    NEW_TAB        = 'new_tab'
    CLOSE_TAB      = 'close_tab'
    NEXT_TAB       = 'next_tab'
    PREV_TAB       = 'prev_tab'
    REOPEN_TAB     = 'reopen_tab'
    SCROLL_DOWN    = 'scroll_down'
    SCROLL_UP      = 'scroll_up'
    SCREENSHOT     = 'screenshot'
    SPEAK          = 'speak'
    LISTEN         = 'listen'


# Derived set for quick membership tests
ALLOWED_ACTIONS: frozenset[str] = frozenset(a.value for a in ActionType)


# ---------------------------------------------------------------------------
# Step model
# ---------------------------------------------------------------------------

class Step(BaseModel):
    """A single atomic execution milestone."""

    action: ActionType
    agent: str = Field(default='Chrome Executor', min_length=1)
    target: Optional[str] = None     # URL, app name, or text, never a raw credential
    query: Optional[str] = None      # Clean search/song query (no boilerplate)
    portal: Optional[str] = None
    play: bool = False
    desc: str = Field(default='', min_length=0)
    requires_approval: bool = False  # set True for SENSITIVE_ACTIONS

    @field_validator('target')
    @classmethod
    def target_domain_allowed(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Only validate URL-shaped targets
        if v.startswith('http://') or v.startswith('https://'):
            try:
                parsed = urllib.parse.urlparse(v)
                host = parsed.netloc.lower()
                if host not in ALLOWED_DOMAINS:
                    raise ValueError(
                        f"Domain '{host}' is not in ALLOWED_DOMAINS. "
                        f"Add it explicitly if this site should be accessible."
                    )
            except ValueError:
                raise
            except Exception:
                pass  # non-URL targets are fine
        return v

    @field_validator('query')
    @classmethod
    def query_no_credentials(cls, v: Optional[str]) -> Optional[str]:
        """Reject queries that look like passwords or tokens."""
        if v and re.search(r'(?i)(password|token|secret|api.?key|bearer)', v):
            raise ValueError('query must not contain credential-like content')
        return v


# ---------------------------------------------------------------------------
# Plan model
# ---------------------------------------------------------------------------

class Plan(BaseModel):
    """Full execution plan produced by Nebula (AI or local parser)."""

    intent: IntentType = IntentType.UNKNOWN
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    steps: List[Step] = Field(default_factory=list)
    ai_used: bool = False         # True if Gemini produced this plan

    @field_validator('steps')
    @classmethod
    def max_ten_steps(cls, v: list) -> list:
        if len(v) > 10:
            raise ValueError(f'Plan exceeds 10-step limit ({len(v)} steps given)')
        if len(v) == 0:
            raise ValueError('Plan must contain at least one step')
        return v

    @model_validator(mode='after')
    def flag_sensitive_steps(self) -> Plan:
        for step in self.steps:
            if step.action.value in SENSITIVE_ACTIONS:
                step.requires_approval = True
        return self


def validate_plan(raw: dict) -> Plan:
    """
    Parse and validate a raw dict into a Plan.
    Raises pydantic.ValidationError with descriptive messages on failure.
    """
    return Plan.model_validate(raw)


# ---------------------------------------------------------------------------
# Local rule-based parser (no AI) — Phase 3 exit criteria
# ---------------------------------------------------------------------------

# Ordered list of (regex, builder_fn) pairs.
# Each builder returns a Plan dict.

def _portal_url(portal: str, query: str) -> str:
    q = urllib.parse.quote_plus(query)
    mapping = {
        'youtube':     f'https://www.youtube.com/results?search_query={q}',
        'google':      f'https://www.google.com/search?q={q}',
        'github':      f'https://github.com/search?q={q}',
        'wikipedia':   f'https://en.wikipedia.org/wiki/Special:Search?search={q}',
        'reddit':      f'https://www.reddit.com/search/?q={q}',
        'amazon':      f'https://www.amazon.com/s?k={q}',
        'google play': f'https://play.google.com/store/search?q={q}&c=apps',
    }
    return mapping.get(portal.lower(), f'https://www.google.com/search?q={q}')


_RULES: list[tuple[re.Pattern, callable]] = []


def _rule(pattern: str):
    """Decorator to register a parser rule."""
    def decorator(fn):
        _RULES.append((re.compile(pattern, re.I), fn))
        return fn
    return decorator


# Rule 1: direct play on YouTube
@_rule(r'^(?:play|listen to|start)\s+(.+?)(?:\s+on\s+youtube)?$')
def _r_play(m: re.Match) -> dict:
    query = m.group(1).strip()
    return {
        'intent': IntentType.MEDIA_PLAY,
        'confidence': 0.95,
        'steps': [
            {'action': ActionType.PLAY, 'agent': 'Chrome Executor',
             'query': query, 'portal': 'youtube', 'play': True,
             'target': None,
             'desc': f"Play '{query}' on YouTube"},
            {'action': ActionType.SCREENSHOT, 'agent': 'Perception Inspector',
             'desc': 'Verify video playback'},
            {'action': ActionType.SPEAK, 'agent': 'Studio Narrator',
             'target': f"Now playing {query} on YouTube, sir.",
             'desc': 'Announce playback'},
        ]
    }


# Rule 2: open <portal> and search for <query> [and play it]
@_rule(
    r'^(?:open|launch|go to)\s+'
    r'(google play|play store|youtube|github|amazon|wikipedia|reddit|google)\s+'
    r'and\s+(?:search|look up)\s+(?:for\s+)?(.+?)(?:\s+and\s+play\s+it)?$'
)
def _r_open_search(m: re.Match) -> dict:
    portal = m.group(1).strip().lower()
    query  = m.group(2).strip()
    should_play = bool(re.search(r'\bplay\b', m.group(0).split('search')[-1], re.I))
    url = _portal_url(portal, query)
    return {
        'intent': IntentType.MEDIA_PLAY if should_play else IntentType.WEB_SEARCH,
        'confidence': 0.90,
        'steps': [
            {'action': ActionType.PLAY if should_play else ActionType.BROWSE,
             'agent': 'Chrome Executor',
             'target': url, 'portal': portal, 'query': query,
             'play': should_play,
             'desc': f"{'Play' if should_play else 'Search'} '{query}' on {portal.title()}"},
            {'action': ActionType.SCREENSHOT, 'agent': 'Perception Inspector',
             'desc': 'Verify result'},
            {'action': ActionType.SPEAK, 'agent': 'Studio Narrator',
             'target': f"{'Playing' if should_play else 'Searching'} {portal.title()} for {query}.",
             'desc': 'Announce action'},
        ]
    }


# Rule 3: open new tab [and go to <dest>]
@_rule(r'^(?:open|create)?\s*(?:a\s+)?new\s+tab(?:\s+(?:and\s+)?(?:go to|navigate to|open)\s+(.+))?$')
def _r_new_tab(m: re.Match) -> dict:
    dest = (m.group(1) or '').strip() or None
    return {
        'intent': IntentType.TAB_OPERATION,
        'confidence': 0.99,
        'steps': [
            {'action': ActionType.NEW_TAB, 'agent': 'Chrome Executor',
             'target': dest, 'desc': f"Open new tab{' → ' + dest if dest else ''}"},
            {'action': ActionType.SCREENSHOT, 'agent': 'Perception Inspector',
             'desc': 'Verify new tab'},
        ]
    }


# Rule 4: close tab / close chrome
@_rule(r'^close\s+(tab|chrome|browser)$')
def _r_close(m: re.Match) -> dict:
    what = m.group(1).lower()
    action = ActionType.CLOSE_TAB if what == 'tab' else ActionType.CLOSE
    return {
        'intent': IntentType.TAB_OPERATION,
        'confidence': 0.99,
        'steps': [
            {'action': action, 'agent': 'Chrome Executor',
             'target': what if action == ActionType.CLOSE else None,
             'desc': f'Close {what}'},
        ]
    }


# Rule 5: next / previous / switch tab
@_rule(r'^(?:next|switch)\s+tab$')
def _r_next_tab(_m: re.Match) -> dict:
    return {
        'intent': IntentType.TAB_OPERATION,
        'confidence': 0.99,
        'steps': [{'action': ActionType.NEXT_TAB, 'agent': 'Chrome Executor', 'desc': 'Next tab'}],
    }


@_rule(r'^(?:prev(?:ious)?)\s+tab$')
def _r_prev_tab(_m: re.Match) -> dict:
    return {
        'intent': IntentType.TAB_OPERATION,
        'confidence': 0.99,
        'steps': [{'action': ActionType.PREV_TAB, 'agent': 'Chrome Executor', 'desc': 'Previous tab'}],
    }


# Rule 6: reopen / restore tab
@_rule(r'^(?:reopen|restore)\s+tab$')
def _r_reopen(_m: re.Match) -> dict:
    return {
        'intent': IntentType.TAB_OPERATION,
        'confidence': 0.99,
        'steps': [{'action': ActionType.REOPEN_TAB, 'agent': 'Chrome Executor', 'desc': 'Reopen tab'}],
    }


# Rule 7: scroll down / up
@_rule(r'^scroll\s+(down|up)$')
def _r_scroll(m: re.Match) -> dict:
    direction = m.group(1).lower()
    action = ActionType.SCROLL_DOWN if direction == 'down' else ActionType.SCROLL_UP
    return {
        'intent': IntentType.WEB_SEARCH,
        'confidence': 0.95,
        'steps': [{'action': action, 'agent': 'Chrome Executor', 'desc': f'Scroll {direction}'}],
    }


# Rule 8: screenshot / take screenshot
@_rule(r'^(?:take\s+)?(?:a\s+)?screenshot$')
def _r_screenshot(_m: re.Match) -> dict:
    return {
        'intent': IntentType.UNKNOWN,
        'confidence': 0.99,
        'steps': [{'action': ActionType.SCREENSHOT, 'agent': 'Perception Inspector', 'desc': 'Take screenshot'}],
    }


# Rule 9: open desktop app ("open notepad", "open calculator", "open settings")
@_rule(r'^open\s+(notepad|calculator|settings|explorer|file explorer)$')
def _r_open_app(m: re.Match) -> dict:
    app = m.group(1).strip()
    return {
        'intent': IntentType.DESKTOP_APP,
        'confidence': 0.99,
        'steps': [
            {'action': ActionType.OPEN_APP, 'agent': 'Chrome Executor',
             'target': app, 'desc': f'Open {app}'},
            {'action': ActionType.SCREENSHOT, 'agent': 'Perception Inspector',
             'desc': f'Verify {app} opened'},
        ]
    }


# Rule 10: say / speak / announce
@_rule(r'^(?:say|speak|announce|tell me)\s+(.+)$')
def _r_speak(m: re.Match) -> dict:
    text = m.group(1).strip().strip("'\"")
    return {
        'intent': IntentType.VOICE,
        'confidence': 0.99,
        'steps': [{'action': ActionType.SPEAK, 'agent': 'Studio Narrator',
                   'target': text, 'desc': f'Speak: {text}'}],
    }


# Rule 11: go to / open <URL or site>
@_rule(r'^(?:go to|open|navigate to)\s+(https?://\S+|\w[\w.-]+\.\w{2,})$')
def _r_goto(m: re.Match) -> dict:
    dest = m.group(1).strip()
    if not dest.startswith('http'):
        dest = 'https://' + dest
    return {
        'intent': IntentType.WEB_SEARCH,
        'confidence': 0.90,
        'steps': [
            {'action': ActionType.BROWSE, 'agent': 'Chrome Executor',
             'target': dest, 'desc': f'Navigate to {dest}'},
            {'action': ActionType.SCREENSHOT, 'agent': 'Perception Inspector',
             'desc': 'Verify page loaded'},
        ]
    }


def local_parse(goal: str) -> Optional[Plan]:
    """
    Attempt to produce a validated Plan from a natural-language goal
    using only deterministic regex rules — no network, no AI.

    Returns None if no rule matched (caller should escalate to AI).
    """
    goal_stripped = goal.strip()
    for pattern, builder in _RULES:
        m = pattern.fullmatch(goal_stripped)
        if m:
            raw = builder(m)
            return validate_plan(raw)
    return None
