# Changelog

All notable changes to **Orion System × Nebula Model** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] — 2026-10-08

### 🔒 Phase 0 — Safety & Cleanup
- **Added** atomic write helper (`config.atomic_write`) — writes to temp file, renames atomically
- **Added** owner-only file permissions (`set_owner_only_permissions`) for sensitive cache files
- **Added** `check_git_tracked_cache()` guard — warns if `.cache/` is accidentally git-tracked
- **Added** `cleanup_old_artifacts()` — prunes artifacts older than 7 days automatically
- **Hardened** `.gitignore` to exclude profiles, logs, traces, `.cache`, `__pycache__`

### 🌐 Phase 1 — Web-Only Playwright Facade
- **Refactored** scope to web-only: removed desktop executor from the primary execution path
- **Added** anti-bot stealth: `navigator.webdriver` always reports `false`
- **Added** multi-step CMP consent handlers (OneTrust, Cookiebot, generic overlay)
- **Added** startup Git exposure guard — aborts if secrets are tracked
- **Added** 7-day artifact auto-pruning on `BrowserManager` init
- **Added** atomic browser state persistence (profiles/)

### 📺 Phase 2 — Media Resolver
- **Added** `resolvers/youtube.py` — YouTube search with structured `Candidate` scoring
- **Added** ad/short/live filtering by duration and title heuristics
- **Added** relevance scoring: token overlap, official video boost, cover/lyrics penalty
- **Added** TTL-based candidate caching (30 min default) with `chosen_video` fast path
- **Added** YouTube Data API v3 integration with scraper fallback (`api_client.py`)

### 🧠 Phase 3–4 — Intent Normalization & AI Brain
- **Added** `nebula_brain.py`: `NebulaBrain` with Gemini AI planning + local parser fallback
- **Added** intent alias normalization: `media_play → media_playback`, `tab_operation → tab_management`
- **Added** `_parse_ai_plan()`: validates AI JSON, rejects raw URL targets, enforces action allow-list
- **Added** `pick_candidate()`: deterministic scoring without AI
- **Added** `pick_candidate_with_ai()`: AI-assisted selection with deterministic fallback
- **Added** retry logic: max 2 AI calls per `plan()` invocation; falls back to local parser on timeout/bad JSON
- **Fixed** silent `UNKNOWN` intent fallback caused by unrecognized alias strings

### 🗣️ Phase 5 — Input Pipeline
- **Added** `input_pipeline.py`: 8-stage natural language understanding pipeline
  1. Capture (text / voice + STT confidence)
  2. Clean (wake word strip, phonetic typo fix, filler removal)
  3. Cancel/Negation interception
  4. Compound command splitting
  5. Reference resolution (`"it"`, `"that site"`, `"again"` → last context)
  6. Understand (local parser first; LLM only on low confidence)
  7. Schema validation
  8. Confidence gate (RUN / ASK / APPROVE)
- **Added** bilingual Tamil/English normalization (`_normalize_tamil_query`)
- **Added** phonetic typo corrections: `tamol→tamil`, `telgu→telugu`, `yotube→youtube`, etc.
- **Added** 100-command evaluation suite (`tests/test_input_pipeline.py`)

### 👁️ Phase 6 — Page Watcher
- **Added** `verify/page_watcher.py`: `PageWatcher` class for post-action page health verification
  - DOM error-page detection (HTTP 4xx/5xx title patterns, error keywords)
  - Blocking modal/dialog detection via ARIA roles and overlay heuristics
  - Login-wall / auth-redirect detection
  - Perceptual visual diff using `imagehash` phash + pixel diff fallback
  - Frozen-frame detection (no visual change when change was expected)
  - `WatchResult` with `Verdict` (OK / FAIL / UNCERTAIN), signal, and evidence dict
  - 24-hour log file retention (`verify/logs/`)
- **Added** `verify/__init__.py` unified public surface for both `playback` and `page_watcher`

### 🤖 Phase 7 — Agent Society Integration
- **Added** `web_verify_page()` tool in `tools/typed_tools.py` — wraps `PageWatcher.verify_action_result()`
- **Updated** `tools/agent_society.py` `SocietyCoordinator`: verifier now branches on `plan.intent`
  - Media intents (`MEDIA_PLAY`, `MEDIA_PLAYBACK`) → `media_verify_playback` + self-heal loop
  - All other intents → `web_verify_page`
- **Updated** `ROLE_TOOL_ALLOW_LIST`: `AgentRole.VERIFIER` now includes `web_verify_page`
- **Exported** `web_verify_page` via `tools/__init__.py`

### 📊 Phase 8 — Observability & Hardening
- **Added** `observability.py`:
  - `StructuredLogger`: thread-safe JSON-lines step logger (appends to `.cache/audit_logs/task_<id>.jsonl`)
  - `StepLog`: typed dataclass (task_id, step_index, agent, action, duration_ms, tokens_used, result, details)
  - `sanitize_value()`: recursive redactor for keys/tokens/passwords/GCP API keys/Bearer headers
  - `TaskAuditReporter`: computes success rate, latency, token spend, healed steps; generates Markdown report
  - `run_regression_suite()`: single-call runner across all 12 test modules — returns `{success, total_tests, critical_errors, elapsed_seconds}`
- **Fixed** `_normalize_tamil_query()`: added English verb-prefix guard to prevent `"play play X"` double-word artefact when input already starts with `play`, `search`, `open`, etc.
- **Tests**: 293 tests across 12 modules, 0 critical errors

---

## [1.x] — Pre-refactor (Legacy)

- Desktop executor with mouse/keyboard control (moved to `legacy/`)
- Screen watcher (`legacy/verify/screen_watcher.py`) — pywin32 + PIL perceptual hash
- Blender IPC integration (removed)
- Audio recording module (moved to `legacy/`)
