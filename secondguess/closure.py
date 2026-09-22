"""Closed-commitment detection - deterministic.

The model kept re-proposing the W-9 as an open commitment even with the rule
sitting in Cognee. That is the right outcome for a prompt rule and the wrong
place for the logic: whether a thread confirms delivery is a fact about the
document, not a judgement call. So it moves into Python, where it holds every
time instead of most of the time.
"""
import re

from .config import DATA

CONFIRMATIONS = [
    r"\breceived\b",
    r"\bwe have everything we need\b",
    r"\bnothing further from your side\b",
    r"\ball set\b",
    r"\bconfirming receipt\b",
    r"\bgot it,? thank",
    r"\bno further action\b",
]


def _doc_text(source):
    if not source:
        return ""
    path = DATA / source
    return path.read_text() if path.exists() else ""


def is_closed(commitment):
    """True when the commitment's own source thread confirms it was delivered.

    Looks only AFTER the committing sentence, so a confirmation that precedes
    the promise does not close it.
    """
    for source in (commitment.get("sources") or [commitment.get("source")]):
        text = _doc_text(source)
        if not text:
            continue
        quote = commitment.get("quote") or ""
        idx = text.find(quote[:60]) if quote else -1
        tail = text[idx:] if idx != -1 else text
        for pat in CONFIRMATIONS:
            if re.search(pat, tail, re.I):
                return True, f"Thread confirms delivery ({source}): matched /{pat}/."
    return False, None
