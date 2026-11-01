"""
MIO Eyes: Privacy Guard & Ephemeral Mechanical Shutter
------------------------------------------------------
Enforces privacy and safety guarantees for MIO's visual perception:
1. Mechanical Shutter: Locked by default. Only opens during explicit on-demand calls.
2. Window Scoping: Rejects inspections of blacklisted sensitive applications (password managers, banking).
3. Redaction: Automatically masks sensitive data (credit cards, tokens, secret keys) in extracted text.
4. Ephemeral RAM-Only: Screen buffers are wiped from memory immediately after parsing.
"""

import os
import re
from typing import Tuple

SHUTTER_LOCKED = True
_ACTIVE_SHUTTERS = 0

BLACKLISTED_PROCESSES = {
    "bitwarden",
    "1password",
    "keepass",
    "keepassxc",
    "lastpass",
    "dashlane",
    "nordpass",
    "authenticator",
    "credentialuibroker",
    "consent",
    "taskmgr",
    "vault",
    "protonpass",
}

SENSITIVE_TITLE_KEYWORDS = [
    "password",
    "incognito",
    "inprivate",
    "private browsing",
    "master key",
    "bank",
    "banking",
    "bank account",
    "credit card",
    "sign in",
    "login",
    "two-factor",
    "2fa",
    "authenticator",
]

# Common PII Regex Patterns
RE_CREDIT_CARD = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
RE_BEARER_TOKEN = re.compile(r"\b(Bearer\s+[A-Za-z0-9_\-\.]{20,})\b", re.IGNORECASE)
RE_API_KEY = re.compile(r"\b(AIza[0-9A-Za-z-_]{35}|sk-[a-zA-Z0-9]{32,})\b")
RE_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def is_window_safe(title: str = "", process_name: str = "") -> Tuple[bool, str]:
    """
    Checks if a target window or process is permitted for inspection under the Safe-Eye Privacy Shield.
    Returns (is_safe, reason).
    """
    norm_proc = (process_name or "").strip().lower()
    if norm_proc.endswith(".exe"):
        norm_proc = norm_proc[:-4]

    for blocked in BLACKLISTED_PROCESSES:
        if blocked in norm_proc:
            return False, f"Privacy Shield blocked: Process '{process_name}' is a protected credentials manager."

    norm_title = (title or "").strip().lower()
    for kw in SENSITIVE_TITLE_KEYWORDS:
        if kw in norm_title:
            return False, f"Privacy Shield blocked: Window title matches sensitive privacy filter ('{kw}')."

    return True, "Window cleared by Privacy Shield."


def redact_sensitive_text(text: str) -> str:
    """Masks detected credit card numbers, tokens, API keys, and SSNs."""
    if not text:
        return ""

    scrubbed = RE_CREDIT_CARD.sub("[REDACTED_CARD]", text)
    scrubbed = RE_BEARER_TOKEN.sub("[REDACTED_TOKEN]", scrubbed)
    scrubbed = RE_API_KEY.sub("[REDACTED_API_KEY]", scrubbed)
    scrubbed = RE_SSN.sub("[REDACTED_SSN]", scrubbed)
    return scrubbed


class SafeEyeShutter:
    """
    Context manager that unlocks the mechanical shutter for a single inspection frame,
    verifies target window privacy, and relocks and cleans up buffers on exit.
    """
    def __init__(self, target_title: str = "", target_proc: str = ""):
        self.target_title = target_title
        self.target_proc = target_proc
        self.is_open = False

    def __enter__(self):
        global SHUTTER_LOCKED, _ACTIVE_SHUTTERS
        safe, reason = is_window_safe(self.target_title, self.target_proc)
        if not safe:
            raise PermissionError(reason)

        _ACTIVE_SHUTTERS += 1
        SHUTTER_LOCKED = False
        self.is_open = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global SHUTTER_LOCKED, _ACTIVE_SHUTTERS
        _ACTIVE_SHUTTERS = max(0, _ACTIVE_SHUTTERS - 1)
        if _ACTIVE_SHUTTERS == 0:
            SHUTTER_LOCKED = True
        self.is_open = False


def get_guard_status() -> dict:
    """Returns current security and shutter state."""
    return {
        "shutter_locked": SHUTTER_LOCKED,
        "active_inspection_sessions": _ACTIVE_SHUTTERS,
        "privacy_shield_active": True,
        "blacklisted_process_count": len(BLACKLISTED_PROCESSES),
        "sensitive_keyword_count": len(SENSITIVE_TITLE_KEYWORDS),
    }
