# 🌐 Nebula Web & Chrome Model: Dedicated Building Plan

## 1. System Identity & Mission

**Nebula** is the specialized **Cognitive Browser Agent & Chrome Engine** of the architecture.
* **Mission**: Handle all complex, human-grade web operations inside Google Chrome: browse pages, fill dynamic forms, interact with multi-tab workflows, stream media, auto-dismiss cookie banners, detect login/2FA walls for human handover, lock down financial checkout screens, and visually inspect web state using Gemini Multimodal Vision.
* **Non-Goals**: Nebula does **not** simulate Win32 OS hardware keystrokes or manage native Windows desktop processes (that is delegated entirely to Orion).

---

## 2. Component Architecture & File Inventory

```
Nebula Cognitive Web Engine/
├── web_engine/
│   ├── engine.py                 # Hardened Playwright browser lifecycle & worker thread
│   ├── stealth.py                # Anti-bot stealth scripts (navigator.webdriver bypass)
│   ├── consent.py                # Automated OneTrust, Cookiebot, and Google banner clearing
│   ├── human_interactions.py     # Gaussian keystroke delays, smooth scrolling, date injection
│   ├── auth_manager.py           # Persistent profiles, login-wall & 2FA handover detector
│   └── checkout_guard.py         # Financial safety gate (auto-halts at payment screens)
├── session.py                    # Persistent NebulaSession owner across sequential commands
├── media_control.py              # Instant DOM media shortcuts (pause, resume, volume, skip ad)
├── verify/
│   ├── screen_watcher.py         # 2–6 FPS perception loop, pHash diffs, dead-click detector
│   ├── gemini_vision.py          # Multimodal Gemini API client with structured remediation
│   └── page_watcher.py           # DOM-level health checks & error page patterns
├── hud/
│   ├── terminal_hud.py           # Unbuffered ANSI real-time live telemetry status bar
│   ├── desktop_hud.py            # Floating Windows glassmorphic HUD pill (WS_EX_NOACTIVATE)
│   └── telemetry_hub.py          # Central event bus broadcasting state to HUD & WebSocket
├── orion_autogen.py              # 5-Agent Cognitive Society & OODA re-planning loop
└── tests/
    ├── test_interactive_session.py
    ├── test_screen_watcher.py
    └── test_gemini_vision.py
```

---

## 3. Subsystem Specifications

### Subsystem 1: Human-Grade Browser Interactions (`human_interactions.py`)
* **Natural Keystroke Engine**:
  * Types text using Gaussian distributed intervals:
    $$t_{\text{delay}} = \max(20\text{ ms}, \mathcal{N}(65\text{ ms}, 22\text{ ms}))$$
  * Supports modifier chords: `Ctrl+A`, `Ctrl+C`, `Ctrl+V`, `Enter`, `Tab`.
* **Smooth Wheel Scrolling**:
  * Emulates human trackpad/mouse wheel momentum:
    `page.mouse.wheel(delta_x, delta_y)` with exponential deceleration curves.
  * Targets nested scrollable `<div>` containers using CSS overflow checks.
* **Direct Date Injection**:
  * Bypasses fragile multi-month calendar clicks by dispatching native DOM events directly to hidden or underlying `<input type="date">` elements.

### Subsystem 2: Identity & High-Stakes Safety Locks (`auth_manager.py` & `checkout_guard.py`)
* **Persistent Session Profiles**:
  * Launches Chrome from `profiles/nebula_user` so cookies, tokens, and Google/Amazon logins persist indefinitely across reboots.
* **2FA / Login Wall Handover**:
  * Detects login walls, SMS OTP inputs, and authenticator prompts.
  * Pauses automation immediately, announces to user via Studio Narrator: *"Authentication required. Please verify on your phone/screen."*
  * Resumes automatically once the destination authenticated URL is detected.
* **Checkout Guard (Financial Safety Barrier)**:
  * Scans viewport for payment gateways (Stripe iframes, credit card inputs, UPI QR codes, PayPal buttons).
  * **Strict Policy**: Hard-halts automation before payment submission. Takes an evidence screenshot, prints the final price and summary to the terminal/HUD, and transfers control to the human.

### Subsystem 3: Continuous Screen Watcher & Stall Detector (`screen_watcher.py`)
* **Adaptive Perception Loop**:
  * Takes baseline screenshot before action (`pHash_before`) and after action (`pHash_after`).
  * Computes normalized visual delta percentage ($0.0\%$ to $100.0\%$).
* **Dead-Click Detector**:
  * If an action is dispatched but $\Delta_{\text{visual}} < 0.5\%$ after 1.5s, flags `signal = "dead_click_detected"`.
* **Error Banner Detector**:
  * Catches Chrome crash banners (`"Aw, Snap!"`), HTTP `404`/`500`, and access denied screens.

### Subsystem 4: Gemini Multimodal Vision Intelligence (`gemini_vision.py`)
* **Zero-Cost Gating**:
  * Local heuristics run at 0ms and $0.00. Gemini Vision is invoked **only** when `verdict == UNCERTAIN` or an obstacle is spotted.
* **Privacy Boundary**:
  * Password and credit card inputs are strictly masked and never sent to cloud APIs.
* **Structured JSON Remediation**:
  * Gemini Vision inspects the screenshot and returns exact click coordinates `(x, y)` to dismiss the obstacle (e.g. cookie banner, modal dialog).
  * Nebula clicks the coordinates, clears the obstacle, and resumes the primary goal.

### Subsystem 5: Multi-Channel Live HUD (`hud/`)
* **Desktop Floating HUD (`desktop_hud.py`)**:
  * A semi-transparent floating pill positioned in the corner of your screen.
  * Always-on-top, but uses `WS_EX_NOACTIVATE` so it **never steals keyboard focus** from Chrome or other applications.
  * Displays: Active Agent badge, Health Status pill (🟢/🟡/🔴), Current Step, Live Reasoning subtitle, and Abort button.
* **Terminal Live ANSI Bar (`terminal_hud.py`)**:
  * Unbuffered real-time status bar for CLI users.
* **WebSocket Telemetry Stream**:
  * Streams live JSON events to web dashboards.

---

## 4. Phased Implementation Roadmap for Nebula

| Step | Action | Output / File | Verification Method |
|:---:|---|---|---|
| **N.1** | Humanized interactions & date injection | `web_engine/human_interactions.py` | Verify Gaussian typing delay & wheel scrolling |
| **N.2** | 2FA handover & Checkout Guard safety locks | `web_engine/auth_manager.py`<br>`web_engine/checkout_guard.py` | Unit tests with mock payment & OTP DOM fixtures |
| **N.3** | Continuous Screen Watcher & dead-click detector | `verify/screen_watcher.py` | Verify pHash diffing on local fixture server |
| **N.4** | Gemini Multimodal Vision remediation client | `verify/gemini_vision.py` | Test with mocked Gemini vision JSON response |
| **N.5** | Multi-channel Live HUD (Desktop Pill + Terminal) | `hud/desktop_hud.py`<br>`hud/terminal_hud.py` | Verify thread-safe updates without focus stealing |
| **N.6** | AutoGen OODA reactive re-planning integration | `orion_autogen.py` | End-to-end multi-agent reactive execution test |
