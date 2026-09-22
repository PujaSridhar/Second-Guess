"""Commitment extraction - the LLM's job.

The model reads prose and proposes commitments. It does NOT decide whether one
is at risk; that is lint's job, in plain Python. Keep the baseline prompt naive
on purpose: if you tune it, you shrink your own before/after delta, and the
delta is the scored part.
"""
import json

from .config import AS_OF, DATA, OWNER
from .llm import agent, parse_structured

BASE_PROMPT = f"""You read someone's email, Slack, and meeting notes and pull out
the commitments THEY made.

The owner is {OWNER}. Today is {AS_OF}.

Return ONLY a JSON array. Each element:
  {{"description": "...", "owed_to": "...", "due_date": "YYYY-MM-DD or null",
    "source": "<file path>", "quote": "<the sentence they committed in>"}}

Do not assign a status. Something else decides that."""

# Appended only for the improved run. These are the rules distilled from user
# feedback into the permanent graph - see ground_truth/feedback.json.
LEARNED_RULES = """

You have learned these rules from past corrections. Apply them:

1. Hedged language is not a commitment. If there is no date and the phrasing is
   indefinite ("sometime", "when I get a chance", "I'll think about it"), skip it.
2. Ownership follows the first-person speaker. Action items belonging to other
   people are out of scope even when addressed to the owner.
3. A commitment is closed when a later message in the same thread confirms
   delivery or receipt. Do not report closed commitments as open.
4. An external deadline announced by someone else is not a commitment the owner
   made."""


def corpus():
    """Every source document, as (relative path, text)."""
    docs = []
    for sub in ("email", "slack", "meetings"):
        for path in sorted((DATA / sub).glob("*.md")):
            docs.append((f"{sub}/{path.name}", path.read_text()))
    cal = (DATA / "calendar" / "calendar.json").read_text()
    docs.append(("calendar/calendar.json", cal))
    return docs


def learned_rules():
    """Read the rules out of Cognee's permanent graph.

    Not a constant in this file: the rules got there because the user corrected
    the system, and they come back because the graph remembers. If Cognee is
    unreachable we fall back to the literal corrections rather than silently
    pretending the brain learned something.
    """
    import asyncio
    from .improve import recall_rules
    try:
        text = asyncio.run(recall_rules())
        if text and text.strip():
            return "\n\nRules you have learned from past corrections:\n" + text.strip()
    except Exception as exc:
        print(f"  [cognee recall failed: {exc}; using local corrections]")
    import json
    from .config import GROUND_TRUTH
    fb = json.loads((GROUND_TRUTH / "feedback.json").read_text())["corrections"]
    return "\n\nRules you have learned from past corrections:\n" + "\n".join(
        f"- {c['distilled_rule']}" for c in fb)


def extract(learned=False):
    prompt = BASE_PROMPT + (learned_rules() if learned else "")
    blob = "\n\n".join(f"--- {name} ---\n{text}" for name, text in corpus())
    reply = agent(prompt)(f"Extract the commitments.\n\n{blob}")
    items = parse_structured(str(reply))
    for it in items:
        it.setdefault("status", None)
    return items


if __name__ == "__main__":
    import sys
    learned = "--learned" in sys.argv
    out = extract(learned=learned)
    print(json.dumps(
        {"run": "improved" if learned else "baseline", "commitments": out},
        indent=2,
    ))
