"""
🌌 Orion × Nebula Web Engine - Configuration Module
Centralized, typed, and environment-driven configuration for production web automation.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

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
    user_agent: Optional[str] = os.getenv(
        "WEB_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    locale: str = os.getenv("WEB_LOCALE", "en-US")
    timezone_id: str = os.getenv("WEB_TIMEZONE", "America/New_York")

    # Timeouts (in milliseconds)
    navigation_timeout_ms: int = int(os.getenv("WEB_NAV_TIMEOUT_MS", "35000"))
    action_timeout_ms: int = int(os.getenv("WEB_ACTION_TIMEOUT_MS", "12000"))
    selector_timeout_ms: int = int(os.getenv("WEB_SELECTOR_TIMEOUT_MS", "8000"))

    # Resilience & Evasions
    max_retries: int = int(os.getenv("WEB_MAX_RETRIES", "3"))
    retry_backoff_base: float = float(os.getenv("WEB_RETRY_BACKOFF", "1.5"))
    stealth_enabled: bool = field(
        default_factory=lambda: os.getenv("WEB_STEALTH_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    human_jitter: bool = field(
        default_factory=lambda: os.getenv("WEB_HUMAN_JITTER", "true").lower() in ("true", "1", "yes")
    )

    # Storage Paths
    cache_dir: str = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache"))
    storage_state_path: str = field(
        default_factory=lambda: os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")),
            "storage_state.json"
        )
    )
    traces_dir: str = field(
        default_factory=lambda: os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")),
            "traces"
        )
    )
    screenshots_dir: str = field(
        default_factory=lambda: os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")),
            "screenshots"
        )
    )
    output_dir: str = field(
        default_factory=lambda: os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")),
            "output"
        )
    )

    def __post_init__(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.traces_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

DEFAULT_CONFIG = BrowserConfig()
