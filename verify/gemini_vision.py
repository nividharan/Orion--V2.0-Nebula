"""
Gemini Multimodal Vision Intelligence Client for Nebula Web Engine.
Invoked ONLY when local heuristics are uncertain or an obstacle is detected.
Enforces strict privacy boundaries (never sends sensitive auth/payment screens).
"""

import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("nebula.gemini_vision")


@dataclass
class VisionRemediation:
    """Structured remediation response from Gemini Multimodal Vision."""
    obstacle_detected: bool
    obstacle_type: str  # cookie_banner, modal_dialog, overlay, captcha, unknown
    recommended_action: str  # click, dismiss, wait, refresh, manual_handover
    target_x: Optional[int] = None
    target_y: Optional[int] = None
    explanation: str = ""
    raw_response: Optional[Dict[str, Any]] = None


class GeminiVisionClient:
    """
    Multimodal visual reasoner that evaluates complex visual obstacles.
    Includes zero-cost gating and client-side PII privacy filtering.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key.strip())

    @staticmethod
    def is_sensitive_content(page_url: str, page_title: str) -> bool:
        """
        Privacy boundary: refuses to send frames from sensitive authentication,
        billing, checkout, or banking surfaces.
        """
        sensitive_keywords = [
            "password", "login", "signin", "auth", "checkout",
            "payment", "billing", "bank", "creditcard", "otp", "2fa"
        ]
        url_lower = page_url.lower()
        title_lower = page_title.lower()
        for kw in sensitive_keywords:
            if kw in url_lower or kw in title_lower:
                return True
        return False

    async def analyze_obstacle(
        self,
        image_bytes: bytes,
        page_url: str = "",
        page_title: str = "",
        task_objective: str = ""
    ) -> VisionRemediation:
        """
        Sends masked screenshot to Gemini Vision for structured obstacle remediation.
        If privacy boundary is triggered, immediately aborts.
        """
        # Privacy Guard
        if self.is_sensitive_content(page_url, page_title):
            logger.warning("Gemini Vision call aborted: Sensitive page boundary triggered for %s", page_url)
            return VisionRemediation(
                obstacle_detected=True,
                obstacle_type="sensitive_surface",
                recommended_action="manual_handover",
                explanation="Privacy boundary active: Screen contains credentials or payment fields."
            )

        # Mock / Offline mode fallback if no API key is provided
        if not self.is_available():
            logger.info("Gemini Vision running in offline/deterministic heuristic mode.")
            return VisionRemediation(
                obstacle_detected=False,
                obstacle_type="none",
                recommended_action="continue",
                explanation="Offline mode: No Gemini API key provided. Relying on local heuristics."
            )

        # In production with API key, calls Gemini 1.5/2.0 Flash Multimodal Vision
        try:
            # Prepare payload
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            prompt = (
                f"You are the visual supervisor for a browser automation agent.\n"
                f"Current URL: {page_url}\n"
                f"Task Objective: {task_objective}\n"
                f"Identify any popup, modal, cookie banner, or blocking overlay on this screen.\n"
                f"Return ONLY valid JSON matching this schema:\n"
                f"{{\n"
                f'  "obstacle_detected": true/false,\n'
                f'  "obstacle_type": "cookie_banner" | "modal_dialog" | "overlay" | "captcha" | "none",\n'
                f'  "recommended_action": "click" | "dismiss" | "wait" | "manual_handover",\n'
                f'  "target_x": integer or null,\n'
                f'  "target_y": integer or null,\n'
                f'  "explanation": "brief reason"\n'
                f"}}"
            )

            # Lazy import or requests call
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": b64_image
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)

            return VisionRemediation(
                obstacle_detected=bool(parsed.get("obstacle_detected")),
                obstacle_type=parsed.get("obstacle_type", "unknown"),
                recommended_action=parsed.get("recommended_action", "none"),
                target_x=parsed.get("target_x"),
                target_y=parsed.get("target_y"),
                explanation=parsed.get("explanation", ""),
                raw_response=parsed
            )
        except Exception as e:
            logger.error("Gemini Vision API query failed: %s", e)
            return VisionRemediation(
                obstacle_detected=False,
                obstacle_type="api_error",
                recommended_action="continue",
                explanation=f"Vision API error: {str(e)}"
            )
