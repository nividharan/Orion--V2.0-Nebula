"""
Checkout Guard: Financial Safety Barrier for Nebula Web Engine.
Detects payment forms, credit cards, Stripe frames, and halts automation before unauthorized payment.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("nebula.checkout_guard")

PAYMENT_SELECTORS = [
    'iframe[src*="stripe.com" i]',
    'iframe[title*="payment" i]',
    'iframe[id*="payment" i]',
    'input[autocomplete*="cc-number" i]',
    'input[name*="cardnumber" i]',
    'input[name*="creditcard" i]',
    'input[id*="card-number" i]',
    'input[id*="cardNumber" i]',
    'input[name*="cvv" i]',
    'input[id*="cvv" i]',
    'input[autocomplete*="cc-csc" i]',
]

PAYMENT_SUBMIT_BUTTON_PATTERNS = [
    "pay now",
    "place order",
    "complete purchase",
    "confirm payment",
    "pay with",
    "submit payment",
    "buy now",
]


class CheckoutGuard:
    """Detects payment interfaces and enforces safety locks on financial transactions."""

    @classmethod
    async def scan_payment_surface(cls, page: Any) -> Dict[str, Any]:
        """
        Scans active page for presence of payment elements or checkout submission gates.
        """
        detected_elements: List[str] = []

        try:
            for selector in PAYMENT_SELECTORS:
                count = await page.locator(selector).count()
                if count > 0:
                    detected_elements.append(selector)

            body_text = await page.inner_text("body")
            body_lower = body_text.lower()
            submit_matches = [p for p in PAYMENT_SUBMIT_BUTTON_PATTERNS if p in body_lower]

            is_payment_page = len(detected_elements) > 0 or len(submit_matches) > 0

            return {
                "payment_detected": is_payment_page,
                "detected_selectors": detected_elements,
                "submit_matches": submit_matches,
                "safety_lock_active": is_payment_page,
            }
        except Exception as e:
            logger.debug("scan_payment_surface encountered: %s", e)
            return {
                "payment_detected": False,
                "detected_selectors": [],
                "submit_matches": [],
                "safety_lock_active": False,
                "error": str(e)
            }

    @classmethod
    async def verify_action_permitted(
        cls,
        page: Any,
        action_name: str,
        armed: bool = False
    ) -> Dict[str, Any]:
        """
        Checks whether the intended action is safe to execute or blocked by Checkout Guard.
        If armed=False and a payment gateway is active, blocks execution.
        """
        scan = await cls.scan_payment_surface(page)
        if scan["payment_detected"] and not armed:
            logger.warning(
                "CHECKOUT GUARD TRIPPED: Action '%s' blocked. Payment surface active and --arm-payment not set.",
                action_name
            )
            return {
                "allowed": False,
                "blocked_reason": "checkout_guard_tripped",
                "message": (
                    "Financial transaction blocked by Checkout Guard. "
                    "Explicit user authorization (--arm-payment) is required to proceed with payment."
                ),
                "scan_details": scan
            }

        return {
            "allowed": True,
            "blocked_reason": None,
            "scan_details": scan
        }
