"""
🌌 Orion × Nebula Web Engine - Configuration Module
Centralized, typed, and environment-driven configuration using pathlib.Path.
Features persistent profile support, action allow-lists, and minimal stealth tuning.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Set, Optional

# Root directory of the repository (dynamic, not hardcoded)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Security: Allowed web actions for LLM / Agent invocation
ALLOWED_ACTIONS: Set[str] = {
    "navigate",
    "search",
    "click",
    "fill",
    "scroll",
    "extract",
    "screenshot",
    "aria_snapshot"
}

# Security: Sensitive actions requiring confirmation
SENSITIVE_ACTIONS: Set[str] = {
    "submit",
    "pay",
    "delete",
    "purchase",
    "checkout",
    "send",
    "confirm",
    "remove account",
    "place order",
    "buy"
}

# Sensitive patterns per Phase 1 spec: (pay, place order, buy, checkout, delete, remove account, submit, send, confirm)
SENSITIVE_PATTERNS: Set[str] = {
    "pay",
    "place order",
    "buy",
    "checkout",
    "delete",
    "remove account",
    "submit",
    "send",
    "confirm"
}

# Security: Sensitive target keywords (accessible name, button text, aria-label, etc.)
SENSITIVE_TARGET_KEYWORDS: Set[str] = {
    "order",
    "place order",
    "pay",
    "payment",
    "buy",
    "purchase",
    "checkout",
    "delete",
    "destroy",
    "remove account",
    "transfer",
    "subscribe",
    "submit payment",
    "send",
    "confirm"
}

# Security: Domain allow-list (None means all allowed, or set of allowed hostnames)
DOMAIN_ALLOW_LIST: Optional[Set[str]] = None

MAX_STEPS_PER_TASK: int = 25

_GLOBAL_KILL_SWITCH_ACTIVE: bool = False

def set_global_kill_switch(active: bool = True):
    global _GLOBAL_KILL_SWITCH_ACTIVE
    _GLOBAL_KILL_SWITCH_ACTIVE = active

def is_global_kill_switch_active() -> bool:
    return _GLOBAL_KILL_SWITCH_ACTIVE


def is_action_or_target_sensitive(
    action_name: str,
    target_text: Optional[str] = None,
    accessible_name: Optional[str] = None,
    form_action: Optional[str] = None,
    href: Optional[str] = None
) -> bool:
    """
    Evaluates whether an action or the element being interacted with is sensitive.
    Guards action names ('pay', 'checkout'), target element labels ('Place order', 'Delete account'),
    as well as form actions and href attributes.
    """
    act_lower = action_name.lower().strip()
    if act_lower in SENSITIVE_ACTIONS or any(p in act_lower for p in SENSITIVE_PATTERNS):
        return True

    text_to_check = f"{target_text or ''} {accessible_name or ''} {form_action or ''} {href or ''}".lower()
    for kw in SENSITIVE_PATTERNS | SENSITIVE_TARGET_KEYWORDS:
        if kw in text_to_check:
            return True

    return False



@dataclass
class BrowserConfig:
    # Execution & Environment
    headless: bool = field(
        default_factory=lambda: os.getenv("WEB_HEADLESS", "false").lower() in ("true", "1", "yes")
    )
    browser_channel: Optional[str] = field(
        default_factory=lambda: os.getenv("WEB_BROWSER_CHANNEL", None)
    )
    viewport_width: int = int(os.getenv("WEB_VIEWPORT_WIDTH", "1920"))
    viewport_height: int = int(os.getenv("WEB_VIEWPORT_HEIGHT", "1080"))
    locale: str = os.getenv("WEB_LOCALE", "en-US")
    timezone_id: str = os.getenv("WEB_TIMEZONE", "America/New_York")

    # Timeouts (in milliseconds)
    navigation_timeout_ms: int = int(os.getenv("WEB_NAV_TIMEOUT_MS", "30000"))
    action_timeout_ms: int = int(os.getenv("WEB_ACTION_TIMEOUT_MS", "10000"))
    selector_probe_timeout_ms: int = int(os.getenv("WEB_PROBE_TIMEOUT_MS", "600"))

    # Resilience & Evasions
    max_retries: int = int(os.getenv("WEB_MAX_RETRIES", "3"))
    retry_backoff_base: float = float(os.getenv("WEB_RETRY_BACKOFF", "1.5"))
    stealth_enabled: bool = field(
        default_factory=lambda: os.getenv("WEB_STEALTH_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    human_jitter: bool = field(
        default_factory=lambda: os.getenv("WEB_HUMAN_JITTER", "true").lower() in ("true", "1", "yes")
    )

    # Persistent Context Profile vs storage_state
    use_persistent_profile: bool = field(
        default_factory=lambda: os.getenv("WEB_PERSISTENT_PROFILE", "false").lower() in ("true", "1", "yes")
    )

    # Paths (all pathlib.Path based)
    base_dir: Path = REPO_ROOT
    cache_dir: Path = field(default_factory=lambda: REPO_ROOT / ".cache")
    profile_dir: Path = field(default_factory=lambda: REPO_ROOT / ".cache" / "browser_profile")
    storage_state_path: Path = field(default_factory=lambda: REPO_ROOT / ".cache" / "storage_state.json")
    traces_dir: Path = field(default_factory=lambda: REPO_ROOT / ".cache" / "traces")
    screenshots_dir: Path = field(default_factory=lambda: REPO_ROOT / ".cache" / "screenshots")
    output_dir: Path = field(default_factory=lambda: REPO_ROOT / ".cache" / "output")
    site_memory_path: Path = field(default_factory=lambda: REPO_ROOT / ".cache" / "site_memory.json")

    def __post_init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.use_persistent_profile:
            self.profile_dir.mkdir(parents=True, exist_ok=True)


DEFAULT_CONFIG = BrowserConfig()
