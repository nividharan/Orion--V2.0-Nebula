"""
🌌 Orion × Nebula Web Engine - Browser Lifecycle & CDP Perception Manager
Handles Playwright browser contexts, anti-bot stealth evasions, session state reuse,
failure trace recording, and pixel-perfect in-memory CDP screen capturing.
"""

import os
import sys
import time
import random
import logging
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page

from .config import BrowserConfig, DEFAULT_CONFIG
from .exceptions import WebEngineError, PageLoadTimeoutError

logger = logging.getLogger("Orion.WebEngine")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# Anti-detection stealth initialization script injected into every page/context
STEALTH_INIT_SCRIPT = """
(() => {
    // 1. Remove navigator.webdriver flag
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });

    // 2. Mock realistic Chrome runtime
    window.chrome = {
        app: { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' } },
        runtime: { OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' } },
        loadTimes: function() {},
        csi: function() {}
    };

    // 3. Mock languages and plugins
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
        configurable: true
    });

    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
        configurable: true
    });

    // 4. Mock notification permissions
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
    Manages Playwright browser instance, persistent session context, and CDP in-memory perception.
    Supports singleton access so Orion and Nebula can share the active page.
    """
    _active_instance: Optional['BrowserManager'] = None

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._active_page: Optional[Page] = None
        self._is_tracing: bool = False
        BrowserManager._active_instance = self

    @classmethod
    def get_active(cls) -> Optional['BrowserManager']:
        return cls._active_instance

    @property
    def page(self) -> Optional[Page]:
        return self._active_page

    @property
    def is_running(self) -> bool:
        return self._active_page is not None and not self._active_page.is_closed()

    def launch(self) -> Page:
        """Launches Google Chrome with anti-bot stealth and session restoration."""
        if self.is_running:
            return self._active_page

        logger.info("Starting Playwright Web Engine substrate...")
        self._playwright = sync_playwright().start()

        # Browser launch arguments with anti-detection flags
        args = [
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-extensions",
            f"--window-size={self.config.viewport_width},{self.config.viewport_height}",
        ]

        # Attempt to launch installed Chrome first, fallback to bundled Chromium
        launch_kwargs = {
            "headless": self.config.headless,
            "args": args,
        }
        try:
            logger.info("Connecting to installed Google Chrome (`channel='chrome'`)...")
            self._browser = self._playwright.chromium.launch(
                channel=self.config.browser_channel,
                **launch_kwargs
            )
        except Exception as e:
            logger.warning(f"Installed Chrome not launched via channel ({e}). Falling back to bundled Chromium...")
            self._browser = self._playwright.chromium.launch(**launch_kwargs)

        # Context configuration with session reuse
        context_kwargs = {
            "viewport": {"width": self.config.viewport_width, "height": self.config.viewport_height},
            "user_agent": self.config.user_agent,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone_id,
            "accept_downloads": True,
        }

        # Load saved session state if exists
        if os.path.exists(self.config.storage_state_path):
            try:
                context_kwargs["storage_state"] = self.config.storage_state_path
                logger.info(f"Loaded existing session state from '{self.config.storage_state_path}'.")
            except Exception as e:
                logger.warning(f"Could not load session state: {e}")

        self._context = self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(self.config.action_timeout_ms)
        self._context.set_default_navigation_timeout(self.config.navigation_timeout_ms)

        # Inject stealth evasions into all pages
        if self.config.stealth_enabled:
            self._context.add_init_script(STEALTH_INIT_SCRIPT)

        # Start Playwright tracing for failure diagnosis
        try:
            self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
            self._is_tracing = True
        except Exception:
            pass

        self._active_page = self._context.new_page()
        logger.info("Playwright page initialized and ready.")
        return self._active_page

    def save_session_state(self):
        """Persists current cookies and local storage to storage_state_path."""
        if self._context:
            try:
                self._context.storage_state(path=self.config.storage_state_path)
                logger.info(f"Saved session state to '{self.config.storage_state_path}'.")
            except Exception as e:
                logger.warning(f"Failed to save session state: {e}")

    def capture_cdp_screenshot(self, target_path: Optional[str] = None, full_page: bool = False) -> dict:
        """
        Captures in-memory screenshot via Chrome DevTools Protocol (CDP).
        Completely immune to Windows GDI BitBlt access-denied restrictions.
        """
        if not self.is_running:
            return {"status": "error", "message": "No active browser page open."}

        save_dest = target_path or os.path.join(self.config.cache_dir, "screen_live.png")
        os.makedirs(os.path.dirname(os.path.abspath(save_dest)), exist_ok=True)

        try:
            shot_bytes = self._active_page.screenshot(
                path=save_dest,
                full_page=full_page,
                timeout=5000
            )
            return {
                "status": "success",
                "success": True,
                "saved_path": save_dest,
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
        """Captures screenshot, DOM HTML dump, and Playwright trace on failure."""
        timestamp = int(time.time())
        artifacts = {}

        if self.is_running:
            # 1. Failure screenshot
            shot_path = os.path.join(self.config.screenshots_dir, f"fail_{action_name}_{timestamp}.png")
            try:
                self._active_page.screenshot(path=shot_path)
                artifacts["screenshot"] = shot_path
            except Exception:
                pass

            # 2. Failure DOM HTML dump
            html_path = os.path.join(self.config.screenshots_dir, f"fail_{action_name}_{timestamp}.html")
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(self._active_page.content())
                artifacts["html_dump"] = html_path
            except Exception:
                pass

            # 3. Playwright trace zip
            if self._is_tracing and self._context:
                trace_path = os.path.join(self.config.traces_dir, f"trace_{action_name}_{timestamp}.zip")
                try:
                    self._context.tracing.stop(path=trace_path)
                    artifacts["trace"] = trace_path
                    # Re-start tracing for future steps
                    self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
                except Exception:
                    pass

        return artifacts

    def human_delay(self, min_sec: float = 0.15, max_sec: float = 0.45):
        """Injects slight humanized jitter to prevent algorithmic rate-limiting."""
        if self.config.human_jitter:
            time.sleep(random.uniform(min_sec, max_sec))

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        """Navigates to URL with auto-waiting and CDP verification."""
        page = self.launch()
        t0 = time.time()
        try:
            page.goto(url, wait_until=wait_until, timeout=self.config.navigation_timeout_ms)
            self.human_delay()
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            shot_res = self.capture_cdp_screenshot()
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

    def close(self):
        """Gracefully closes page, context, browser, and playwright session."""
        try:
            if self._is_tracing and self._context:
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
            BrowserManager._active_instance = None
            logger.info("Playwright Web Engine shutdown complete.")

    def __enter__(self):
        self.launch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
