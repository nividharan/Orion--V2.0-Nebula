"""
input_pipeline.py — Natural Language & Speech Input Understanding Pipeline
==========================================================================
Global Rules & Stages:
1. Capture: text or voice (+ STT confidence)
2. Clean: strip wake word/fillers, phonetic typo fixes (tamol->tamil), mixed Tamil/English
3. Cancel/Negation: intercept stop/cancel/undo/negation
4. Split: break compound multi-step commands into discrete execution phases
5. Resolve: resolve references ('it', 'that site', 'again') from conversational memory
6. Understand: fast local parser first; LLM only on low confidence
7. Validate: validate against Schema, ALLOWED_DOMAINS, and ALLOWED_ACTIONS
8. Confidence Gate:
     - Clear + Low/Medium risk -> RUN
     - Ambiguous -> ASK (with candidate options)
     - Sensitive / High risk -> APPROVE (with read-back confirmation)
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from schemas import (
    ALLOWED_ACTIONS,
    ALLOWED_DOMAINS,
    SENSITIVE_ACTIONS,
    ActionType,
    IntentType,
    Plan,
    Step,
    local_parse,
    validate_plan,
)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class CapturedInput:
    """Raw input captured from text or microphone."""
    raw_text: str
    source: Literal["text", "voice"] = "text"
    stt_confidence: float = 1.0


@dataclass
class ConversationContext:
    """Episodic context memory for reference and state resolution."""
    last_url: Optional[str] = None
    last_domain: Optional[str] = None
    last_query: Optional[str] = None
    last_candidates: List[Dict[str, Any]] = field(default_factory=list)
    last_action: Optional[str] = None
    last_plan: Optional[Plan] = None


@dataclass
class PipelineResult:
    """Structured decision output from the Input Pipeline."""
    status: Literal["run", "ask", "approve", "cancel", "undo", "error"]
    cleaned_text: str
    plan: Optional[Plan] = None
    options: List[Dict[str, Any]] = field(default_factory=list)
    read_back: Optional[str] = None
    requires_approval: bool = False
    clarification_question: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Stage 2: Normalization, Typo Correction & Bilingual Cleaning
# ---------------------------------------------------------------------------

WAKE_WORDS = [
    r"\b(hey|ok|hello)?\s*(orion|nebula)\b",
]

FILLER_WORDS = [
    r"\bplease\b", r"\bkindly\b", r"\bcan\s+you\b", r"\bcould\s+you\b",
    r"\bjust\b", r"\bum+\b", r"\buh+\b", r"\bnow\b",
]

PHONETIC_TYPOS = [
    (r"\btamol\b", "tamil"),
    (r"\btelgu\b", "telugu"),
    (r"\bmalaylam\b", "malayalam"),
    (r"\bhinid\b", "hindi"),
    (r"\byotube\b", "youtube"),
    (r"\byoutub\b", "youtube"),
    (r"\bgogle\b", "google"),
    (r"\bamzon\b", "amazon"),
    (r"\bgithb\b", "github"),
    (r"\bwikpedia\b", "wikipedia"),
]

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"you\s+are\s+now\s+(in\s+)?evil",
    r"system\s*prompt",
    r"bypass\s+safety",
    r"format\s+drive",
    r"delete\s+system32",
    r"drop\s+database",
]


def _normalize_tamil_query(s: str) -> str:
    """Translates colloquial Tamil browser/song commands into canonical English commands."""
    has_play_verb = any(w in s for w in ["podu", "vilayadu", "kaattu", "kaatu", "vei"])
    has_media_noun = any(w in s for w in ["paatu", "paadal", "padam", "trailer", "melodies", "song"])
    has_youtube = "youtube" in s or "la" in s

    if has_play_verb or (has_media_noun and has_youtube):
        clean_s = s
        for w in ["youtube la", "youtube", "la", "paatu", "paadal", "podu", "vilayadu", "kaattu", "kaatu", "vei"]:
            clean_s = re.sub(r'\b' + w + r'\b', '', clean_s, flags=re.IGNORECASE)
        clean_s = re.sub(r'\s+', ' ', clean_s).strip()
        if clean_s:
            return f"play {clean_s} on youtube"
    return s


def clean_input(text: str) -> str:
    """Cleans input text: strips wake words, fillers, corrects typos and mixed Tamil/English."""
    if not text:
        return ""

    s = text.strip().lower()

    # 1. Strip wake words
    for pat in WAKE_WORDS:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)

    # 2. Correct phonetic typos
    for pat, repl in PHONETIC_TYPOS:
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)

    # 3. Strip fillers
    for pat in FILLER_WORDS:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)

    # 4. Handle mixed Tamil / English
    s = _normalize_tamil_query(s)

    # Clean multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Stage 3: Cancel, Negation & Undo Interception
# ---------------------------------------------------------------------------

def check_cancel_or_negation(text: str) -> Optional[str]:
    """Detects explicit user halts, negations, or undo instructions."""
    s = text.lower().strip()

    cancel_triggers = ["stop", "cancel", "halt", "abort", "terminate", "nevermind", "exit"]
    if any(s.startswith(t) for t in cancel_triggers):
        return "cancel"

    negation_triggers = [
        "no, not that one", "not that one", "no not this", "not this one",
        "wrong one", "different one", "choose another", "pick another",
        "not that", "not this"
    ]
    if any(trig in s for trig in negation_triggers):
        return "reject_candidate"

    undo_triggers = ["undo", "revert", "go back", "take it back"]
    if any(s.startswith(u) for u in undo_triggers):
        return "undo"

    return None


# ---------------------------------------------------------------------------
# Stage 4: Split Multi-Step Commands
# ---------------------------------------------------------------------------

def split_commands(text: str) -> List[str]:
    """Splits compound commands joined by distinct sequence connectors."""
    connectors = [
        r"\s+and\s+then\s+",
        r"\s+then\s+",
        r"\s+after\s+that\s+",
        r"\s+afterwards\s+",
        r"\s*;\s*",
    ]
    combined_pat = "|".join(f"(?:{c})" for c in connectors)
    parts = re.split(combined_pat, text, flags=re.IGNORECASE)
    cleaned_parts = [p.strip() for p in parts if p.strip()]
    return cleaned_parts if cleaned_parts else [text]


# ---------------------------------------------------------------------------
# Stage 5: Reference Resolution
# ---------------------------------------------------------------------------

def resolve_references(text: str, context: Optional[ConversationContext]) -> str:
    """Resolves anaphoric references ('it', 'that site', 'again') from episodic memory."""
    if not context:
        return text

    s = text.strip()

    # "again", "search again", "play again"
    if re.search(r"\b(again|replay|once more)\b", s, re.IGNORECASE):
        if context.last_query:
            action = "search for" if "search" in s else "play"
            return f"{action} {context.last_query}"
        if context.last_url:
            return f"open {context.last_url}"

    # "play it" / "open it" / "resume it"
    if re.search(r"\b(play|open|resume|watch)\s+it\b", s, re.IGNORECASE):
        if context.last_query:
            return re.sub(r"\bit\b", context.last_query, s, flags=re.IGNORECASE)
        if context.last_url:
            return re.sub(r"\bit\b", context.last_url, s, flags=re.IGNORECASE)

    # "that site" / "that page" / "go back to that site"
    if re.search(r"\b(that\s+site|that\s+page|that\s+website)\b", s, re.IGNORECASE):
        if context.last_domain:
            return re.sub(r"\b(that\s+site|that\s+page|that\s+website)\b", context.last_domain, s, flags=re.IGNORECASE)
        if context.last_url:
            return re.sub(r"\b(that\s+site|that\s+page|that\s+website)\b", context.last_url, s, flags=re.IGNORECASE)

    return s


# ---------------------------------------------------------------------------
# Stage 6 & 7: Understand, Validate & Confidence Gate
# ---------------------------------------------------------------------------

class InputPipeline:
    """Full-stack input understanding pipeline enforcing all Phase 5 specifications."""

    def __init__(self, default_confidence: float = 0.95):
        self.default_confidence = default_confidence

    def process(
        self,
        raw_input: Union[str, CapturedInput],
        context: Optional[ConversationContext] = None
    ) -> PipelineResult:
        """Processes raw text or speech input through the 7-stage pipeline."""
        # 1. Capture
        if isinstance(raw_input, str):
            captured = CapturedInput(raw_text=raw_input)
        else:
            captured = raw_input

        # Check for empty input
        if not captured.raw_text.strip():
            return PipelineResult(
                status="ask",
                cleaned_text="",
                clarification_question="I didn't catch that. Could you please specify what you would like to do?"
            )

        # Prompt-injection defense: Untrusted data check
        for inj in INJECTION_PATTERNS:
            if re.search(inj, captured.raw_text, re.IGNORECASE):
                return PipelineResult(
                    status="error",
                    cleaned_text=captured.raw_text,
                    error="Security violation: Input contained instruction override or forbidden command."
                )

        # 2. Clean
        cleaned = clean_input(captured.raw_text)

        # 3. Cancel / Negation / Undo check
        cancel_action = check_cancel_or_negation(cleaned)
        if cancel_action == "cancel":
            return PipelineResult(status="cancel", cleaned_text=cleaned)
        elif cancel_action == "undo":
            return PipelineResult(status="undo", cleaned_text=cleaned)
        elif cancel_action == "reject_candidate":
            opts = context.last_candidates[1:4] if (context and context.last_candidates) else []
            return PipelineResult(
                status="ask",
                cleaned_text=cleaned,
                options=opts,
                clarification_question="Understood. Would you prefer one of these alternatives instead?"
            )

        # 4. Resolve references
        resolved = resolve_references(cleaned, context)

        # 5. Split compound commands
        subcommands = split_commands(resolved)

        # 6. Understand (Local parser first)
        plan_steps: List[Step] = []
        overall_intent: IntentType = IntentType.UNKNOWN
        accumulated_confidence = captured.stt_confidence

        for subcmd in subcommands:
            parsed = local_parse(subcmd)
            if parsed and parsed.steps:
                plan_steps.extend(parsed.steps)
                overall_intent = parsed.intent
                accumulated_confidence = min(accumulated_confidence, parsed.confidence)
            else:
                # Ambiguous command
                return PipelineResult(
                    status="ask",
                    cleaned_text=resolved,
                    clarification_question=f"I'm not certain how to handle '{subcmd}'. Did you mean to search the web, play media, or open a site?"
                )

        # Cap plan steps at 30
        if len(plan_steps) > 30:
            return PipelineResult(
                status="error",
                cleaned_text=resolved,
                error="Plan rejected: Compound command exceeds 30-step maximum safety limit."
            )

        final_plan = Plan(
            intent=overall_intent,
            confidence=accumulated_confidence,
            steps=plan_steps,
            parsed_from=resolved
        )

        # 7. Validate & Confidence Gate
        # Check if any step requires approval (sensitive or high risk)
        has_sensitive_step = False
        sensitive_step_desc = ""

        for step in final_plan.steps:
            act_name = step.action.value.lower()
            target_str = str(step.target or "").lower()

            # Check if action or target is sensitive
            if act_name in SENSITIVE_ACTIONS or step.risk == "high" or any(s in target_str for s in SENSITIVE_ACTIONS):
                has_sensitive_step = True
                step.requires_approval = True
                sensitive_step_desc = f"{step.action.value} ({step.target or 'action'})"
                break

        if has_sensitive_step:
            read_back_msg = (
                f"You requested to perform a sensitive operation: '{sensitive_step_desc}'. "
                f"Please confirm: Do you wish to approve this action?"
            )
            return PipelineResult(
                status="approve",
                cleaned_text=resolved,
                plan=final_plan,
                requires_approval=True,
                read_back=read_back_msg
            )

        # Ambiguity threshold gate
        if accumulated_confidence < 0.70:
            return PipelineResult(
                status="ask",
                cleaned_text=resolved,
                plan=final_plan,
                clarification_question="Your request appears ambiguous. Please select an action to continue:",
                options=[
                    {"index": 1, "label": f"Search the web for '{resolved}'"},
                    {"index": 2, "label": f"Play media for '{resolved}'"},
                ]
            )

        # Clear + Low/Medium risk -> RUN
        return PipelineResult(
            status="run",
            cleaned_text=resolved,
            plan=final_plan,
            requires_approval=False
        )
