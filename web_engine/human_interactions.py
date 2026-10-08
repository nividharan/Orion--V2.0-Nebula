"""
Human-Grade Browser Interactions for Nebula Web Engine.
Implements Gaussian typing intervals, smooth momentum scrolling, and direct DOM date injection.
"""

import asyncio
import inspect
import logging
import random
from typing import Optional, Any

logger = logging.getLogger("nebula.human_interactions")


async def _maybe_await(res: Any) -> Any:
    if inspect.isawaitable(res):
        return await res
    return res


class HumanInteractions:
    """Provides human-like input emulation for Playwright pages and locators."""

    @staticmethod
    def calculate_keystroke_delay(
        min_ms: float = 20.0,
        mean_ms: float = 65.0,
        std_ms: float = 22.0
    ) -> float:
        """Calculates a delay drawn from a normal distribution in milliseconds."""
        delay = random.gauss(mean_ms, std_ms)
        return max(min_ms, delay) / 1000.0

    @classmethod
    async def human_type(
        cls,
        target: Any,
        text: str,
        clear_first: bool = True,
        min_ms: float = 20.0,
        mean_ms: float = 65.0,
        std_ms: float = 22.0
    ) -> bool:
        """
        Types text character-by-character with natural Gaussian timing delays.
        Target can be a Playwright Page or Locator.
        """
        try:
            if clear_first:
                fill_fn = getattr(target, "fill", None)
                if callable(fill_fn):
                    await _maybe_await(fill_fn(""))
                elif hasattr(target, "keyboard"):
                    await _maybe_await(target.keyboard.press("Control+A"))
                    await _maybe_await(target.keyboard.press("Backspace"))

            keyboard = getattr(target, "keyboard", None)
            if keyboard is None and hasattr(target, "page"):
                keyboard = getattr(target.page, "keyboard", None)

            for char in text:
                delay_sec = cls.calculate_keystroke_delay(min_ms, mean_ms, std_ms)
                if keyboard and hasattr(keyboard, "type"):
                    await _maybe_await(keyboard.type(char))
                elif hasattr(target, "type") and callable(target.type):
                    await _maybe_await(target.type(char, delay=int(delay_sec * 1000)))
                await asyncio.sleep(delay_sec)

            return True
        except Exception as e:
            logger.error("human_type failed: %s", e)
            return False

    @classmethod
    async def human_scroll(
        cls,
        page: Any,
        delta_y: int = 300,
        steps: int = 5,
        selector: Optional[str] = None
    ) -> bool:
        """
        Emulates smooth human wheel/trackpad scrolling using exponential decay momentum.
        """
        try:
            if selector and hasattr(page, "locator"):
                element = page.locator(selector)
                if hasattr(element, "hover") and callable(element.hover):
                    await _maybe_await(element.hover())

            # Exponential decay momentum across steps
            total_scroll = float(delta_y)
            weights = [0.4, 0.25, 0.18, 0.12, 0.05][:steps]
            weight_sum = sum(weights)
            normalized_weights = [w / weight_sum for w in weights]

            for weight in normalized_weights:
                step_y = total_scroll * weight
                if hasattr(page, "mouse") and hasattr(page.mouse, "wheel"):
                    await _maybe_await(page.mouse.wheel(0, step_y))
                elif hasattr(page, "evaluate"):
                    await _maybe_await(page.evaluate(f"window.scrollBy(0, {step_y})"))
                await asyncio.sleep(random.uniform(0.04, 0.09))

            return True
        except Exception as e:
            logger.error("human_scroll failed: %s", e)
            return False

    @classmethod
    async def inject_date(
        cls,
        page: Any,
        selector: str,
        date_str: str
    ) -> bool:
        """
        Directly sets the date on <input type="date"> elements via DOM events,
        bypassing fragile multi-month calendar picker popups.
        """
        try:
            script = """
            ([sel, val]) => {
                const el = document.querySelector(sel);
                if (!el) return false;
                el.value = val;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
            """
            result = await _maybe_await(page.evaluate(script, [selector, date_str]))
            return bool(result)
        except Exception as e:
            logger.error("inject_date failed on %s: %s", selector, e)
            return False

    @classmethod
    async def human_press(
        cls,
        page: Any,
        key_or_chord: str
    ) -> bool:
        """
        Presses a key or key combination (e.g. Enter, Control+A, Tab, Escape).
        """
        try:
            keyboard = getattr(page, "keyboard", None)
            if keyboard and hasattr(keyboard, "press"):
                await _maybe_await(keyboard.press(key_or_chord))
                return True
            return False
        except Exception as e:
            logger.error("human_press failed on %s: %s", key_or_chord, e)
            return False
