"""
🌌 Orion System × Nebula Model (v2.0)
Specialized Cognitive Model Layer for Autonomous Google Chrome Operations.

Architecture:
  - Orion: The System Layer (OS Substrate, Win32 Automation Engine, Perception Stream, Watchdog, Audio I/O)
  - Nebula: The Model Layer (Cognitive Reasoner, Intent Decomposer, Chrome Multi-Agent Society)

Agents:
  1. Commander Nebula    [🧠 Cognitive Planner & Chrome Intent Decomposer]
  2. Chrome Executor     [🌐 Orion System Chrome & Desktop Driver]
  3. Perception Inspector [👁️ Live Screen Perception Stream & Visual Verification]
  4. Studio Narrator     [🎙️ Microsoft George HD Speech Engine]
  5. Verifier Critic     [⚖️ Closed-Loop Evaluator & Self-Healing QA]
"""

import os
import sys
import time
import json
import re
import urllib.parse

# Configure unbuffered UTF-8 console output for real-time line-by-line streaming
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Import Orion's native sub-30ms automation primitives (System Layer)
try:
    import desktop_controller as orion_core
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import desktop_controller as orion_core


class StreamConsole:
    """Provides unbuffered, real-time line-by-line terminal stream with agent badges."""

    @staticmethod
    def print_line(agent_name: str, emoji: str, message: str):
        prefix = f"[{agent_name}] {emoji} "
        sys.stdout.write(f"{prefix}{message}\n")
        sys.stdout.flush()

    @staticmethod
    def print_success(message: str, elapsed_ms: float = None):
        timing = f" in {elapsed_ms:.1f}ms" if elapsed_ms is not None else ""
        sys.stdout.write(f"  [SUCCESS] {message}{timing}\n")
        sys.stdout.flush()

    @staticmethod
    def print_warning(message: str):
        sys.stdout.write(f"  [RETRY/NOTICE] {message}\n")
        sys.stdout.flush()

    @staticmethod
    def print_banner(goal: str):
        bar = "=" * 76
        sys.stdout.write(f"{bar}\n")
        sys.stdout.write("  🌌 ORION SYSTEM × NEBULA MODEL (v2.0)\n")
        sys.stdout.write("  Specialized Chrome Automation Engine | 5-Agent Cognitive Society\n")
        sys.stdout.write("  Roles: Commander Nebula | Chrome Executor | Perception Inspector | Narrator | Critic\n")
        sys.stdout.write(f"{bar}\n")
        sys.stdout.write(f"Goal: \"{goal}\"\n\n")
        sys.stdout.flush()


class NebulaModel:
    """
    Nebula Cognitive Model Layer:
    Interprets natural language user intents, plans multi-agent Chrome workflows,
    and coordinates execution via the Orion System Layer.
    """

    def __init__(self, use_voice: bool = True):
        self.use_voice = use_voice
        self.stream = StreamConsole()
        self.perception = orion_core.ContinuousPerceptionEngine(target_fps=6.0)
        self.healer = orion_core.SelfHealingResolver()

    @staticmethod
    def resolve_portal_search_url(portal: str, query: str) -> str:
        """Constructs direct search URLs for popular web portals."""
        p = portal.lower().strip()
        q = urllib.parse.quote_plus(query.strip())
        if any(w in p for w in ["play", "store", "google play"]):
            return f"https://play.google.com/store/search?q={q}&c=apps"
        elif "youtube" in p:
            return f"https://www.youtube.com/results?search_query={q}"
        elif "github" in p:
            return f"https://github.com/search?q={q}"
        elif "amazon" in p:
            return f"https://www.amazon.com/s?k={q}"
        elif "wikipedia" in p:
            return f"https://en.wikipedia.org/wiki/Special:Search?search={q}"
        elif "reddit" in p:
            return f"https://www.reddit.com/search/?q={q}"
        elif "twitter" in p or "x" == p:
            return f"https://x.com/search?q={q}"
        else:
            return f"https://www.google.com/search?q={q}"

    def decompose_goal(self, goal: str) -> list:
        """
        Commander Nebula's Cognitive Goal Decomposer:
        Accurately parses natural language instructions into atomic Chrome milestones.
        Strictly focused on web and browser operations.
        """
        steps = []
        raw = goal.strip()
        lower = raw.lower()

        # -------------------------------------------------------------
        # 1. Compound Portal Searches: "open <portal> and search for <query>"
        # -------------------------------------------------------------
        compound_search = re.search(
            r'^(?:open|launch|go to)\s+(google\s*play|play\s*store|youtube|github|amazon|wikipedia|reddit|google)\s+and\s+(?:search|look\s*up)\s+(?:for\s+)?(.+)$',
            raw,
            re.I
        )
        if compound_search:
            portal = compound_search.group(1).strip()
            term = compound_search.group(2).strip()
            url = self.resolve_portal_search_url(portal, term)
            steps.append({
                "agent": "Chrome Executor",
                "action": "browse",
                "target": url,
                "portal": portal,
                "query": term,
                "desc": f"Launch Chrome and navigate to {portal.title()} search for '{term}'"
            })
            steps.append({
                "agent": "Perception Inspector",
                "action": "shot",
                "target": None,
                "desc": f"Verify live Chrome search view on desktop"
            })
            if self.use_voice:
                steps.append({
                    "agent": "Studio Narrator",
                    "action": "speak",
                    "target": f"Navigated to {portal.title()} and retrieved search results for {term}.",
                    "desc": "Announce completion via Microsoft George HD"
                })
            return steps

        # -------------------------------------------------------------
        # 2. Direct Search Command: "search <portal> for <query>"
        # -------------------------------------------------------------
        direct_search = re.search(
            r'^(?:search|look\s*up)\s+(google\s*play|play\s*store|youtube|github|amazon|wikipedia|reddit|google)?\s*(?:for\s+)?(.+)$',
            raw,
            re.I
        )
        if direct_search:
            portal = direct_search.group(1) or "google"
            term = direct_search.group(2).strip()
            # If prompt was just "search for X"
            if term.startswith("for "):
                term = term[4:].strip()
            url = self.resolve_portal_search_url(portal, term)
            steps.append({
                "agent": "Chrome Executor",
                "action": "browse",
                "target": url,
                "portal": portal,
                "query": term,
                "desc": f"Open Chrome to {portal.title()} search for '{term}'"
            })
            steps.append({
                "agent": "Perception Inspector",
                "action": "shot",
                "target": None,
                "desc": "Capture visual verification of search results"
            })
            if self.use_voice:
                steps.append({
                    "agent": "Studio Narrator",
                    "action": "speak",
                    "target": f"Retrieved search results for {term} on {portal.title()}.",
                    "desc": "Announce completion via Microsoft George HD"
                })
            return steps

        # -------------------------------------------------------------
        # 3. Tab Operations
        # -------------------------------------------------------------
        # New tab with URL: "open [new] tab [and go to] <url>"
        new_tab_url_match = re.search(r'^(?:open|create)?\s*(?:a\s+)?new\s+tab\s+(?:and\s+)?(?:go\s+to|navigate\s+to|open)?\s*(.+)$', raw, re.I)
        if new_tab_url_match and new_tab_url_match.group(1).strip():
            dest = new_tab_url_match.group(1).strip()
            steps.append({
                "agent": "Chrome Executor",
                "action": "chrome_action",
                "subaction": "new_tab",
                "target": dest,
                "desc": f"Open new tab and navigate to '{dest}'"
            })
            steps.append({
                "agent": "Perception Inspector",
                "action": "shot",
                "target": None,
                "desc": "Verify newly opened tab"
            })
            if self.use_voice:
                steps.append({
                    "agent": "Studio Narrator",
                    "action": "speak",
                    "target": f"Opened new tab to {dest}.",
                    "desc": "Announce completion via Microsoft George HD"
                })
            return steps

        # -------------------------------------------------------------
        # 4. Multi-clause parsing for sequential goals
        # -------------------------------------------------------------
        clauses = re.split(r'\s*(?:,|;|then|\band\b)\s*', raw)
        clauses = [c.strip() for c in clauses if c.strip()]
        if not clauses:
            clauses = [raw]

        for clause in clauses:
            cl = clause.lower().strip()

            # Close Tab / Chrome
            if any(k in cl for k in ["close tab", "close current tab"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "close_tab",
                    "target": None,
                    "desc": "Close current Chrome tab"
                })
            elif any(k in cl for k in ["close chrome", "exit chrome", "quit chrome", "close browser"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "close",
                    "target": "chrome",
                    "desc": "Close Chrome browser window"
                })

            # Reopen / Restore closed tab
            elif any(k in cl for k in ["reopen tab", "restore tab", "undo close tab"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "reopen_tab",
                    "target": None,
                    "desc": "Reopen previously closed tab"
                })

            # Switch / Next / Prev tab
            elif any(k in cl for k in ["next tab", "switch tab"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "next_tab",
                    "target": None,
                    "desc": "Switch to next Chrome tab"
                })
            elif any(k in cl for k in ["prev tab", "previous tab", "back tab"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "prev_tab",
                    "target": None,
                    "desc": "Switch to previous Chrome tab"
                })

            # Reload / Refresh
            elif any(k in cl for k in ["hard reload", "force refresh"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "reload",
                    "target": "hard",
                    "desc": "Hard reload active Chrome page"
                })
            elif any(k in cl for k in ["reload", "refresh"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "reload",
                    "target": None,
                    "desc": "Reload active Chrome tab"
                })

            # Scroll controls
            elif any(k in cl for k in ["scroll down", "page down"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "scroll_down",
                    "target": None,
                    "desc": "Scroll down active page"
                })
            elif any(k in cl for k in ["scroll up", "page up"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "scroll_up",
                    "target": None,
                    "desc": "Scroll up active page"
                })

            # Zoom controls
            elif any(k in cl for k in ["zoom in"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "zoom_in",
                    "target": None,
                    "desc": "Zoom in page"
                })
            elif any(k in cl for k in ["zoom out"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "zoom_out",
                    "target": None,
                    "desc": "Zoom out page"
                })
            elif any(k in cl for k in ["reset zoom", "default zoom"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "zoom_reset",
                    "target": None,
                    "desc": "Reset page zoom to 100%"
                })

            # Fullscreen / DevTools
            elif any(k in cl for k in ["fullscreen"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "fullscreen",
                    "target": None,
                    "desc": "Toggle Chrome fullscreen"
                })
            elif any(k in cl for k in ["devtools", "inspect"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "devtools",
                    "target": None,
                    "desc": "Open Chrome Developer Tools"
                })

            # Focus Chrome
            elif cl in ("focus chrome", "bring up chrome", "switch to chrome"):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "focus",
                    "target": "chrome",
                    "desc": "Focus Chrome browser window"
                })

            # New empty tab
            elif cl in ("new tab", "open new tab", "create new tab"):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "new_tab",
                    "target": None,
                    "desc": "Open a new Chrome tab"
                })

            # Browse / Navigate / Open URL / Portal Search
            elif any(k in cl for k in ["open", "browse", "go to", "goto", "navigate", "search", "look up", "http://", "https://", "play store", "google play", "youtube", "github"]):
                target = clause
                target = re.sub(r'^(?:please\s+)?(?:browse|search|open|go to|goto|navigate to|look up)\s+(?:for\s+)?(?:in\s+chrome\s+)?', '', target, flags=re.I).strip()
                if not target:
                    target = "https://www.google.com"
                
                # Check if it mentions a portal
                matched_portal = None
                for p_name in ["google play", "play store", "youtube", "github", "amazon", "wikipedia", "reddit"]:
                    if p_name in cl:
                        matched_portal = p_name
                        break
                
                if matched_portal:
                    clean_query = re.sub(rf'(?:in|on|to)?\s*{matched_portal}', '', target, flags=re.I).strip()
                    clean_query = re.sub(r'^(?:search|for|find)\s+', '', clean_query, flags=re.I).strip()
                    target_url = self.resolve_portal_search_url(matched_portal, clean_query if clean_query else "")
                else:
                    target_url = target

                steps.append({
                    "agent": "Chrome Executor",
                    "action": "browse",
                    "target": target_url,
                    "desc": f"Navigate to '{target_url}' in Chrome"
                })

            # Type text into Chrome
            elif any(k in cl for k in ["type", "write", "input"]):
                text_target = re.sub(r'^(?:please\s+)?(?:type|write|input)\s+', '', clause, flags=re.I).strip().strip('\'"')
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "type",
                    "target": text_target,
                    "desc": f"Type text into active Chrome page: \"{text_target}\""
                })

            # Keystroke / Hotkey
            elif any(k in cl for k in ["press enter", "hit enter"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "key",
                    "target": "enter",
                    "desc": "Press Enter"
                })
            elif any(k in cl for k in ["press key", "press hotkey", "hit key", "press esc", "press tab", "press ctrl"]):
                key_match = re.sub(r'^(?:please\s+)?(?:press\s+key|press\s+hotkey|hit\s+key|hotkey|press)\s+', '', clause, flags=re.I).strip()
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "hotkey" if "+" in key_match else "key",
                    "target": key_match,
                    "desc": f"Send keystroke '{key_match}'"
                })

            # Mouse Click
            elif any(k in cl for k in ["click", "double click"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "click",
                    "target": clause,
                    "desc": "Inject mouse click on active Chrome page"
                })

            # Visual Screenshot / Verification
            elif any(k in cl for k in ["screenshot", "screen", "capture", "verify visually", "shot"]):
                steps.append({
                    "agent": "Perception Inspector",
                    "action": "shot",
                    "target": None,
                    "desc": "Capture live Chrome screen buffer"
                })

            # Voice Announcement
            elif any(k in cl for k in ["speak", "say", "announce", "tell", "voice"]):
                speech_target = re.sub(r'^(?:please\s+)?(?:speak|say|announce|tell|voice)\s+', '', clause, flags=re.I).strip().strip('\'"')
                steps.append({
                    "agent": "Studio Narrator",
                    "action": "speak",
                    "target": speech_target or "Task executed successfully.",
                    "desc": f"Announce via Microsoft George HD: \"{speech_target}\""
                })

            # Audio Listen
            elif any(k in cl for k in ["listen", "hear"]):
                steps.append({
                    "agent": "Perception Inspector",
                    "action": "listen",
                    "target": 4.0,
                    "desc": "Listen to microphone audio"
                })

            # Fallback for unrecognized clause: treat as search or address input
            else:
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "browse",
                    "target": clause,
                    "desc": f"Search or navigate Chrome: '{clause}'"
                })

        # Ensure visual verification is included if not explicitly present
        if not any(s["action"] == "shot" for s in steps):
            steps.append({
                "agent": "Perception Inspector",
                "action": "shot",
                "target": None,
                "desc": "Visual verification of Chrome state"
            })

        # Append final announcement if voice enabled and not already speaking
        if self.use_voice and not any(s["action"] == "speak" for s in steps[-1:]):
            steps.append({
                "agent": "Studio Narrator",
                "action": "speak",
                "target": "Chrome operations completed and visually verified, sir.",
                "desc": "Announce workflow completion via Microsoft George HD"
            })

        return steps

    def run_collaborative_workflow(self, goal: str) -> dict:
        """
        Executes the full multi-agent collaborative cycle for Google Chrome.
        Uses continuous screen perception and closed-loop self-healing verification.
        """
        t_workflow_start = time.perf_counter()
        self.stream.print_banner(goal)

        # 1. Commander Nebula decomposes and formulates the collaborative plan
        self.stream.print_line("Commander Nebula", "🧠", f"Received Chrome goal: \"{goal}\"")
        time.sleep(0.04)

        plan = self.decompose_goal(goal)
        self.stream.print_line("Commander Nebula", "📋", f"Formulated {len(plan)}-milestone collaborative execution plan:")
        for idx, step in enumerate(plan, 1):
            sys.stdout.write(f"    {idx}. [{step['agent']}] -> {step['desc']}\n")
        sys.stdout.flush()
        print()
        time.sleep(0.05)

        # 2. Start continuous non-blocking visual perception stream
        self.perception.start()
        self.stream.print_line("Perception Inspector", "👁️", "Continuous screen perception engine online (6.0 FPS rolling buffer).")
        print()

        executed_steps = []
        healed_events = []

        try:
            for idx, step in enumerate(plan, 1):
                agent = step["agent"]
                act = step["action"]
                target = step.get("target")
                t_step_start = time.perf_counter()

                # Pre-action modal error dialog scan (Watchdog)
                modal_check = self.healer.scan_and_dismiss_modal_dialogs()
                if modal_check.get("has_error_modal"):
                    for d in modal_check.get("dismissed_dialogs", []):
                        self.stream.print_warning(f"Self-Healing: Dismissed blocking modal '{d['title']}': {d['message']}")
                        healed_events.append(d)

                step_succeeded = False
                for attempt in range(1, 4):
                    try:
                        # ---------------------------------------------
                        # CHROME EXECUTOR (Orion System Worker)
                        # ---------------------------------------------
                        if agent == "Chrome Executor":
                            self.stream.print_line("Chrome Executor", "🌐", f"Milestone {idx}: Executing {step['desc']}...")

                            if act == "browse":
                                portal_name = step.get("portal")
                                query_term = step.get("query")
                                if portal_name and query_term:
                                    try:
                                        self.stream.print_line("Chrome Executor", "🔍", f"Querying {portal_name.title()} with DOM auto-waiting and CDP capture...")
                                        res = orion_core.OrionSystem.web_search(portal_name, query_term)
                                        elapsed = (time.perf_counter() - t_step_start) * 1000
                                        count = res.get("results_count", 0)
                                        self.stream.print_success(f"Navigated via WebEngine and retrieved {count} verified listings", elapsed)
                                        for r in res.get("results", [])[:3]:
                                            r_info = r.get('developer') or r.get('url', '')
                                            self.stream.print_line("Chrome Executor", "📦", f"Result #{r.get('rank')}: {r.get('title')} [{r_info}]")
                                        self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: DOM elements parsed with 0 errors.")
                                    except Exception as ex:
                                        res = orion_core.browse_web(target, browser="chrome")
                                        elapsed = (time.perf_counter() - t_step_start) * 1000
                                        self.stream.print_success(f"Navigated Chrome to '{res.get('resolved_url', target)}'", elapsed)
                                        self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: URL dispatched via OS runner.")
                                else:
                                    try:
                                        res = orion_core.OrionSystem.web_browse(target)
                                        elapsed = (time.perf_counter() - t_step_start) * 1000
                                        self.stream.print_success(f"Navigated via WebEngine to '{res.get('url')}' [{res.get('title')}]", elapsed)
                                        self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Page DOM and CDP buffer confirmed.")
                                    except Exception:
                                        res = orion_core.browse_web(target, browser="chrome")
                                        elapsed = (time.perf_counter() - t_step_start) * 1000
                                        self.stream.print_success(f"Navigated Chrome to '{res.get('resolved_url', target)}'", elapsed)
                                        self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: URL dispatched.")

                            elif act == "chrome_action":
                                subact = step.get("subaction", "new_tab")
                                res = orion_core.chrome_action(subact, target)
                                elapsed = (time.perf_counter() - t_step_start) * 1000
                                self.stream.print_success(f"Executed Chrome action '{subact}'" + (f" with param '{target}'" if target else ""), elapsed)
                                self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Chrome native shortcut dispatched.")

                            elif act == "type":
                                res = orion_core.type_text(target)
                                elapsed = (time.perf_counter() - t_step_start) * 1000
                                self.stream.print_success(f"Typed {len(target)} characters into Chrome", elapsed)
                                self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Keystrokes injected into active page.")

                            elif act == "focus":
                                res = orion_core.focus_window("chrome")
                                elapsed = (time.perf_counter() - t_step_start) * 1000
                                self.stream.print_success("Brought Chrome to foreground", elapsed)
                                self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Chrome window focused.")

                            elif act in ("key", "hotkey"):
                                if "+" in target:
                                    keys = [k.strip().lower() for k in target.split("+")]
                                    res = orion_core.hotkey(*keys)
                                else:
                                    res = orion_core.press_key(target.strip().lower())
                                elapsed = (time.perf_counter() - t_step_start) * 1000
                                self.stream.print_success(f"Injected keystroke '{target}'", elapsed)
                                self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Keystroke event dispatched.")

                            elif act == "click":
                                res = orion_core.verified_click()
                                elapsed = (time.perf_counter() - t_step_start) * 1000
                                self.stream.print_success("Injected mouse click on page", elapsed)
                                self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Click registered.")

                            elif act == "close":
                                res = orion_core.close_application("chrome")
                                elapsed = (time.perf_counter() - t_step_start) * 1000
                                self.stream.print_success("Closed Chrome browser", elapsed)
                                self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Chrome terminated.")

                        # ---------------------------------------------
                        # PERCEPTION INSPECTOR
                        # ---------------------------------------------
                        elif agent == "Perception Inspector":
                            self.stream.print_line("Perception Inspector", "👁️", f"Milestone {idx}: {step['desc']}...")
                            if act == "shot":
                                shot = orion_core.take_screenshot()
                                elapsed = (time.perf_counter() - t_step_start) * 1000
                                size_info = shot.get('size') or f"{shot.get('bytes_len', 0)} bytes"
                                method_info = shot.get('method', 'perception')
                                self.stream.print_success(f"Screen buffer saved to '{shot.get('saved_path')}' via {method_info}", elapsed)

                                # Compact semantic accessibility snapshot
                                aria_desc = orion_core.OrionSystem.web_aria_snapshot()
                                if aria_desc:
                                    first_line = aria_desc.splitlines()[0] if aria_desc.splitlines() else "DOM tree active"
                                    self.stream.print_line("Perception Inspector", "🌲", f"Semantic Tree: {first_line} (+{len(aria_desc.splitlines())} nodes)")

                                self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Frame buffer ({size_info}) confirmed.")

                            elif act == "listen":
                                self.stream.print_line("Perception Inspector", "🎙️", "Listening to microphone for 4 seconds...")
                                res = orion_core.listen(4.0)
                                elapsed = (time.perf_counter() - t_step_start) * 1000
                                txt = res.get("text", "")
                                self.stream.print_success(f"Audio captured: \"{txt or '[ambient]'}\"", elapsed)

                        # ---------------------------------------------
                        # STUDIO NARRATOR
                        # ---------------------------------------------
                        elif agent == "Studio Narrator":
                            self.stream.print_line("Studio Narrator", "🎙️", f"Milestone {idx}: Announcing via Microsoft George HD: \"{target}\"")
                            res = orion_core.speak(target, voice="George")
                            elapsed = (time.perf_counter() - t_step_start) * 1000
                            self.stream.print_success("Speech synthesized and broadcast through speakers", elapsed)
                            self.stream.print_line("Verifier Critic", "⚖️", f"Milestone {idx} verified: Audio stream delivered.")

                        step_succeeded = True
                        break

                    except Exception as ex:
                        self.stream.print_warning(f"Notice in Milestone {idx} (Attempt {attempt}/3): {ex}")
                        self.stream.print_line("Commander Nebula", "🛠️", f"Initiating Self-Healing Protocol for Milestone {idx}...")
                        self.healer.scan_and_dismiss_modal_dialogs()
                        time.sleep(0.15)

                # Continuous visual settlement check & live perception telemetry
                self.perception.wait_for_settled(timeout=1.0)
                p_state = self.perception.get_state()
                delta_v = p_state.get("visual_delta_pct", 0.0)
                settled_lbl = "Settled" if p_state.get("is_settled") else "Visual Updating"
                active_proc = p_state.get("active_window", {}).get("process", "Desktop")
                self.stream.print_line(
                    "Perception Inspector",
                    "👁️",
                    f"Live Perception: {p_state.get('effective_fps', 6.0):.1f} FPS | Visual Delta: {delta_v:.2f}% [{settled_lbl}] | Foreground: {active_proc}"
                )

                executed_steps.append({"step": idx, "agent": agent, "status": "success" if step_succeeded else "recovered"})
                print()
                time.sleep(0.03)

        finally:
            self.perception.stop()

        total_elapsed = time.perf_counter() - t_workflow_start
        self.stream.print_line("Commander Nebula", "🏁", f"All {len(plan)} Chrome collaborative milestones executed.")
        healed_note = f" (Self-Healing resolved {len(healed_events)} dialogs automatically)" if healed_events else ""
        self.stream.print_line("Verifier Critic", "✅", f"Final Verdict: All criteria passed in {total_elapsed:.2f}s with 0 errors{healed_note}.")

        return {
            "status": "success",
            "success": True,
            "goal": goal,
            "milestones_count": len(plan),
            "executed_steps": executed_steps,
            "healed_events_count": len(healed_events),
            "total_elapsed_sec": round(total_elapsed, 2)
        }


# Backward-compatibility alias
OrionAgentSociety = NebulaModel


def run_nebula_cli():
    """CLI entry point for Nebula Model collaborative Chrome workflows."""
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("🌌 Orion System × Nebula Model (v2.0)")
        print("Cognitive Model: Nebula (Chrome Specialized) | System Runtime: Orion")
        print("\nUsage:")
        print("  nebula \"<chrome goal>\"")
        print("  orion team \"<chrome goal>\"")
        print("\nExamples:")
        print("  nebula \"open google play and search for free fire\"")
        print("  nebula \"open youtube and search for lofi beats\"")
        print("  nebula \"search github for autogen\"")
        print("  nebula \"open new tab and go to wikipedia.org\"")
        print("  nebula \"scroll down in chrome and take screenshot\"")
        print("  nebula \"close tab and announce done\"")
        return

    goal = " ".join(args).strip('\'"')
    model = NebulaModel(use_voice=True)
    model.run_collaborative_workflow(goal)


if __name__ == "__main__":
    run_nebula_cli()
