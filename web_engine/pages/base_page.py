"""
🌌 Orion × Nebula Web Engine - Base Page Object Model (POM)
Features:
- Fast short-probe fallback resolution (300-600ms per candidate, not 10s!)
- Safe cookie rejection scoped to dialog containers
- Idempotent-only retries (never retry submits/payments)
- aria_snapshot() for compact semantic page descriptions (Perception Inspector)
- Structured action logging and per-site memory (.cache/site_memory.json)
- Structured SelectorNotFoundError with page_state for AI recovery
"""

import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

from ..browser_manager import BrowserManager
from ..exceptions import SelectorNotFoundError, ActionNotAllowedError, WebEngineError
from ..locators.base_locators import (
    COOKIE_CONSENT_LOCATORS,
    CMP_MANAGE_PREFERENCES_LOCATORS,
    CMP_CONFIRM_OR_REJECT_LOCATORS,
    MODAL_CLOSE_LOCATORS
)
from ..config import SENSITIVE_ACTIONS, DOMAIN_ALLOW_LIST, is_action_or_target_sensitive


logger = logging.getLogger("Orion.BasePage")


class BasePage:
    """Base Page Object Model with short-probe resolution, site memory, and safe actions."""

    def __init__(self, browser_mgr: BrowserManager):
        self.mgr = browser_mgr
        self.action_logs: List[Dict[str, Any]] = []
        self._site_memory: Dict[str, Any] = self._load_site_memory()

    @property
    def page(self) -> Page:
        p = self.mgr.page
        if not p or p.is_closed():
            return self.mgr.launch()
        return p

    def _load_site_memory(self) -> Dict[str, Any]:
        """Loads learned selector memory from disk if present."""
        mem_file = self.mgr.config.site_memory_path
        if mem_file.exists():
            try:
                with open(mem_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_site_memory(self, domain: str, target_name: str, working_selector: Dict[str, Any]):
        """Saves known working selector to disk for instant future matching."""
        if domain not in self._site_memory:
            self._site_memory[domain] = {}
        self._site_memory[domain][target_name] = working_selector
        try:
            with open(self.mgr.config.site_memory_path, "w", encoding="utf-8") as f:
                json.dump(self._site_memory, f, indent=2)
        except Exception:
            pass

    def get_domain(self) -> str:
        try:
            from urllib.parse import urlparse
            return urlparse(self.page.url).netloc
        except Exception:
            return "unknown"

    def resolve_locator(self, selector_def: Dict[str, Any], context: Optional[Any] = None) -> Locator:
        """Translates a selector definition into a Playwright Locator."""
        root = context or self.page

        if "role" in selector_def:
            role = selector_def["role"]
            name = selector_def.get("name")
            exact = selector_def.get("exact", False)
            if name:
                return root.get_by_role(role, name=name, exact=exact)
            return root.get_by_role(role)

        if "text" in selector_def:
            return root.get_by_text(selector_def["text"], exact=selector_def.get("exact", False))

        if "testid" in selector_def:
            return root.get_by_test_id(selector_def["testid"])

        if "label" in selector_def:
            return root.get_by_label(selector_def["label"])

        if "placeholder" in selector_def:
            return root.get_by_placeholder(selector_def["placeholder"])

        if "css" in selector_def:
            return root.locator(selector_def["css"])

        if "xpath" in selector_def:
            return root.locator(selector_def["xpath"])

        raise ValueError(f"Invalid selector definition: {selector_def}")

    def find_first_visible(
        self,
        fallback_chain: List[Dict[str, Any]],
        target_name: str = "element",
        full_timeout_ms: int = 8000,
        context: Optional[Any] = None
    ) -> Locator:
        """
        Fast Short-Probe Resolver:
        Probes each fallback with a 400-600ms probe timeout rather than wasting 10s per candidate.
        Checks site memory first. Spends the full timeout only on the matched candidate.
        """
        t0 = time.time()
        domain = self.get_domain()
        probe_timeout = self.mgr.config.selector_probe_timeout_ms
        tried = []

        # 1. Check site memory first
        mem_sel = self._site_memory.get(domain, {}).get(target_name)
        if mem_sel:
            try:
                loc = self.resolve_locator(mem_sel, context=context)
                loc.first.wait_for(state="visible", timeout=probe_timeout)
                self._log_action("resolve_locator_memory", target_name, mem_sel, time.time() - t0, "success")
                return loc.first
            except Exception:
                pass

        # 2. Short-probe through fallback chain using wait_for (properly waits for SPA renders)
        matched_loc: Optional[Locator] = None
        matched_sel: Optional[Dict[str, Any]] = None

        for sel in fallback_chain:
            tried.append(sel)
            try:
                candidate = self.resolve_locator(sel, context=context)
                candidate.first.wait_for(state="visible", timeout=probe_timeout)
                matched_loc = candidate.first
                matched_sel = sel
                break
            except (PlaywrightTimeoutError, Exception):
                continue

        # 3. If matched, wait for full actionability and remember working selector
        if matched_loc and matched_sel:
            try:
                matched_loc.wait_for(state="visible", timeout=full_timeout_ms)
                self._save_site_memory(domain, target_name, matched_sel)
                self._log_action("resolve_locator", target_name, matched_sel, time.time() - t0, "success")
                return matched_loc
            except Exception:
                pass

        # 4. If none matched, dismiss popups and re-probe first two
        self.dismiss_cookie_banners()
        for sel in fallback_chain[:2]:
            try:
                candidate = self.resolve_locator(sel, context=context)
                candidate.first.wait_for(state="visible", timeout=probe_timeout)
                candidate.first.wait_for(state="visible", timeout=1200)
                self._save_site_memory(domain, target_name, sel)
                return candidate.first
            except (PlaywrightTimeoutError, Exception):
                continue

        # 5. Raise structured SelectorNotFoundError with page state for future AI recovery
        page_state = {
            "url": self.page.url,
            "title": self.page.title(),
            "aria_summary": self.aria_snapshot()
        }
        self._log_action("resolve_locator", target_name, tried, time.time() - t0, "failed")
        raise SelectorNotFoundError(target_name, tried, full_timeout_ms, page_state=page_state)

    def click_with_fallback(
        self,
        fallback_chain: List[Dict[str, Any]],
        target_name: str = "button",
        timeout_ms: int = 6000
    ):
        """Finds visible element from fallback chain and clicks with auto-waiting and safety guards."""
        t0 = time.time()
        domain = self.get_domain()
        if DOMAIN_ALLOW_LIST is not None and domain not in DOMAIN_ALLOW_LIST:
            raise ActionNotAllowedError(f"Domain '{domain}' is not in DOMAIN_ALLOW_LIST.")

        self.dismiss_cookie_banners()
        loc = self.find_first_visible(fallback_chain, target_name, timeout_ms)

        # Inspect target element accessible text to guard against sensitive actions
        # (e.g. clicking 'Place order', 'Delete account', 'Submit payment')
        accessible_text = ""
        try:
            accessible_text = (
                loc.get_attribute("aria-label") or
                loc.inner_text() or
                loc.get_attribute("value") or
                loc.get_attribute("title") or
                ""
            ).strip()
        except Exception:
            pass

        if is_action_or_target_sensitive("click", target_name, accessible_text):
            raise ActionNotAllowedError(
                f"Action 'click' on target '{target_name}' (accessible name: '{accessible_text}') "
                f"is sensitive and requires explicit human confirmation."
            )

        loc.scroll_into_view_if_needed()
        self.mgr.human_delay(0.1, 0.2)
        loc.click(timeout=timeout_ms)
        self.mgr.human_delay(0.1, 0.25)
        self._log_action("click", target_name, {"accessible_name": accessible_text}, time.time() - t0, "success")

    def fill_with_fallback(
        self,
        fallback_chain: List[Dict[str, Any]],
        value: str,
        target_name: str = "input_field",
        timeout_ms: int = 6000,
        press_enter: bool = False
    ):
        """Finds visible input element, clears it, and types value with safety guards."""
        t0 = time.time()
        domain = self.get_domain()
        if DOMAIN_ALLOW_LIST is not None and domain not in DOMAIN_ALLOW_LIST:
            raise ActionNotAllowedError(f"Domain '{domain}' is not in DOMAIN_ALLOW_LIST.")

        self.dismiss_cookie_banners()
        loc = self.find_first_visible(fallback_chain, target_name, timeout_ms)

        accessible_text = ""
        try:
            accessible_text = (
                loc.get_attribute("aria-label") or
                loc.get_attribute("placeholder") or
                loc.get_attribute("name") or
                ""
            ).strip()
        except Exception:
            pass

        if is_action_or_target_sensitive("fill", target_name, accessible_text):
            raise ActionNotAllowedError(
                f"Action 'fill' on target '{target_name}' (accessible name: '{accessible_text}') "
                f"is sensitive and requires explicit human confirmation."
            )

        loc.scroll_into_view_if_needed()
        loc.click()
        loc.fill("")
        self.mgr.human_delay(0.05, 0.15)
        loc.type(value, delay=25)
        if press_enter:
            self.mgr.human_delay(0.1, 0.2)
            loc.press("Enter")
        self.mgr.human_delay(0.1, 0.2)
        self._log_action("fill", target_name, {"length": len(value), "press_enter": press_enter, "accessible_name": accessible_text}, time.time() - t0, "success")

    def dismiss_cookie_banners(self):
        """
        Safely dismisses cookie consent dialogs:
        - Step 1: Checks direct 'Reject all' / 'Necessary only' buttons.
        - Step 2: Multi-step CMP flow (OneTrust, Cookiebot, Didomi): If direct reject is hidden
                  behind 'Manage preferences' / 'Cookie Settings', clicks it, then clicks
                  'Reject all' / 'Confirm my choices'.
        - Step 3: Generic modal dismissers.
        """
        # 1. Direct rejection locators
        for sel in COOKIE_CONSENT_LOCATORS:
            try:
                loc = self.resolve_locator(sel)
                loc.first.wait_for(state="visible", timeout=180)
                loc.first.click(timeout=600)
                logger.info(f"Safely handled cookie dialog via direct {sel.get('name', sel.get('css', 'selector'))}.")
                self.mgr.human_delay(0.1, 0.2)
                return
            except Exception:
                continue

        # 2. Multi-step CMP flow (Manage preferences -> Reject all)
        for pref_sel in CMP_MANAGE_PREFERENCES_LOCATORS:
            try:
                loc = self.resolve_locator(pref_sel)
                loc.first.wait_for(state="visible", timeout=180)
                loc.first.click(timeout=600)
                logger.info(f"Opened CMP preference panel via {pref_sel.get('name', pref_sel.get('css', 'selector'))}.")
                self.mgr.human_delay(0.1, 0.2)

                for conf_sel in CMP_CONFIRM_OR_REJECT_LOCATORS:
                    try:
                        conf_loc = self.resolve_locator(conf_sel)
                        conf_loc.first.wait_for(state="visible", timeout=400)
                        conf_loc.first.click(timeout=600)
                        logger.info(f"Rejected CMP cookies inside preferences via {conf_sel.get('name', conf_sel.get('css', 'selector'))}.")
                        self.mgr.human_delay(0.1, 0.2)
                        return
                    except Exception:
                        continue
                return
            except Exception:
                continue

        # 3. Dismiss blocking generic popups
        for sel in MODAL_CLOSE_LOCATORS:
            try:
                loc = self.resolve_locator(sel)
                loc.first.wait_for(state="visible", timeout=150)
                loc.first.click(timeout=500)
                break
            except Exception:
                continue


    def scroll_until_no_new_content(
        self,
        item_selector: Optional[Dict[str, Any]] = None,
        max_iterations: int = 12,
        pause_sec: float = 0.6
    ) -> int:
        """
        Infinite scroll helper with safeguard max-iteration limits.
        Terminates safely when scroll height ceases to change or item count stabilizes.
        """
        last_height = self.page.evaluate("() => document.body.scrollHeight")
        last_count = 0
        iterations = 0

        while iterations < max_iterations:
            self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(pause_sec)

            new_height = self.page.evaluate("() => document.body.scrollHeight")
            current_count = 0
            if item_selector:
                try:
                    loc = self.resolve_locator(item_selector)
                    current_count = loc.count()
                except Exception:
                    pass

            iterations += 1

            if new_height == last_height:
                if item_selector and current_count > last_count:
                    last_count = current_count
                    last_height = new_height
                    continue
                break

            last_height = new_height
            last_count = current_count

        return current_count if item_selector else iterations

    def aria_snapshot(self) -> str:
        """
        Compact accessibility snapshot of the page.
        Provides a cheap, token-efficient semantic tree for Nebula's Perception Inspector.
        """
        try:
            # Query visible landmarks, headings, buttons, and inputs
            js_script = """
            (() => {
                const elements = document.querySelectorAll('h1, h2, h3, button, a[href], input, [role="button"], [role="searchbox"]');
                const tree = [];
                for (const el of Array.from(elements).slice(0, 30)) {
                    if (el.offsetParent !== null) {
                        const tag = el.tagName.toLowerCase();
                        const text = (el.innerText || el.placeholder || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
                        if (text) {
                            tree.push(`[${tag}] ${text.slice(0, 50)}`);
                        }
                    }
                }
                return tree.join('\\n');
            })()
            """
            return self.page.evaluate(js_script)
        except Exception:
            return ""

    def retry_idempotent(
        self,
        action_name: str,
        func: Callable,
        max_retries: int = 3,
        backoff: float = 1.5,
        target_text: Optional[str] = None
    ):
        """
        Executes idempotent operations with exponential backoff.
        Guarantees that sensitive actions (by action name OR target accessible text) are NEVER retried.
        """
        if is_action_or_target_sensitive(action_name, target_text):
            raise ActionNotAllowedError(
                f"Auto-retry blocked on sensitive non-idempotent action/target: '{action_name}' ('{target_text}')"
            )

        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                return func()
            except (PlaywrightTimeoutError, SelectorNotFoundError) as ex:
                last_err = ex
                if attempt < max_retries:
                    sleep_time = backoff ** attempt
                    logger.warning(f"Retry {attempt}/{max_retries} for idempotent '{action_name}' after {sleep_time:.1f}s: {ex}")
                    time.sleep(sleep_time)
            except Exception as non_retryable:
                raise non_retryable

        raise last_err


    def _log_action(self, action: str, target: Any, details: Dict[str, Any], duration: float, status: str):
        """Records structured JSON action entry for observability."""
        self.action_logs.append({
            "timestamp": time.time(),
            "action": action,
            "target": str(target),
            "duration_ms": round(duration * 1000, 1),
            "status": status,
            "details": details
        })
