"""
verify/playback.py — Phase 5: Verification & Self-Healing
=========================================================
Principle: Code does the work, DOM-first perception and surgical healing.
No blind keypresses (no random spacebar or 'k' taps).
Deterministic inspection of <video> state: paused, currentTime, readyState,
ads showing, skippable ads, consent popups.
Vision fallback crops strictly to browser viewport and redacts sensitive inputs.
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger("Orion.VerifyPlayback")

SKIP_AD_SELECTORS: List[str] = [
    ".ytp-ad-skip-button",
    ".ytp-skip-ad-button",
    ".ytp-ad-skip-button-modern",
    "button.ytp-ad-skip-button-icon",
    "button[class*='skip-button']",
    "[aria-label*='Skip ad' i]",
    "[aria-label*='Skip advertisement' i]",
    ".ytp-ad-skip-button-slot button",
    "#skip-button\\:5",
    "button:has-text('Skip')",
    "button:has-text('Skip Ad')",
    "button:has-text('Skip ad')",
]

CONSENT_MODAL_SELECTORS: List[str] = [
    "ytd-consent-bump-v2-lightbox",
    "#consent-bump",
    "tp-yt-paper-dialog",
    ".cookie-modal",
    "#cookie-banner",
    "#cmp-modal",
    "[aria-modal='true'][role='dialog']",
]

CONSENT_DISMISS_BUTTONS: List[str] = [
    "#reject-btn",
    "#cmp-reject-all",
    "button[aria-label*='Reject all' i]",
    "button[aria-label*='Accept all' i]",
    "button:has-text('Reject all')",
    "button:has-text('Accept all')",
    "button:has-text('I agree')",
    "button:has-text('Dismiss')",
    "button:has-text('Close')",
]


@dataclass
class PlaybackState:
    """Structured representation of media playback in the DOM."""
    has_video: bool
    is_playing: bool
    is_paused: bool
    ad_showing: bool
    can_skip_ad: bool
    skip_button_selector: Optional[str] = None
    has_consent_modal: bool = False
    current_time: float = 0.0
    duration: float = 0.0
    ready_state: int = 0
    muted: bool = False
    volume: float = 1.0
    ended: bool = False
    status: str = "UNKNOWN"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_video": self.has_video,
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "ad_showing": self.ad_showing,
            "can_skip_ad": self.can_skip_ad,
            "skip_button_selector": self.skip_button_selector,
            "has_consent_modal": self.has_consent_modal,
            "current_time": round(self.current_time, 2),
            "duration": round(self.duration, 2),
            "ready_state": self.ready_state,
            "muted": self.muted,
            "volume": round(self.volume, 2),
            "ended": self.ended,
            "status": self.status,
            "details": self.details,
        }


def _evaluate_dom_state(page) -> Dict[str, Any]:
    """
    Executes pure DOM inspection in the browser context via page.evaluate.
    Safe against exceptions, returns raw dictionary.
    """
    js_probe = """
    () => {
        try {
            function isVisible(el) {
                if (!el) return false;
                try {
                    const rects = el.getClientRects();
                    if (!rects || rects.length === 0) return false;
                    const style = window.getComputedStyle(el);
                    return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
                } catch (e) {
                    return Boolean(el.offsetWidth > 0 || el.offsetHeight > 0);
                }
            }

            const v = document.querySelector('video');

            // Player container check for ad-showing class (YouTube standard)
            const player = document.querySelector('#movie_player, .html5-video-player, #player-container');
            const hasPlayerAdClass = player ? (
                player.classList.contains('ad-showing') ||
                player.classList.contains('ad-interrupting')
            ) : false;

            // Direct ad overlays
            const adOverlayElements = Array.from(document.querySelectorAll(
                '.ytp-ad-player-overlay, .video-ads.ytp-ad-module, [class*="ad-showing"]'
            ));
            const hasVisibleAdOverlay = adOverlayElements.some(isVisible);

            const adShowing = hasPlayerAdClass || hasVisibleAdOverlay;

            const skipSelectors = [
                '.ytp-ad-skip-button',
                '.ytp-skip-ad-button',
                '.ytp-ad-skip-button-modern',
                'button.ytp-ad-skip-button-icon',
                'button[class*="skip-button"]',
                '.ytp-ad-skip-button-slot button',
                '#skip-button\\\\:5'
            ];
            let foundSkip = null;
            for (const s of skipSelectors) {
                try {
                    const el = document.querySelector(s);
                    if (isVisible(el)) {
                        foundSkip = s;
                        break;
                    }
                } catch (e) {}
            }

            const consentSelectors = [
                'ytd-consent-bump-v2-lightbox',
                '#consent-bump',
                'tp-yt-paper-dialog',
                '.cookie-modal',
                '#cookie-banner',
                '#cmp-modal',
                '[aria-modal="true"][role="dialog"]'
            ];
            let foundConsent = false;
            for (const cs of consentSelectors) {
                try {
                    const el = document.querySelector(cs);
                    if (isVisible(el)) {
                        foundConsent = true;
                        break;
                    }
                } catch (e) {}
            }

            if (!v) {
                return {
                    has_video: false,
                    is_playing: false,
                    is_paused: false,
                    ad_showing: adShowing,
                    can_skip_ad: Boolean(foundSkip),
                    skip_button_selector: foundSkip,
                    has_consent_modal: foundConsent,
                    current_time: 0.0,
                    duration: 0.0,
                    ready_state: 0,
                    muted: false,
                    volume: 1.0,
                    ended: false,
                    status: 'NO_VIDEO',
                    details: { reason: 'No HTML5 video element found in DOM' }
                };
            }

            const isPaused = Boolean(v.paused);
            const isEnded = Boolean(v.ended);
            const currentTime = Number(v.currentTime || 0);
            const duration = Number(v.duration || 0);
            const readyState = Number(v.readyState || 0);
            const isMuted = Boolean(v.muted);
            const volume = Number(v.volume != null ? v.volume : 1.0);

            // Active playback criteria: not paused, not ended, readyState >= 2 (HAVE_CURRENT_DATA)
            const isPlaying = !isPaused && !isEnded && readyState >= 2 && !adShowing;

            let status = 'PAUSED';
            if (foundConsent) {
                status = 'CONSENT_BLOCKED';
            } else if (adShowing && foundSkip) {
                status = 'AD_SKIPPABLE';
            } else if (adShowing) {
                status = 'AD_PLAYING';
            } else if (isEnded) {
                status = 'ENDED';
            } else if (isPlaying) {
                status = 'PLAYING';
            } else if (isPaused) {
                status = 'PAUSED';
            } else if (readyState < 2) {
                status = 'BUFFERING';
            }

            return {
                has_video: true,
                is_playing: isPlaying,
                is_paused: isPaused,
                ad_showing: adShowing,
                can_skip_ad: Boolean(foundSkip),
                skip_button_selector: foundSkip,
                has_consent_modal: foundConsent,
                current_time: currentTime,
                duration: duration,
                ready_state: readyState,
                muted: isMuted,
                volume: volume,
                ended: isEnded,
                status: status,
                details: {}
            };
        } catch (err) {
            return {
                has_video: false,
                is_playing: false,
                is_paused: false,
                ad_showing: false,
                can_skip_ad: false,
                skip_button_selector: null,
                has_consent_modal: false,
                current_time: 0.0,
                duration: 0.0,
                ready_state: 0,
                muted: false,
                volume: 1.0,
                ended: false,
                status: 'ERROR',
                details: { error: String(err) }
            };
        }
    }
    """
    return page.evaluate(js_probe)


def verify_playback(
    page,
    check_progress_delta: bool = False,
    delta_timeout: float = 0.5
) -> PlaybackState:
    """
    Performs DOM-first inspection of video playback state.
    
    If check_progress_delta is True and video reports PLAYING, pauses delta_timeout
    seconds and confirms currentTime actually advances (detecting frozen decoders or stalls).
    """
    raw = _evaluate_dom_state(page)
    state = PlaybackState(
        has_video=raw.get("has_video", False),
        is_playing=raw.get("is_playing", False),
        is_paused=raw.get("is_paused", False),
        ad_showing=raw.get("ad_showing", False),
        can_skip_ad=raw.get("can_skip_ad", False),
        skip_button_selector=raw.get("skip_button_selector"),
        has_consent_modal=raw.get("has_consent_modal", False),
        current_time=float(raw.get("current_time", 0.0)),
        duration=float(raw.get("duration", 0.0)),
        ready_state=int(raw.get("ready_state", 0)),
        muted=raw.get("muted", False),
        volume=float(raw.get("volume", 1.0)),
        ended=raw.get("ended", False),
        status=raw.get("status", "UNKNOWN"),
        details=raw.get("details", {}),
    )

    if check_progress_delta and state.is_playing and not state.ad_showing:
        t1 = state.current_time
        time.sleep(delta_timeout)
        raw2 = _evaluate_dom_state(page)
        t2 = float(raw2.get("current_time", 0.0))
        if t2 <= t1:
            logger.warning("Playback reported active but currentTime did not advance (t1=%.2f, t2=%.2f)", t1, t2)
            state.is_playing = False
            state.status = "BUFFERING"
            state.details["progress_stalled"] = True
        else:
            state.current_time = t2

    return state


def dismiss_consent_modals(page) -> bool:
    """
    Surgically dismisses cookie / consent dialogs that block page interaction.
    Returns True if an overlay or modal button was clicked.
    """
    # Try evaluate click on first visible dismiss candidate
    try:
        dismissed = page.evaluate("""
            () => {
                function isVisible(el) {
                    if (!el) return false;
                    try {
                        const rects = el.getClientRects();
                        return rects && rects.length > 0;
                    } catch (e) {
                        return el.offsetWidth > 0 || el.offsetHeight > 0;
                    }
                }
                const candidates = [
                    '#reject-btn', '#cmp-reject-all', '#accept-btn',
                    'button[aria-label*="Reject" i]', 'button[aria-label*="Accept" i]',
                    'ytd-consent-bump-v2-lightbox button'
                ];
                for (const c of candidates) {
                    const el = document.querySelector(c);
                    if (isVisible(el)) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        if dismissed:
            logger.info("Dismissed consent modal via DOM evaluation")
            return True
    except Exception:
        pass

    for sel in CONSENT_DISMISS_BUTTONS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                logger.info("Dismissed consent modal via selector '%s'", sel)
                return True
        except Exception:
            continue

    return False


def skip_ad_if_available(page) -> bool:
    """
    Surgically clicks the YouTube Skip Ad button if present.
    Returns True if successfully clicked.
    """
    # Try evaluate click on first visible skip candidate
    try:
        clicked = page.evaluate("""
            () => {
                function isVisible(el) {
                    if (!el) return false;
                    try {
                        const rects = el.getClientRects();
                        return rects && rects.length > 0;
                    } catch (e) {
                        return el.offsetWidth > 0 || el.offsetHeight > 0;
                    }
                }
                const selectors = [
                    '.ytp-ad-skip-button',
                    '.ytp-skip-ad-button',
                    '.ytp-ad-skip-button-modern',
                    'button.ytp-ad-skip-button-icon',
                    '.ytp-ad-skip-button-slot button',
                    'button[class*="skip-button"]'
                ];
                for (const s of selectors) {
                    const el = document.querySelector(s);
                    if (isVisible(el)) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        if clicked:
            logger.info("Clicked skip ad button via DOM evaluation")
            return True
    except Exception:
        pass

    for sel in SKIP_AD_SELECTORS:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                logger.info("Clicked skip ad button via '%s'", sel)
                return True
        except Exception:
            continue

    return False


def ensure_video_playing(page, unmute_if_muted: bool = False) -> bool:
    """
    Surgically calls video.play() on the HTML5 video element only if paused.
    Never sends blind global keyboard spacebars or letters.
    """
    js = f"""
    () => {{
        const v = document.querySelector('video');
        if (!v) return false;
        if ({str(unmute_if_muted).lower()}) {{
            v.muted = false;
        }}
        if (v.paused) {{
            const res = v.play();
            if (res && res.catch) {{
                res.catch(() => {{}});
            }}
            return true;
        }}
        return false;
    }}
    """
    try:
        return bool(page.evaluate(js))
    except Exception as e:
        logger.warning("ensure_video_playing JS call failed: %s", e)
        return False


def heal_playback(
    page,
    max_retries: int = 3,
    probe_delay: float = 0.5,
    unmute_if_muted: bool = False
) -> PlaybackState:
    """
    Self-healing loop:
      1. Inspects current state.
      2. If consent modal blocks, dismisses it.
      3. If skippable ad active, clicks Skip Ad.
      4. If paused, surgical video.play() is called.
      5. Re-probes until playing or max_retries exhausted.
    """
    state = verify_playback(page)
    if state.is_playing:
        return state

    for attempt in range(1, max_retries + 1):
        logger.info("Healing attempt %d/%d (status: %s)", attempt, max_retries, state.status)

        if state.has_consent_modal:
            dismiss_consent_modals(page)
            time.sleep(probe_delay)

        if state.ad_showing and state.can_skip_ad:
            skip_ad_if_available(page)
            time.sleep(probe_delay)

        if state.has_video and state.is_paused:
            ensure_video_playing(page, unmute_if_muted=unmute_if_muted)
            time.sleep(probe_delay)

        state = verify_playback(page)
        if state.is_playing:
            logger.info("Healing successful on attempt %d", attempt)
            return state

    return state


def capture_playback_viewport_safe(
    page,
    output_path: Optional[str] = None,
    redact_inputs: bool = True
) -> str:
    """
    Cropped Vision Fallback:
    Captures screenshot cropped strictly to browser viewport.
    If redact_inputs is True, applies temporary high-contrast dark redaction
    to sensitive credentials, passwords, and payment inputs before capture.
    """
    if output_path is None:
        os.makedirs(".cache/screenshots", exist_ok=True)
        output_path = os.path.abspath(f".cache/screenshots/verify_{int(time.time()*1000)}.png")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    redaction_style_id = "__orion_redact_style__"

    if redact_inputs:
        try:
            page.evaluate(f"""
                () => {{
                    if (document.getElementById('{redaction_style_id}')) return;
                    const style = document.createElement('style');
                    style.id = '{redaction_style_id}';
                    style.innerHTML = `
                        input[type="password"],
                        input[type="email"],
                        input[type="tel"],
                        input[autocomplete*="cc-"],
                        input[name*="pass"],
                        input[name*="card"],
                        .sensitive-redact {{
                            filter: blur(12px) !important;
                            background-color: #111 !important;
                            color: transparent !important;
                        }}
                    `;
                    document.head.appendChild(style);
                }}
            """)
        except Exception:
            pass

    try:
        page.screenshot(path=output_path, full_page=False)
    finally:
        if redact_inputs:
            try:
                page.evaluate(f"""
                    () => {{
                        const el = document.getElementById('{redaction_style_id}');
                        if (el) el.remove();
                    }}
                """)
            except Exception:
                pass

    return output_path
