"""
Authentication & 2FA / Login Wall Handover Manager for Nebula Web Engine.
Detects OTP, MFA, and SSO login barriers, and orchestrates human handover.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("nebula.auth_manager")

DEFAULT_PROFILE_DIR = Path("profiles") / "nebula_user"

AUTH_SELECTORS = [
    'input[autocomplete*="one-time-code"]',
    'input[name*="otp" i]',
    'input[name*="2fa" i]',
    'input[name*="mfa" i]',
    'input[id*="otp" i]',
    'input[id*="2fa" i]',
    'input[id*="mfa" i]',
    'input[placeholder*="verification code" i]',
    'input[placeholder*="enter code" i]',
    'input[placeholder*="security code" i]',
]

AUTH_TEXT_PATTERNS = [
    "verification code",
    "enter the 6-digit code",
    "two-factor authentication",
    "check your phone",
    "authenticator app",
    "approve sign-in",
    "security key",
    "verify your identity",
    "one-time password",
]


class AuthManager:
    """Manages persistent browser profiles and detects human login/2FA handover events."""

    def __init__(self, profile_dir: Optional[Path] = None):
        self.profile_dir = Path(profile_dir) if profile_dir else DEFAULT_PROFILE_DIR
        self._ensure_profile_dir()

    def _ensure_profile_dir(self) -> Path:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        return self.profile_dir

    @classmethod
    async def check_auth_required(cls, page: Any) -> Dict[str, Any]:
        """
        Scans current page for 2FA/OTP inputs or login-wall challenge banners.
        """
        try:
            # Check input element selectors
            for selector in AUTH_SELECTORS:
                count = await page.locator(selector).count()
                if count > 0:
                    return {
                        "required": True,
                        "type": "2fa_input",
                        "selector": selector,
                        "message": "Two-factor authentication / OTP input detected."
                    }

            # Check page text for authentication challenge indicators
            body_text = await page.inner_text("body")
            body_lower = body_text.lower()
            for pattern in AUTH_TEXT_PATTERNS:
                if pattern in body_lower:
                    return {
                        "required": True,
                        "type": "auth_challenge_text",
                        "pattern": pattern,
                        "message": f"Auth challenge text detected: '{pattern}'"
                    }

            return {"required": False, "type": "none"}
        except Exception as e:
            logger.debug("check_auth_required encountered: %s", e)
            return {"required": False, "type": "error", "error": str(e)}

    @classmethod
    async def wait_for_human_handover(
        cls,
        page: Any,
        timeout_sec: float = 120.0,
        poll_interval_sec: float = 2.0
    ) -> bool:
        """
        Polls until the human completes the login/2FA wall and the page transitions away.
        """
        logger.info("Human handover initiated. Waiting up to %ds for user completion...", int(timeout_sec))
        elapsed = 0.0
        while elapsed < timeout_sec:
            await asyncio.sleep(poll_interval_sec)
            elapsed += poll_interval_sec
            status = await cls.check_auth_required(page)
            if not status.get("required"):
                logger.info("Human authentication completed successfully!")
                return True
        logger.warning("Human handover timed out after %ds.", int(timeout_sec))
        return False
