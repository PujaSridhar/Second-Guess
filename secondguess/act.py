"""Draft the follow-up a flagged commitment needs.

Nothing is ever sent. The point of the event's "take an action" bar is that the
system closes the loop, not that it gets to mail people on your behalf without
you reading it first.
"""
from .config import AT_RISK, BROKEN
from .llm import agent, parse_structured

DRAFT_PROMPT = """You draft short, plain follow-up messages for a commitment the
owner cannot keep as promised. No throat-clearing, no apology spiral. State the
change, give the new date or the new plan, keep it under 80 words.

Return ONLY: {"to": "...", "subject": "...", "body": "..."}"""


def draft(commitment):
    if commitment.get("status") not in (AT_RISK, BROKEN):
        return None
    ctx = (
        f"Commitment: {commitment['description']}\n"
        f"Owed to: {commitment.get('owed_to')}\n"
        f"Original due date: {commitment.get('due_date')}\n"
        f"Problem: {commitment.get('why')}\n"
    )
    if commitment.get("suggested_date"):
        ctx += f"Owner is next available: {commitment['suggested_date']}\n"
    try:
        return parse_structured(str(agent(DRAFT_PROMPT)(ctx)))
    except Exception as exc:
        return {"error": str(exc)[:200]}


def draft_all(commitments):
    out = []
    for c in commitments:
        d = draft(c)
        if d:
            c["draft"] = d
            out.append((c, d))
    return out
