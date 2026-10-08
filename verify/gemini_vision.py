"""
Gemini Multimodal Vision Intelligence Client for Nebula Web Engine.
Phase 4 Implementation:
- Visual reasoning fallback with automated PII privacy redaction.
- Zero-cost gating (invoked ONLY when local heuristics are uncertain or an obstacle is spotted).
- Automated Pillow black-box redaction of sensitive form bounding boxes.
- Strict refusal on banking / login surfaces.
- Structured JSON remediation schema with click coordinates (x, y).
"""

import base64
import io
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

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


class PIIRedactor:
    """
    Automated client-side visual redaction for privacy defense.
    Draws opaque black fill over sensitive UI rectangles prior to cloud transmission.
    """

    @classmethod
    def redact_boxes(
        cls,
        image_bytes: bytes,
        rects: List[Dict[str, int]],
        fill_color: str = "#000000"
    ) -> bytes:
        """
        Overlays solid black boxes over sensitive coordinate rectangles.
        Each rect: {'x': int, 'y': int, 'width': int, 'height': int}.
        """
        if not rects:
            return image_bytes

        try:
            img = Image.open(io.BytesIO(image_bytes))
            draw = ImageDraw.Draw(img)

            for r in rects:
                x0 = r.get("x", 0)
                y0 = r.get("y", 0)
                w = r.get("width", 0)
                h = r.get("height", 0)
                x1 = x0 + w
                y1 = y0 + h
                draw.rectangle([x0, y0, x1, y1], fill=fill_color)

            out_buf = io.BytesIO()
            img.save(out_buf, format="PNG")
            return out_buf.getvalue()
        except Exception as e:
            logger.error("PII redaction failed: %s", e)
            return image_bytes


class GeminiVisionClient:
    """
    Multimodal visual reasoner that evaluates complex visual obstacles.
    Includes zero-cost gating, automated PII masking, and client-side privacy filtering.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.redactor = PIIRedactor()

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
        task_objective: str = "",
        sensitive_rects: Optional[List[Dict[str, int]]] = None
    ) -> VisionRemediation:
        """
        Redacts PII and sends image to Gemini Vision for structured obstacle remediation.
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

        # Automated PII Redaction
        redacted_bytes = image_bytes
        if sensitive_rects:
            redacted_bytes = self.redactor.redact_boxes(image_bytes, sensitive_rects)

        # Mock / Offline mode fallback if no API key is provided
        if not self.is_available():
            logger.info("Gemini Vision running in offline/deterministic heuristic mode.")
            return VisionRemediation(
                obstacle_detected=False,
                obstacle_type="none",
                recommended_action="continue",
                explanation="Offline mode: No Gemini API key provided. Relying on local heuristics."
            )

        # Production query to Gemini API
        try:
            b64_image = base64.b64encode(redacted_bytes).decode("utf-8")
            prompt = (
                f"You are the visual supervisor for an automated browser agent.\n"
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
