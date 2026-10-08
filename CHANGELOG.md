# Changelog

All notable changes to **Orion System × Nebula Model** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
[Semantic Versioning](https://semver.org/).

---

## [2.0.0] — 2026-10-08

### Added

- **Multi-Agent Society** — 5-agent collaborative execution model:
  - `Commander Nebula` decomposes natural language goals into typed execution plans
  - `Chrome Executor` drives Playwright browser actions with domain allow-lists and action guards
  - `Perception Inspector` runs post-action page health checks (error pages, modals, login walls, visual stalls)
  - `Studio Narrator` announces task progress via Microsoft OneCore SAPI text-to-speech
  - `Verifier Critic` closes the loop — verifies outcomes and triggers self-healing when needed

- **Natural Language Input Pipeline** — 8-stage understanding engine:
  - Wake-word stripping, phonetic typo correction (`tamol → tamil`, `yotube → youtube`), filler removal
  - Bilingual Tamil/English command normalization
  - Conversational reference resolution (`"it"`, `"that site"`, `"again"` → last context)
  - Confidence gating: auto-runs clear commands, asks on ambiguity, requires approval on sensitive actions

- **Page Health Verification** — post-action DOM and visual inspector:
  - Detects error pages, blocking modals/dialogs, and login-wall redirects via DOM signals
  - Perceptual visual diff (phash) to confirm or deny page-level changes after actions
  - Frozen-frame detection when visual mutation was expected but none occurred
  - Structured `Verdict` (OK / FAIL / UNCERTAIN) with signal and evidence for downstream healing

- **Media Resolver** — intelligent YouTube playback pipeline:
  - Relevance scoring: token overlap, official-video boost, cover/lyrics/shorts penalty
  - Ad and live-stream filtering by duration and title heuristics
  - 30-minute TTL candidate cache with fast `chosen_video` path
  - YouTube Data API v3 with automatic scraper fallback

- **AI Brain with Local Fallback** — `NebulaBrain` planning engine:
  - Gemini AI intent decomposition with structured JSON validation
  - Automatic retry (max 2 calls) with local parser fallback on timeout or malformed response
  - Deterministic candidate scoring (`pick_candidate`) independent of AI
  - Rejects raw URLs, enforces action allow-list on all AI-generated plans

- **Hardened Playwright Web Engine**:
  - Anti-bot stealth: `navigator.webdriver` always reports `false`
  - Multi-step CMP consent handlers (OneTrust, Cookiebot, generic overlays)
  - Atomic browser state persistence and 7-day artifact auto-pruning

- **Structured Observability**:
  - Per-step JSON audit logs with automatic redaction of API keys, tokens, and passwords
  - Task-level metrics: success rate, total latency, token spend, healed step count
  - Markdown audit report generation
  - Single-call full regression runner across all test modules

- **Safety & Integrity**:
  - Atomic file writes (write-to-temp, rename) for all persistent state
  - Owner-only permissions on sensitive cache files
  - Git exposure guard — aborts startup if secrets are accidentally tracked
  - Kill switch for immediate halt of any running task

### Fixed

- Input normalization falsely prepending `"play"` to commands that already started with an English verb (e.g., `"play this song"` → `"play play this song"`). Added an English verb-prefix guard to the Tamil normalization stage.
- Silent `UNKNOWN` intent fallback caused by unrecognized AI-returned alias strings (`media_play`, `tab_operation`). Aliases are now normalized to their canonical forms before schema validation.

### Changed

- Desktop mouse/keyboard automation moved to `legacy/` — disabled by default. Web-first Playwright execution is now the primary path.
- Screen watcher (Win32 + PIL) moved to `legacy/` — replaced by in-process DOM and visual diff verification.

---

## [1.x] — Pre-2.0 (Legacy)

- Direct Win32 desktop automation (mouse, keyboard, window management)
- PyWin32 screen capture and perceptual hashing
- Blender IPC integration
- Audio recording pipeline
