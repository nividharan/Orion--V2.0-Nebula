"""
🌌 Orion × Nebula Web Engine - Browser Lifecycle & CDP Perception Manager
Production Playwright manager featuring:
- Thread-safe execution (immune to active asyncio loops in agent frameworks)
- Correct tracing lifecycle (start at launch, discard on success, save on failure)
- Minimal, clean stealth (no over-masking)
- Response listener for 429/403 Retry-After backoff
- Persistent browser profile support (user_data_dir) alongside storage_state.json
- Active page validation with `page.bring_to_front()` before CDP capture
"""

import os
import sys
import time
import random
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page, Response

from .config import BrowserConfig, DEFAULT_CONFIG
from .exceptions import WebEngineError, PageLoadTimeoutError, BotDetectionTriggeredError

logger = logging.getLogger("Orion.WebEngine")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# Minimal stealth script: Report false for navigator.webdriver (matching real headed Chrome)
MINIMAL_STEALTH_SCRIPT = """
(() => {
    // 1. Report navigator.webdriver as false (real headed Chrome reports false, not undefined)
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
        configurable: true
    });

    // 2. Normal permissions query behavior for notifications
    const originalQuery = window.navigator.permissions ? window.navigator.permissions.query : null;
    if (originalQuery) {
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    }
})();
"""


class BrowserManager:
    """
    Manages Playwright browser lifecycle with thread-safety, resilient tracing,
    CDP in-memory capture, and rate-limit listeners.
    """
    _active_instance: Optional['BrowserManager'] = None
    _lock = threading.Lock()

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._active_page: Optional[Page] = None
        self._tracing_active: bool = False
        self._last_retry_after: Optional[float] = None
        with BrowserManager._lock:
            BrowserManager._active_instance = self

    @classmethod
    def get_active(cls) -> Optional['BrowserManager']:
        with cls._lock:
            inst = cls._active_instance
            if inst and inst.is_running:
                return inst
            return None

    @property
    def page(self) -> Optional[Page]:
        if self._active_page and not self._active_page.is_closed():
            return self._active_page
        return None

    @property
    def is_running(self) -> bool:
        return self._active_page is not None and not self._active_page.is_closed()

    def _on_response(self, response: Response):
        """Monitors network responses for 429/403 rate-limiting and Retry-After headers."""
        if response.status in (429, 403):
            retry_header = response.headers.get("retry-after")
            wait_time = 5.0
            if retry_header:
                try:
                    wait_time = float(retry_header)
                except ValueError:
                    pass
            self._last_retry_after = wait_time
            logger.warning(f"Rate limit / Bot challenge received (HTTP {response.status}). Retry-After: {wait_time}s")

    def launch(self) -> Page:
        """Launches Google Chrome with minimal stealth, correct tracing, and rate listeners."""
        if self.is_running:
            return self._active_page

        logger.info("Initializing Playwright Web Engine substrate...")
        self._playwright = sync_playwright().start()

        args = [
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-extensions",
            f"--window-size={self.config.viewport_width},{self.config.viewport_height}",
        ]

        # Common context options
        context_options = {
            "viewport": {"width": self.config.viewport_width, "height": self.config.viewport_height},
            "locale": self.config.locale,
            "timezone_id": self.config.timezone_id,
            "accept_downloads": True,
        }

        # 1. Persistent Context Profile vs Standard Context
        if self.config.use_persistent_profile:
            logger.info(f"Using persistent automation profile at '{self.config.profile_dir}'...")
            try:
                self._context = self._playwright.chromium.launch_persistent_context(
                    str(self.config.profile_dir),
                    channel=self.config.browser_channel,
                    headless=self.config.headless,
                    args=args,
                    **context_options
                )
            except Exception as e:
                logger.warning(f"Persistent context launch with channel failed ({e}). Retrying with bundled Chromium...")
                self._context = self._playwright.chromium.launch_persistent_context(
                    str(self.config.profile_dir),
                    headless=self.config.headless,
                    args=args,
                    **context_options
                )
            self._browser = None  # In persistent context, context manages browser lifecycle
        else:
            launch_kwargs = {"headless": self.config.headless, "args": args}
            try:
                self._browser = self._playwright.chromium.launch(
                    channel=self.config.browser_channel,
                    **launch_kwargs
                )
            except Exception as e:
                logger.warning(f"Chrome launch with channel failed ({e}). Retrying with bundled Chromium...")
                self._browser = self._playwright.chromium.launch(**launch_kwargs)

            # Check if saved storage state exists
            if self.config.storage_state_path.exists():
                try:
                    context_options["storage_state"] = str(self.config.storage_state_path)
                    logger.info(f"Loaded storage state from '{self.config.storage_state_path}'.")
                except Exception as ex:
                    logger.warning(f"Could not load storage state: {ex}")

            self._context = self._browser.new_context(**context_options)

        self._context.set_default_timeout(self.config.action_timeout_ms)
        self._context.set_default_navigation_timeout(self.config.navigation_timeout_ms)

        # Apply minimal stealth script (context level applies to all tabs & iframes)
        if self.config.stealth_enabled:
            self._context.add_init_script(MINIMAL_STEALTH_SCRIPT)

        # 2. Correct Tracing Pattern: Start tracing at context creation
        try:
            self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
            self._tracing_active = True
        except Exception:
            self._tracing_active = False

        # Get or create active page
        pages = self._context.pages
        self._active_page = pages[0] if pages else self._context.new_page()

        # Attach rate-limiting response listener
        self._active_page.on("response", self._on_response)

        logger.info("Playwright page initialized and ready.")
        return self._active_page

    def save_session_state(self):
        """Persists session state if running non-persistent context."""
        if not self.config.use_persistent_profile and self._context:
            try:
                self._context.storage_state(path=str(self.config.storage_state_path))
                logger.info(f"Saved session state to '{self.config.storage_state_path}'.")
            except Exception as e:
                logger.warning(f"Failed to save session state: {e}")

    def capture_cdp_screenshot(self, target_path: Optional[str] = None, full_page: bool = False) -> dict:
        """
        Captures in-memory screenshot via Chrome DevTools Protocol (CDP).
        Ensures page is brought to front before capture to prevent blank renders.
        """
        if not self.is_running:
            return {"status": "error", "message": "No active browser page open."}

        save_dest = Path(target_path) if target_path else self.config.cache_dir / "screen_live.png"
        save_dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Bring tab to front so background rendering doesn't stall
            try:
                self._active_page.bring_to_front()
            except Exception:
                pass

            shot_bytes = self._active_page.screenshot(
                path=str(save_dest),
                full_page=full_page,
                timeout=5000
            )
            return {
                "status": "success",
                "success": True,
                "saved_path": str(save_dest),
                "bytes_len": len(shot_bytes),
                "method": "playwright_cdp",
                "timestamp": time.time(),
                "url": self._active_page.url,
                "title": self._active_page.title()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"CDP screenshot capture failed: {e}"
            }

    def capture_failure_artifacts(self, action_name: str) -> dict:
        """
        On failure: stops tracing and saves trace.zip, captures HTML dump, and failure screenshot.
        """
        timestamp = int(time.time())
        artifacts = {}

        if self.is_running:
            # 1. Failure screenshot
            shot_path = self.config.screenshots_dir / f"fail_{action_name}_{timestamp}.png"
            try:
                self._active_page.screenshot(path=str(shot_path))
                artifacts["screenshot"] = str(shot_path)
            except Exception:
                pass

            # 2. Failure DOM HTML dump
            html_path = self.config.screenshots_dir / f"fail_{action_name}_{timestamp}.html"
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(self._active_page.content())
                artifacts["html_dump"] = str(html_path)
            except Exception:
                pass

            # 3. Save Playwright trace zip on failure
            if self._tracing_active and self._context:
                trace_path = self.config.traces_dir / f"trace_{action_name}_{timestamp}.zip"
                try:
                    self._context.tracing.stop(path=str(trace_path))
                    artifacts["trace"] = str(trace_path)
                    # Restart tracing for subsequent operations
                    self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
                except Exception:
                    pass

        return artifacts

    def finish_task_success(self):
        """
        On successful completion of a task: discards current trace buffer without disk penalty,
        and starts a fresh trace chunk for future tasks.
        """
        if self._tracing_active and self._context:
            try:
                # Stop tracing without path -> discards memory buffer
                self._context.tracing.stop()
                # Restart for next task
                self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
            except Exception:
                pass

    def human_delay(self, min_sec: float = 0.1, max_sec: float = 0.3):
        """Subtle humanized jitter without excessive sleep penalties."""
        if self.config.human_jitter:
            time.sleep(random.uniform(min_sec, max_sec))

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        """
        Navigates to URL with auto-waiting and rate-limit backoff handling.
        Guards against networkidle infinite hangs by navigating via domcontentloaded
        and capping networkidle wait with a non-fatal 3000ms safety timeout.
        """
        page = self.launch()
        t0 = time.time()

        # Handle 429/403 backoff if triggered earlier
        if self._last_retry_after:
            logger.info(f"Backing off for {self._last_retry_after}s due to earlier rate limit...")
            time.sleep(self._last_retry_after)
            self._last_retry_after = None

        try:
            # Prevent networkidle hang: navigate using domcontentloaded or load
            effective_wait = "domcontentloaded" if wait_until == "networkidle" else wait_until
            page.goto(url, wait_until=effective_wait, timeout=self.config.navigation_timeout_ms)

            # If caller explicitly requested networkidle, wait with a strict non-fatal timeout
            if wait_until == "networkidle":
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    logger.debug("networkidle wait reached 3000ms safety cap; continuing with loaded DOM.")

            self.human_delay()
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            shot_res = self.capture_cdp_screenshot()
            self.finish_task_success()
            return {
                "status": "success",
                "success": True,
                "url": page.url,
                "title": page.title(),
                "elapsed_ms": elapsed_ms,
                "screenshot": shot_res.get("saved_path")
            }
        except Exception as e:
            artifacts = self.capture_failure_artifacts("navigate")
            raise PageLoadTimeoutError(f"Failed to navigate to '{url}': {e}. Artifacts: {artifacts}") from e

    def verify_or_refresh_session(
        self,
        validity_probe: Callable[[Page], bool],
        relogin_callback: Optional[Callable[[Page], None]] = None
    ) -> bool:
        """
        Validates session state against an expired-session probe.
        If expired and relogin_callback is provided, executes re-login flow and updates session.
        """
        page = self.launch()
        is_valid = validity_probe(page)
        if not is_valid and relogin_callback:
            logger.warning("Session probe reported expired state. Triggering automated re-login flow...")
            relogin_callback(page)
            self.save_session_state()
            return validity_probe(page)
        return is_valid

    @staticmethod
    def run_isolated(func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Executes a Playwright operation inside a dedicated worker thread.
        Solves the sync vs async mismatch for AutoGen / Orion: prevents
        'Playwright Sync API inside asyncio loop' errors when called from async agents.
        """
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            return future.result()


    def close(self):
        """Gracefully closes tracing, context, browser, and playwright instance."""
        try:
            if self._tracing_active and self._context:
                try:
                    self._context.tracing.stop()
                except Exception:
                    pass
            self.save_session_state()
            if self._active_page and not self._active_page.is_closed():
                self._active_page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self._active_page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._tracing_active = False
            with BrowserManager._lock:
                BrowserManager._active_instance = None
            logger.info("Playwright Web Engine shutdown complete.")

    def __enter__(self):
        self.launch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.capture_failure_artifacts("context_exit")
        self.close()
