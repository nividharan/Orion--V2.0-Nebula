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
    "checkout"
}

MAX_STEPS_PER_TASK: int = 25


@dataclass
class BrowserConfig:
    # Execution & Environment
    headless: bool = field(
        default_factory=lambda: os.getenv("WEB_HEADLESS", "false").lower() in ("true", "1", "yes")
    )
    browser_channel: str = field(
        default_factory=lambda: os.getenv("WEB_BROWSER_CHANNEL", "chrome")
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
