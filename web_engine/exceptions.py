"""
🌌 Orion × Nebula Web Engine - Exceptions Hierarchy
Distinct, informative error classes for robust automation failure diagnosis.
"""

class WebEngineError(Exception):
    """Base exception for all web automation engine errors."""
    pass

class SelectorNotFoundError(WebEngineError):
    """Raised when an element cannot be found after exhausting all fallback chains."""
    def __init__(self, target_name: str, tried_selectors: list, timeout_ms: int):
        self.target_name = target_name
        self.tried_selectors = tried_selectors
        self.timeout_ms = timeout_ms
        msg = f"Failed to locate '{target_name}' after {timeout_ms}ms. Exhausted fallbacks: {tried_selectors}"
        super().__init__(msg)

class SessionExpiredError(WebEngineError):
    """Raised when an authenticated session is detected as logged out or invalid."""
    pass

class BotDetectionTriggeredError(WebEngineError):
    """Raised when a Cloudflare challenge, CAPTCHA, or access denied page is encountered."""
    pass

class PageLoadTimeoutError(WebEngineError):
    """Raised when a page fails to reach the required load state within the timeout window."""
    pass

class CheckpointCorruptionError(WebEngineError):
    """Raised when an execution checkpoint file cannot be parsed or resumed."""
    pass
