# ==============================================================================
# 🌌 Nebula Brain (v2.0) - Unified Cognitive Model for Orion System
# ==============================================================================
# Bridges high-level natural language user intents to deterministic execution
# milestones. Supports Google Gemini AI (Cloud Brain) with a resilient
# local NLP & structured metadata resolver (Local Brain) fallback.
# ==============================================================================

import os
import re
import sys
import json
import time
import urllib.parse
import urllib.request
from typing import List, Dict, Any, Optional

# Load local .env if available
try:
    import dotenv
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
except Exception:
    pass


class NebulaBrain:
    """
    Unified Cognitive Engine for Orion/Nebula.
    - Cloud Mode: Google Gemini API (if GEMINI_API_KEY is available)
    - Local Mode: Structured NLP, semantic token matching & ytInitialData resolver
    """

    def __init__(self, use_voice: bool = True):
        self.use_voice = use_voice
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.gemini_model = None
        self._init_gemini()

    def _init_gemini(self):
        if not self.api_key:
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            try:
                self.gemini_model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    system_instruction=(
                        "You are Commander Nebula, the cognitive AI brain of the Orion Desktop Automation System. "
                        "Given a user command, formulate a precise, atomic execution plan. "
                        "Correct all typos, extract true user intent, and output strictly JSON."
                    )
                )
            except Exception:
                self.gemini_model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction="You are Commander Nebula, the cognitive brain of Orion."
                )
        except Exception:
            self.gemini_model = None

    @property
    def has_ai_brain(self) -> bool:
        return self.gemini_model is not None

    # ==========================================================================
    # 1. Semantic Token Normalization
    # ==========================================================================
    @staticmethod
    def normalize_text(text: str) -> str:
        """Corrects common typos, phonetics, and noisy prefixes."""
        s = text.strip()
        # Phonetic language corrections
        s = re.sub(r'\btamol\b', 'tamil', s, flags=re.I)
        s = re.sub(r'\btelgu\b', 'telugu', s, flags=re.I)
        s = re.sub(r'\bmalaylam\b', 'malayalam', s, flags=re.I)
        s = re.sub(r'\bhinid\b', 'hindi', s, flags=re.I)
        s = re.sub(r'\benglsih\b', 'english', s, flags=re.I)

        # Portal aliases
        s = re.sub(r'\byt\b', 'youtube', s, flags=re.I)
        s = re.sub(r'\bplaystore\b', 'google play', s, flags=re.I)
        s = re.sub(r'\bplay\s+store\b', 'google play', s, flags=re.I)
        return s

    # ==========================================================================
    # 2. Structured YouTube & Media Resolver (Zero-Key High-Accuracy Extraction)
    # ==========================================================================
    @classmethod
    def resolve_youtube_media(cls, query: str) -> Optional[Dict[str, Any]]:
        """
        Extracts structured search results from YouTube's ytInitialData payload.
        Inspects candidate titles, durations, and channels to find the best match.
        Returns exact watch URL with autoplay=1.
        """
        clean_q = cls.normalize_text(query)
        encoded = urllib.parse.quote_plus(clean_q)
        url = f"https://www.youtube.com/results?search_query={encoded}"

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9"
                }
            )
            html = urllib.request.urlopen(req, timeout=4).read().decode("utf-8", errors="ignore")

            m = re.search(r'var ytInitialData = ({.*?});</script>', html)
            if not m:
                m = re.search(r'window\["ytInitialData"\] = ({.*?});</script>', html)

            candidates = []
            if m:
                try:
                    data = json.loads(m.group(1))
                    contents = (
                        data.get("contents", {})
                        .get("twoColumnSearchResultsRenderer", {})
                        .get("primaryContents", {})
                        .get("sectionListRenderer", {})
                        .get("contents", [])
                    )
                    for sec in contents:
                        items = sec.get("itemSectionRenderer", {}).get("contents", [])
                        for item in items:
                            vr = item.get("videoRenderer")
                            if not vr:
                                continue
                            vid = vr.get("videoId")
                            title = "".join(r.get("text", "") for r in vr.get("title", {}).get("runs", []))
                            dur = vr.get("lengthText", {}).get("simpleText", "")
                            channel = "".join(r.get("text", "") for r in vr.get("ownerText", {}).get("runs", []))
                            if vid and title:
                                candidates.append({
                                    "id": vid,
                                    "title": title,
                                    "duration": dur,
                                    "channel": channel,
                                    "url": f"https://www.youtube.com/watch?v={vid}&autoplay=1"
                                })
                except Exception:
                    pass

            if not candidates:
                raw_vids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                seen = set()
                for vid in raw_vids:
                    if vid not in seen:
                        seen.add(vid)
                        candidates.append({
                            "id": vid,
                            "title": clean_q,
                            "duration": "",
                            "channel": "",
                            "url": f"https://www.youtube.com/watch?v={vid}&autoplay=1"
                        })
                    if len(candidates) >= 5:
                        break

            if not candidates:
                return None

            # Score candidates based on query token matches
            q_tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', clean_q.lower()))
            best_cand = candidates[0]
            best_score = -1.0

            for cand in candidates:
                cand_title_lower = cand["title"].lower()
                cand_tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', cand_title_lower))
                overlap = len(q_tokens & cand_tokens)
                score = float(overlap)

                # Penalize Shorts / teasers
                dur = cand["duration"]
                if dur:
                    parts = dur.split(":")
                    if len(parts) == 2 and int(parts[0]) == 0 and int(parts[1]) < 50:
                        score -= 2.0

                # Boost official / video songs
                if any(w in cand_title_lower for w in ["video song", "official", "lyrics", "full song", "audio"]):
                    score += 0.5

                if score > best_score:
                    best_score = score
                    best_cand = cand

            return best_cand

        except Exception:
            return None

    # ==========================================================================
    # 3. Cognitive Goal Decomposition
    # ==========================================================================
    def decompose_goal(self, goal: str) -> List[Dict[str, Any]]:
        """
        Decomposes natural language user goals into atomic execution milestones.
        Uses Gemini AI if configured, otherwise uses the smart local cognitive engine.
        """
        raw = goal.strip()
        cleaned_goal = self.normalize_text(raw)

        # -------------------------------------------------------------
        # Path A: Google Gemini AI Brain (if API key available)
        # -------------------------------------------------------------
        if self.gemini_model:
            try:
                ai_plan = self._decompose_with_gemini(cleaned_goal)
                if ai_plan:
                    return ai_plan
            except Exception:
                pass

        # -------------------------------------------------------------
        # Path B: Local Cognitive Engine (Zero-Key Resilient Fallback)
        # -------------------------------------------------------------
        return self._decompose_locally(cleaned_goal, original_raw=raw)

    def _decompose_with_gemini(self, goal: str) -> Optional[List[Dict[str, Any]]]:
        """Queries Gemini AI for structured milestone formulation."""
        prompt = f"""
Analyze this desktop/browser command: "{goal}"
Formulate an atomic milestone plan for Orion System.
Return ONLY valid JSON with this structure:
{{
  "intent": "media_play" | "web_search" | "tab_operation" | "desktop_action",
  "portal": "youtube" | "google" | "google play" | "github" | null,
  "clean_query": "<cleaned search or song name>",
  "play": true | false,
  "target_url": "<direct url if known, otherwise null>",
  "speech_announcement": "<short voice announcement for user>"
}}
"""
        response = self.gemini_model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        data = json.loads(text)

        steps = []
        intent = data.get("intent")
        portal = data.get("portal")
        query = data.get("clean_query")
        should_play = data.get("play", False)
        speech = data.get("speech_announcement")

        if intent == "media_play" or (portal == "youtube" and should_play):
            media_info = self.resolve_youtube_media(query or goal)
            target_url = media_info["url"] if media_info else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query or goal)}"
            title = media_info.get("title", query) if media_info else query

            steps.append({
                "agent": "Chrome Executor",
                "action": "browse",
                "target": target_url,
                "portal": "youtube",
                "query": query,
                "play": True,
                "desc": f"Stream '{title}' on YouTube in Chrome"
            })
            steps.append({
                "agent": "Perception Inspector",
                "action": "shot",
                "target": None,
                "desc": "Verify active YouTube video playback on desktop"
            })
            if self.use_voice:
                steps.append({
                    "agent": "Studio Narrator",
                    "action": "speak",
                    "target": speech or f"Now playing {query} on YouTube, sir.",
                    "desc": "Announce playback via Microsoft George HD"
                })
            return steps

        return None

    def _decompose_locally(self, goal: str, original_raw: str) -> List[Dict[str, Any]]:
        """Local cognitive decomposition with multi-token parsing."""
        steps = []
        raw = goal

        # 1. Direct Play Command
        play_direct = re.search(r'^(?:play|listen\s+to|start)\s+(.+?)(?:\s+(?:on|in)\s+youtube)?$', raw, re.I)
        if play_direct:
            term = play_direct.group(1).strip()
            media = self.resolve_youtube_media(term)
            target_url = media["url"] if media else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(term)}"
            display_title = media.get("title", term) if media else term

            steps.append({
                "agent": "Chrome Executor",
                "action": "browse",
                "target": target_url,
                "portal": "youtube",
                "query": term,
                "play": True,
                "desc": f"Launch Chrome and play '{display_title}' on YouTube"
            })
            steps.append({
                "agent": "Perception Inspector",
                "action": "shot",
                "target": None,
                "desc": "Verify active YouTube video playback on desktop"
            })
            if self.use_voice:
                steps.append({
                    "agent": "Studio Narrator",
                    "action": "speak",
                    "target": f"Now playing {term} on YouTube, sir.",
                    "desc": "Announce playback via Microsoft George HD"
                })
            return steps

        # 2. Compound Portal Searches
        compound_search = re.search(
            r'^(?:open|launch|go to)\s+(google\s*play|play\s*store|youtube|github|amazon|wikipedia|reddit|google)\s+and\s+(?:search|look\s*up)\s+(?:for\s+)?(.+)$',
            raw,
            re.I
        )
        if compound_search:
            portal = compound_search.group(1).strip().lower()
            term = compound_search.group(2).strip()

            should_play = bool(re.search(r'\b(?:and\s+)?(?:play\s+it|play|start\s+it|listen)\b', term, re.I))
            clean_term = re.sub(r'\b(?:and\s+)?(?:play\s+it|play|start\s+it|listen)\b', '', term, flags=re.I).strip()
            clean_term = re.sub(r'^(?:a|an|the|for)\s+', '', clean_term, flags=re.I).strip()

            if "youtube" in portal and should_play:
                media = self.resolve_youtube_media(clean_term)
                target_url = media["url"] if media else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_term)}"
                display_title = media.get("title", clean_term) if media else clean_term

                steps.append({
                    "agent": "Chrome Executor",
                    "action": "browse",
                    "target": target_url,
                    "portal": "youtube",
                    "query": clean_term,
                    "play": True,
                    "desc": f"Launch Chrome and play '{display_title}' on YouTube"
                })
                steps.append({
                    "agent": "Perception Inspector",
                    "action": "shot",
                    "target": None,
                    "desc": "Verify active YouTube video playback on desktop"
                })
                if self.use_voice:
                    steps.append({
                        "agent": "Studio Narrator",
                        "action": "speak",
                        "target": f"Now playing {clean_term} on YouTube, sir.",
                        "desc": "Announce playback via Microsoft George HD"
                    })
                return steps

            url = self.resolve_portal_url(portal, clean_term or term)
            steps.append({
                "agent": "Chrome Executor",
                "action": "browse",
                "target": url,
                "portal": portal,
                "query": clean_term or term,
                "desc": f"Launch Chrome and navigate to {portal.title()} search for '{clean_term or term}'"
            })
            steps.append({
                "agent": "Perception Inspector",
                "action": "shot",
                "target": None,
                "desc": "Verify live Chrome search view on desktop"
            })
            if self.use_voice:
                steps.append({
                    "agent": "Studio Narrator",
                    "action": "speak",
                    "target": f"Searching {portal.title()} for {clean_term or term}.",
                    "desc": "Announce action via Microsoft George HD"
                })
            return steps

        # 3. Tab Operations
        new_tab = re.search(r'^(?:open|create)?\s*(?:a\s+)?new\s+tab\s+(?:and\s+)?(?:go\s+to|navigate\s+to|open)?\s*(.+)$', raw, re.I)
        if new_tab and new_tab.group(1).strip():
            dest = new_tab.group(1).strip()
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

        # 4. Multi-clause parsing for sequential goals
        clauses = re.split(r'\s*(?:,|;|then|\band\b)\s*', raw)
        clauses = [c.strip() for c in clauses if c.strip()]
        if not clauses:
            clauses = [raw]

        for clause in clauses:
            cl = clause.lower().strip()
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
            elif any(k in cl for k in ["reopen tab", "restore tab"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "reopen_tab",
                    "target": None,
                    "desc": "Reopen previously closed tab"
                })
            elif any(k in cl for k in ["next tab", "switch tab"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "next_tab",
                    "target": None,
                    "desc": "Switch to next Chrome tab"
                })
            elif any(k in cl for k in ["prev tab", "previous tab"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "prev_tab",
                    "target": None,
                    "desc": "Switch to previous Chrome tab"
                })
            elif any(k in cl for k in ["scroll down", "scroll page down"]):
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "chrome_action",
                    "subaction": "scroll_down",
                    "target": None,
                    "desc": "Scroll down active Chrome page"
                })
            elif any(k in cl for k in ["speak", "say", "announce", "tell"]):
                speech_target = re.sub(r'^(?:please\s+)?(?:speak|say|announce|tell)\s+', '', clause, flags=re.I).strip().strip('\'"')
                steps.append({
                    "agent": "Studio Narrator",
                    "action": "speak",
                    "target": speech_target or "Task executed successfully.",
                    "desc": f"Announce via Microsoft George HD: \"{speech_target}\""
                })
            else:
                steps.append({
                    "agent": "Chrome Executor",
                    "action": "browse",
                    "target": clause,
                    "desc": f"Search or navigate Chrome: '{clause}'"
                })

        if not any(s["action"] == "shot" for s in steps):
            steps.append({
                "agent": "Perception Inspector",
                "action": "shot",
                "target": None,
                "desc": "Visual verification of Chrome state"
            })

        if self.use_voice and not any(s["action"] == "speak" for s in steps[-1:]):
            steps.append({
                "agent": "Studio Narrator",
                "action": "speak",
                "target": "Operations completed and visually verified, sir.",
                "desc": "Announce workflow completion via Microsoft George HD"
            })

        return steps

    @staticmethod
    def resolve_portal_url(portal: str, query: str) -> str:
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
