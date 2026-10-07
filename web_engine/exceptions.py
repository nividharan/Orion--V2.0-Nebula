"""
🌌 Orion × Nebula Web Engine - Exceptions Hierarchy
Distinct, informative error classes including structured failure states for future LLM recovery agents.
"""

from typing import List, Dict, Any, Optional

class WebEngineError(Exception):
    """Base exception for all web automation engine errors."""
    pass

class SelectorNotFoundError(WebEngineError):
    """
    Raised when an element cannot be found after exhausting all fallback chains.
    Carries structured page state so future AI recovery agents can inspect the context.
    """
    def __init__(
        self,
        target_name: str,
        tried_selectors: List[Dict[str, Any]],
        timeout_ms: int,
        page_state: Optional[Dict[str, Any]] = None
    ):
        self.target_name = target_name
        self.tried_selectors = tried_selectors
        self.timeout_ms = timeout_ms
        self.page_state = page_state or {}
        url_info = f" at {self.page_state.get('url', 'unknown')}" if self.page_state else ""
        msg = f"Failed to locate '{target_name}'{url_info} after {timeout_ms}ms. Exhausted fallbacks: {tried_selectors}"
        super().__init__(msg)

class ActionNotAllowedError(WebEngineError):
    """Raised when an unapproved or prompt-injected action is requested."""
    pass

class SessionExpiredError(WebEngineError):
    """Raised when an authenticated session is detected as logged out or invalid."""
    pass

class BotDetectionTriggeredError(WebEngineError):
    """Raised when a Cloudflare challenge, CAPTCHA, or rate limit 429/403 is encountered."""
    def __init__(self, message: str, retry_after_sec: Optional[float] = None):
        self.retry_after_sec = retry_after_sec
        super().__init__(message)

class PageLoadTimeoutError(WebEngineError):
    """Raised when a page fails to reach the required load state within the timeout window."""
    pass
